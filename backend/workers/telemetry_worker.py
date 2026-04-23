from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, datetime
from typing import Any

from backend.db.base import AsyncSessionLocal
from backend.db.service import save_telemetry_batch
from backend.services.f1_service import f1_service

RPM_REDLINE = 14500
THROTTLE_WOT = 95
BRAKE_HEAVY = 90
DRS_FAULT_CODES = {14}
REPLAY_WINDOW_SIZE = 600
REPLAY_WINDOW_STRIDE_DIVISOR = 6
TELEMETRY_FETCH_TIMEOUT_SECONDS = 2.0


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
        "x": _to_float(row.get("X", 0.0)),
        "y": _to_float(row.get("Y", 0.0)),
        "_id": date_value,
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except TypeError, ValueError:
        return default


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

    if any(_to_int(r.get("drs")) in DRS_FAULT_CODES for r in records):
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

    snapshot = {
        "date": latest.get("date"),
        "rpm": _to_int(latest.get("rpm")),
        "speed": _to_float(latest.get("speed")),
        "throttle": _to_float(latest.get("throttle")),
        "brake": _to_float(latest.get("brake")),
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
    for speed in speeds:
        prefix_sum.append(prefix_sum[-1] + speed)

    best_start = max_start  # default to most recent for recency
    best_score = -1.0
    for start in range(0, max_start + 1, stride):
        window_total = prefix_sum[start + window_size] - prefix_sum[start]
        avg_speed = window_total / window_size
        # Prefer racing-like pace but slightly bias toward newer segments.
        recency_bonus = (start / max_start) * 5.0 if max_start > 0 else 0.0
        score = avg_speed + recency_bonus
        if score > best_score:
            best_score = score
            best_start = start

    replay_slice = records[best_start : best_start + window_size]
    logging.info(
        "Replay window selected at index %s (size=%s, avg_speed=%.1f km/h)",
        best_start,
        window_size,
        sum(_to_float(item.get("speed")) for item in replay_slice) / window_size,
    )
    return replay_slice


async def poll_telemetry(
    session_key: str | int = 9161,
    driver_number: int | None = 1,
    interval_seconds: float = 0.15,
):
    resolved_driver = driver_number if driver_number is not None else 1
    resolved_session_key = str(session_key)

    try:
        car_data = await asyncio.wait_for(
            asyncio.to_thread(f1_service.get_car_data, str(resolved_driver)),
            timeout=TELEMETRY_FETCH_TIMEOUT_SECONDS,
        )
    except Exception:
        car_data = None

    if car_data is None or car_data.empty:
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

            latest = {
                "date": now_iso,
                "driver_number": resolved_driver,
                "speed": round(max(0.0, speed), 1),
                "throttle": round(max(0.0, min(100.0, throttle)), 1),
                "brake": round(max(0.0, min(100.0, brake)), 1),
                "rpm": max(0, rpm),
                "n_gear": n_gear,
                "drs": drs,
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
            }
            tick += 1
            await asyncio.sleep(interval_seconds)

    records = [
        _row_to_record(row, resolved_session_key, resolved_driver)
        for _, row in car_data.iterrows()
    ]

    # Pick a representative high-pace contiguous segment for better replay realism.
    replay_records = _select_replay_window(records)

    async def _persist(
        records_to_save: list[dict[str, Any]], health_data: dict[str, Any]
    ):
        try:
            async with AsyncSessionLocal() as db:
                await save_telemetry_batch(db, records_to_save, health_data)
        except Exception as exc:  # noqa: BLE001
            logging.error(f"DB save failed: {exc}")

    while True:
        for i, record in enumerate(replay_records):
            try:
                recent_records = replay_records[max(0, i - 9) : i + 1]
                record_dict, health = await asyncio.to_thread(
                    _process_record_sync,
                    record,
                    recent_records,
                )

                asyncio.create_task(_persist([record_dict], health))

                yield {
                    "type": "telemetry",
                    "session_key": resolved_session_key,
                    "driver_number": resolved_driver,
                    "health": health,
                    "new_records": 1,
                    "latest": record_dict,
                }

                # Keep the event loop responsive for websocket heartbeat tasks.
                await asyncio.sleep(0.01)
                await asyncio.sleep(interval_seconds)
            except Exception as exc:  # noqa: BLE001
                logging.error(f"Error in replay loop: {exc}")
                await asyncio.sleep(1)

        logging.info("Restarting telemetry replay loop...")


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
