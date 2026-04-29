from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, datetime
from typing import Any

from backend.core.config import settings
from backend.db.base import AsyncSessionLocal
from backend.db.service import save_telemetry_batch
from backend.services.f1_service import f1_service

logger = logging.getLogger(__name__)

RPM_REDLINE = 14500
THROTTLE_WOT = 100
BRAKE_HEAVY = 90
DRS_FAULT_CODES: set[int] = set()
DRS_RECOGNIZED_CODES = {0, 1, 8, 10, 12, 14}
DRS_ACTIVE_CODES = {10, 12, 14}
REPLAY_WINDOW_SIZE = 600
REPLAY_WINDOW_STRIDE_DIVISOR = 6
REPLAY_DRS_ACTIVE_SAMPLE_BONUS = 3.0
TELEMETRY_FETCH_TIMEOUT_SECONDS = 2.0
FALLBACK_RETRY_TICKS = 20


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
    except TypeError, ValueError:
        return default


def _to_optional_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except TypeError, ValueError:
        return None

    return parsed if math.isfinite(parsed) else None


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        return default


def compute_vehicle_health(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "score": 0,
            "warnings": ["NO_DATA"],
            "snapshot": {},
            "timestamp": datetime.now(UTC).isoformat(),
        }

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
        "drs": _to_int(latest.get("drs")),
        "n_gear": _to_int(latest.get("n_gear")),
    }

    return {
        "score": score,
        "warnings": warnings,
        "snapshot": snapshot,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _process_record_sync(
    record: dict[str, Any], recent_records: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    health = compute_vehicle_health(recent_records)

    record_dict = record.to_dict() if hasattr(record, "to_dict") else dict(record)
    rpm = _to_float(record_dict.get("RPM", record_dict.get("rpm")))
    throttle = _to_float(record_dict.get("Throttle", record_dict.get("throttle")))
    brake = _to_float(record_dict.get("Brake", record_dict.get("brake")))
    speed = _to_float(record_dict.get("Speed", record_dict.get("speed")))
    gear = _to_int(record_dict.get("nGear", record_dict.get("n_gear")))

    # 1. Engine Load: % of RPM range * Throttle percentage.
    engine_load = (rpm / 15000) * (throttle / 100) * 100

    # 2. Brake Aggression: Intensity of braking relative to current speed.
    brake_aggression = brake if speed > 50 else 0

    # 3. Transmission Stress: Simulated index based on gear changes and high RPM.
    trans_stress = 0
    if gear > 0 and rpm > 13000:
        trans_stress = 80

    health.setdefault("snapshot", {})
    health["snapshot"]["engine_load"] = round(engine_load, 1)
    health["snapshot"]["brake_agg"] = round(brake_aggression, 1)
    health["snapshot"]["trans_stress"] = trans_stress

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


def _select_replay_window(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(records) <= REPLAY_WINDOW_SIZE:
        return records

    window_size = REPLAY_WINDOW_SIZE
    max_start = len(records) - window_size
    stride = max(1, window_size // REPLAY_WINDOW_STRIDE_DIVISOR)

    speeds = [max(0.0, _to_float(record.get("speed"))) for record in records]
    prefix_sum = [0.0]
    drs_active_prefix_sum = [0]
    for speed in speeds:
        prefix_sum.append(prefix_sum[-1] + speed)
    for record in records:
        drs_active_prefix_sum.append(
            drs_active_prefix_sum[-1] + int(is_drs_active(_to_int(record.get("drs"))))
        )

    best_start = max_start  # default to most recent for recency
    best_score = -1.0
    for start in range(0, max_start + 1, stride):
        window_total = prefix_sum[start + window_size] - prefix_sum[start]
        avg_speed = window_total / window_size
        drs_active_count = (
            drs_active_prefix_sum[start + window_size] - drs_active_prefix_sum[start]
        )
        # Prefer racing-like pace but slightly bias toward newer segments.
        recency_bonus = (start / max_start) * 5.0 if max_start > 0 else 0.0
        drs_bonus = drs_active_count * REPLAY_DRS_ACTIVE_SAMPLE_BONUS
        score = avg_speed + recency_bonus + drs_bonus
        if score > best_score:
            best_score = score
            best_start = start

    replay_slice = records[best_start : best_start + window_size]
    logging.info(
        "Replay window selected at index %s (size=%s, avg_speed=%.1f km/h, drs_active_samples=%s)",
        best_start,
        window_size,
        sum(_to_float(item.get("speed")) for item in replay_slice) / window_size,
        sum(1 for item in replay_slice if is_drs_active(_to_int(item.get("drs")))),
    )
    return replay_slice


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

            yield {
                "type": "telemetry",
                "session_key": resolved_session_key,
                "driver_number": resolved_driver,
                "health": compute_vehicle_health(fallback_history),
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

    # Pick a representative high-pace contiguous segment for better replay realism.
    replay_records = _select_replay_window(records)
    record_count = len(replay_records)
    if record_count == 0:
        logger.warning(
            "Telemetry replay has no records after window selection; stopping stream"
        )
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

                if len(asyncio.all_tasks()) < 50:
                    asyncio.create_task(_persist([record_dict], health))

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
