from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from backend.core.config import settings
from backend.db.base import AsyncSessionLocal
from backend.db.service import save_telemetry_batch
from backend.services.f1_service import f1_service

logger = logging.getLogger(__name__)

RPM_REDLINE = 11500
THROTTLE_WOT = 100
BRAKE_HEAVY = 80
DRS_FAULT_CODES: set[int] = set()
DRS_RECOGNIZED_CODES = {0, 1, 8, 10, 12, 14}
DRS_ACTIVE_CODES = {10, 12, 14}
TELEMETRY_FETCH_TIMEOUT_SECONDS = 2.0
FALLBACK_RETRY_TICKS = 20
_last_seen_warnings = set()
_last_seen_warnings_lock = Lock()


def _clamp_percentage(value: float) -> float:
    return max(0.0, min(100.0, value))


def is_drs_active(drs_val: int) -> bool:
    return drs_val in DRS_ACTIVE_CODES


def _is_drs_fault(drs_val: int) -> bool:
    if drs_val == 0 or is_drs_active(drs_val):
        return False

    return drs_val in DRS_FAULT_CODES or drs_val not in DRS_RECOGNIZED_CODES


def _row_to_record(row: Any, session_key: str, driver_number: int) -> dict[str, Any]:
    date_value = row.get("Date")
    date_iso = (
        date_value.isoformat()
        if hasattr(date_value, "isoformat")
        else datetime.now(UTC).isoformat()
    )

    gear = _to_int(row.get("nGear"))
    return {
        "session_key": session_key,
        "date": date_iso,
        "driver_number": driver_number,
        "speed": _to_float(row.get("Speed")),
        "throttle": _to_float(row.get("Throttle")),
        "brake": _to_float(row.get("Brake")),
        "rpm": _to_int(row.get("RPM")),
        "gear": gear,
        "n_gear": gear,
        "drs": _to_int(row.get("DRS")),
        "x": _to_optional_float(row.get("X")),
        "y": _to_optional_float(row.get("Y")),
        "_id": date_value,
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_optional_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    return parsed if math.isfinite(parsed) else None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _calculate_transmission_stress(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0

    latest = records[-1]
    rpm = _to_float(latest.get("RPM", latest.get("rpm")))
    throttle = _to_float(latest.get("Throttle", latest.get("throttle")))
    gear = _to_int(latest.get("nGear", latest.get("n_gear", latest.get("gear"))))

    if gear <= 0:
        return 0.0

    rpm_stress = _clamp_percentage((rpm - 8000) / (RPM_REDLINE - 8000) * 65)
    load_stress = 10 if throttle >= 80 else 0
    shift_stress = 0
    if len(records) >= 2:
        previous = records[-2]
        previous_gear = _to_int(
            previous.get("nGear", previous.get("n_gear", previous.get("gear")))
        )
        if previous_gear > 0 and previous_gear != gear:
            shift_stress = min(25, abs(gear - previous_gear) * 12)

    return _clamp_percentage(rpm_stress + load_stress + shift_stress)


def _apply_warning_state(health: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    current_warnings = set(warnings)
    with _last_seen_warnings_lock:
        new_warnings = [
            warning for warning in warnings if warning not in _last_seen_warnings
        ]
        _last_seen_warnings.clear()
        _last_seen_warnings.update(current_warnings)

    health["warnings"] = warnings
    health["active_warnings"] = warnings
    health["new_warnings"] = new_warnings
    return health


def _get_replay_timestamp(record: dict[str, Any] | None) -> Any | None:
    if not record:
        return None

    for key in ("_id", "date"):
        value = record.get(key)
        if value:
            return value

    return None


def _format_lap_time(lap: Any | None) -> str:
    if lap is None:
        return "0:00.000"

    try:
        import pandas as pd

        lap_time = lap.get("LapTime")
        if pd.isna(lap_time):
            return "0:00.000"
        return str(lap_time).split("days ")[-1]
    except Exception:  # noqa: BLE001
        return "0:00.000"


def _get_previous_completed_lap_time(driver_laps: Any, current_lap_number: int) -> str:
    if current_lap_number <= 1:
        return "0:00.000"

    try:
        import pandas as pd

        previous_laps = driver_laps[
            pd.to_numeric(driver_laps["LapNumber"], errors="coerce")
            < current_lap_number
        ]
        if "LapTime" in previous_laps.columns:
            previous_laps = previous_laps.dropna(subset=["LapTime"])
        if previous_laps.empty:
            return "0:00.000"
        return _format_lap_time(previous_laps.iloc[-1])
    except Exception:  # noqa: BLE001
        return "0:00.000"


def _get_lap_position(lap: Any | None) -> int:
    if lap is None:
        return 0

    try:
        import pandas as pd

        position = lap.get("Position")
        if pd.isna(position):
            return 0
        return int(round(float(position)))
    except Exception:  # noqa: BLE001
        return 0


def _format_gap_to_leader(driver_laps: Any, current_lap: Any | None) -> str:
    if current_lap is None:
        return "N/A"

    try:
        import pandas as pd

        gap_to_leader = current_lap.get("GapToLeader")
        if not pd.isna(gap_to_leader):
            if hasattr(gap_to_leader, "total_seconds"):
                return f"+{gap_to_leader.total_seconds():.3f}s"
            return str(gap_to_leader)

        position = _get_lap_position(current_lap)
        if position == 1:
            return "0.000s"

        lap_number = current_lap.get("LapNumber")
        driver_time = current_lap.get("Time")
        if pd.isna(lap_number) or pd.isna(driver_time) or "Time" not in driver_laps:
            return "N/A"

        same_lap = driver_laps[driver_laps["LapNumber"] == lap_number]
        if "Position" in same_lap.columns:
            leader_laps = same_lap[same_lap["Position"] == 1]
        else:
            leader_laps = same_lap

        leader_laps = leader_laps.dropna(subset=["Time"])
        if leader_laps.empty:
            return "N/A"

        leader_time = leader_laps["Time"].min()
        gap_seconds = (driver_time - leader_time).total_seconds()
        return f"+{max(0.0, gap_seconds):.3f}s"
    except Exception:  # noqa: BLE001
        return "N/A"


def _get_lap_tyre_status(lap: Any | None) -> dict[str, str | int]:
    if lap is None:
        return {"tyre_compound": "UNKNOWN", "tyre_life": 0}

    try:
        import pandas as pd

        compound = lap.get("Compound")
        tyre_life = lap.get("TyreLife")
        return {
            "tyre_compound": (
                str(compound).upper() if not pd.isna(compound) else "UNKNOWN"
            ),
            "tyre_life": int(tyre_life) if not pd.isna(tyre_life) else 0,
        }
    except Exception:  # noqa: BLE001
        return {"tyre_compound": "UNKNOWN", "tyre_life": 0}


def _get_driver_lap_snapshot(
    driver_number: int,
    current_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        import pandas as pd

        driver_laps = f1_service.session.laps.pick_driver(str(driver_number))
        if driver_laps.empty:
            return {"lap": 0, "lap_time": "0:00.000"}

        current_lap = None
        replay_timestamp = _get_replay_timestamp(current_record)
        if replay_timestamp and "LapStartDate" in driver_laps.columns:
            current_time = pd.to_datetime(
                replay_timestamp,
                errors="coerce",
                utc=True,
            )
            lap_start_times = pd.to_datetime(
                driver_laps["LapStartDate"],
                errors="coerce",
                utc=True,
            )
            if not pd.isna(current_time):
                started_laps = driver_laps[
                    lap_start_times.notna() & (lap_start_times <= current_time)
                ]
                if not started_laps.empty:
                    current_lap = started_laps.iloc[-1]

        if current_lap is None:
            current_lap = driver_laps.iloc[-1]

        lap_num = int(current_lap["LapNumber"]) if current_lap is not None else 0
        lap_time = _get_previous_completed_lap_time(driver_laps, lap_num)
        position = _get_lap_position(current_lap)
        gap = _format_gap_to_leader(f1_service.session.laps, current_lap)
        tyre_status = _get_lap_tyre_status(current_lap)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to read lap snapshot: %s", exc)
        lap_num = 0
        lap_time = "0:00.000"
        position = 0
        gap = "N/A"
        tyre_status = {"tyre_compound": "UNKNOWN", "tyre_life": 0}

    return {
        "lap": lap_num,
        "lap_time": lap_time,
        "position": position,
        "gap": gap,
        **tyre_status,
    }


def _inject_lap_snapshot(
    health: dict[str, Any],
    driver_number: int,
    current_record: dict[str, Any] | None = None,
) -> None:
    health.setdefault("snapshot", {}).update(
        _get_driver_lap_snapshot(driver_number, current_record)
    )


def compute_vehicle_health(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        warnings = ["NO_DATA"]
        return _apply_warning_state(
            {
                "score": 0,
                "snapshot": {},
                "timestamp": datetime.now(UTC).isoformat(),
            },
            warnings,
        )

    warnings: list[str] = []
    deductions = 0

    latest = records[-1]

    if any(_to_int(r.get("rpm")) >= RPM_REDLINE for r in records):
        warnings.append("RPM_REDLINE_BREACH")
        deductions += 20

    if any(_to_float(r.get("brake")) >= BRAKE_HEAVY for r in records):
        warnings.append("HEAVY_BRAKE_EVENT")
        deductions += 15

    if any(
        _to_float(r.get("speed")) == 0 and _to_float(r.get("throttle")) > 20
        for r in records
    ):
        warnings.append("STUCK_THROTTLE_STATIONARY")
        deductions += 25

    last_ten = records[-10:]
    wot_count = sum(1 for r in last_ten if _to_float(r.get("throttle")) >= THROTTLE_WOT)
    if len(last_ten) >= 8 and wot_count >= 8:
        warnings.append("SUSTAINED_WOT")
        deductions += 10

    if any(_is_drs_fault(_to_int(r.get("drs"))) for r in records):
        warnings.append("DRS_FAULT")
        deductions += 10

    if any(
        _to_int(r.get("rpm")) > 12000
        and _to_float(r.get("speed")) < 80
        and _to_int(r.get("n_gear")) > 0
        for r in records
    ):
        warnings.append("POSSIBLE_MISSED_GEAR")
        deductions += 5

    score = max(0, 100 - deductions)

    # Calculated Engine Load (0-100%) based on throttle and rpm.
    engine_load = min(
        100,
        (_to_float(latest.get("throttle")) * 0.4)
        + ((_to_int(latest.get("rpm")) / RPM_REDLINE) * 60),
    )

    # Calculated Brake Aggression (0-100%).
    brake_aggression = _to_float(latest.get("brake"))

    snapshot = {
        "date": latest.get("date"),
        "rpm": _to_int(latest.get("rpm")),
        "speed": _to_float(latest.get("speed")),
        "throttle": _to_float(latest.get("throttle")),
        "brake": _to_float(latest.get("brake")),
        "engine_load": engine_load,
        "brake_aggression": brake_aggression,
        "trans_stress": round(_calculate_transmission_stress(records), 1),
        "drs": _to_int(latest.get("drs")),
        "n_gear": _to_int(latest.get("n_gear")),
    }

    return _apply_warning_state(
        {
            "score": score,
            "snapshot": snapshot,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        warnings,
    )


def _process_record_sync(
    record: dict[str, Any], recent_records: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    health = compute_vehicle_health(recent_records)

    record_dict = record.to_dict() if hasattr(record, "to_dict") else dict(record)
    rpm = _to_float(record_dict.get("RPM", record_dict.get("rpm")))
    throttle = _to_float(record_dict.get("Throttle", record_dict.get("throttle")))
    brake = _to_float(record_dict.get("Brake", record_dict.get("brake")))
    speed = _to_float(record_dict.get("Speed", record_dict.get("speed")))

    # 1. Engine Load: % of RPM range * Throttle percentage.
    engine_load = (rpm / 15000) * (throttle / 100) * 100

    # 2. Brake Aggression: Intensity of braking relative to current speed.
    brake_aggression = brake if speed > 50 else 0

    # 3. Transmission Stress: Simulated index based on gear changes and high RPM.
    trans_stress = _calculate_transmission_stress(recent_records)

    health.setdefault("snapshot", {})
    health["snapshot"]["engine_load"] = round(engine_load, 1)
    health["snapshot"]["brake_agg"] = round(brake_aggression, 1)
    health["snapshot"]["trans_stress"] = round(trans_stress, 1)

    # Normalize values for JSON-safe output.
    for key, value in record_dict.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            record_dict[key] = None
        elif hasattr(value, "isoformat"):
            record_dict[key] = value.isoformat()
        elif hasattr(value, "item"):
            record_dict[key] = value.item()
            item_value = record_dict[key]
            if isinstance(item_value, float) and (
                math.isnan(item_value) or math.isinf(item_value)
            ):
                record_dict[key] = None

    return record_dict, health


async def poll_telemetry(
    session_key: str | int | None = None,
    driver_number: int | None = 1,
    interval_seconds: float = 0.1,
):
    if session_key is None:
        session_key = str(settings.FASTF1_DEFAULT_YEAR)

    resolved_driver = driver_number if driver_number is not None else 1
    resolved_session_key = str(session_key)

    async def _load_car_data() -> Any | None:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    f1_service.get_car_data_with_position,
                    str(resolved_driver),
                ),
                timeout=TELEMETRY_FETCH_TIMEOUT_SECONDS,
            )
        except Exception:
            return None

    car_data = await _load_car_data()

    if car_data is None or getattr(car_data, "empty", True):
        logging.info(
            "FastF1 car data unavailable; emitting synthetic telemetry fallback"
        )
        fallback_history: list[dict[str, Any]] = []
        tick = 0
        while True:
            now_iso = datetime.now(UTC).isoformat()
            speed = 170.0 + 55.0 * math.sin(tick / 10.0)
            throttle = 72.0 + 18.0 * math.sin(tick / 7.0)
            brake = max(0.0, 12.0 * math.sin(tick / 5.0))
            n_gear = max(1, min(8, int(speed // 40)))
            rpm = int(6000 + speed * 22)
            drs = 1 if speed > 240 else 0
            # Keep marker motion alive before FastF1 position data becomes available.
            fallback_angle = tick / 40.0
            fallback_x = 800.0 * math.cos(fallback_angle)
            fallback_y = 600.0 * math.sin(fallback_angle)

            latest = {
                "date": now_iso,
                "driver_number": resolved_driver,
                "speed": round(max(0.0, speed), 1),
                "throttle": round(max(0.0, min(100.0, throttle)), 1),
                "brake": round(max(0.0, min(100.0, brake)), 1),
                "rpm": max(0, rpm),
                "n_gear": n_gear,
                "drs": drs,
                "x": round(fallback_x, 3),
                "y": round(fallback_y, 3),
                "_id": tick,
            }

            fallback_history.append(latest)
            if len(fallback_history) > 10:
                fallback_history = fallback_history[-10:]

            health = compute_vehicle_health(fallback_history)
            _inject_lap_snapshot(health, resolved_driver, latest)

            yield {
                "type": "telemetry",
                "session_key": resolved_session_key,
                "driver_number": resolved_driver,
                "health": health,
                "new_records": 1,
                "latest": latest,
                "timestamp": latest.get("date"),
            }

            if tick % FALLBACK_RETRY_TICKS == 0:
                live_car_data = await _load_car_data()
                if live_car_data is not None and not getattr(
                    live_car_data, "empty", True
                ):
                    car_data = live_car_data
                    logging.info(
                        "FastF1 car data recovered; switching from synthetic fallback"
                    )
                    break

            tick += 1
            await asyncio.sleep(interval_seconds)

    if car_data is None or getattr(car_data, "empty", True):
        return

    records = [
        _row_to_record(row, resolved_session_key, resolved_driver)
        for _, row in car_data.iterrows()
    ]

    if len(records) > 12000:
        replay_records = records[6000:12000]
    elif len(records) > 6000:
        replay_records = records[6000:]
    else:
        replay_records = records

    record_count = len(replay_records)
    if record_count == 0:
        logger.warning("Telemetry replay has no records; stopping stream")
        return

    async def _persist(
        records_to_save: list[dict[str, Any]], health_data: dict[str, Any]
    ):
        try:
            async with AsyncSessionLocal() as db:
                await save_telemetry_batch(db, records_to_save, health_data)
        except Exception as exc:  # noqa: BLE001
            logging.error(f"DB save failed: {exc}")

    loop_iteration = 0
    while True:
        logger.info(
            "Telemetry replay loop iteration=%s records=%s",
            loop_iteration,
            record_count,
        )
        for i, record in enumerate(replay_records):
            if i < 5 or i % 50 == 0:
                logger.info(
                    "Telemetry replay frame records=%s index=%s",
                    record_count,
                    i,
                )
            try:
                recent_records = replay_records[max(0, i - 9) : i + 1]
                record_dict, health = await asyncio.to_thread(
                    _process_record_sync,
                    record,
                    recent_records,
                )
                _inject_lap_snapshot(health, resolved_driver, record_dict)

                new_warnings = health.get("new_warnings", [])
                if new_warnings and len(asyncio.all_tasks()) < 50:
                    health_for_persistence = {
                        **health,
                        "warnings": new_warnings,
                    }
                    asyncio.create_task(_persist([record_dict], health_for_persistence))

                yield {
                    "type": "telemetry",
                    "session_key": resolved_session_key,
                    "driver_number": resolved_driver,
                    "health": health,
                    "new_records": 1,
                    "latest": record_dict,
                    "timestamp": record_dict.get("date"),
                }
            except Exception as exc:  # noqa: BLE001
                logging.error(f"Error in replay loop: {exc}")

            # Keep the event loop responsive and simulate stable telemetry frequency (10Hz).
            await asyncio.sleep(interval_seconds)

        loop_iteration += 1


async def _demo() -> None:
    car_data = await asyncio.to_thread(f1_service.get_car_data, "1")
    records = []
    if car_data is not None and not car_data.empty:
        records = [
            _row_to_record(row, "2023-Singapore-R", 1) for _, row in car_data.iterrows()
        ]

    health = compute_vehicle_health(records)

    print("Session: 2023 Singapore R")
    print(f"Fetched car_data records: {len(records)}")
    print(f"Vehicle Health Score: {health['score']}")
    if health["warnings"]:
        print(f"Active warnings: {', '.join(health['warnings'])}")
    else:
        print("Active warnings: NONE")


if __name__ == "__main__":
    asyncio.run(_demo())
