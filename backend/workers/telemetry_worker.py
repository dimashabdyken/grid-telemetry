from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, datetime
from typing import Any

import fastf1

from backend.db.base import AsyncSessionLocal
from backend.db.service import save_telemetry_batch

RPM_REDLINE = 14500
THROTTLE_WOT = 95
BRAKE_HEAVY = 90
DRS_FAULT_CODES = {14}

fastf1.Cache.enable_cache("./cache")
FASTF1_YEAR = 2023
FASTF1_EVENT = "Singapore"
FASTF1_SESSION = "R"

_FASTF1_SESSION: Any | None = None
_FASTF1_LOAD_TASK: asyncio.Task[Any] | None = None


def initialize_fastf1_session() -> Any:
    global _FASTF1_SESSION
    if _FASTF1_SESSION is None:
        session = fastf1.get_session(FASTF1_YEAR, FASTF1_EVENT, FASTF1_SESSION)
        try:
            session.load(telemetry=True, laps=False, weather=False)
        except Exception:
            fastf1.Cache.clear_cache("./cache")
            raise
        _FASTF1_SESSION = session
    return _FASTF1_SESSION


async def get_fastf1_session() -> Any:
    global _FASTF1_SESSION
    global _FASTF1_LOAD_TASK

    if _FASTF1_SESSION is not None:
        return _FASTF1_SESSION

    if _FASTF1_LOAD_TASK is None:
        _FASTF1_LOAD_TASK = asyncio.create_task(
            asyncio.to_thread(initialize_fastf1_session)
        )

    try:
        _FASTF1_SESSION = await _FASTF1_LOAD_TASK
        return _FASTF1_SESSION
    finally:
        if _FASTF1_SESSION is not None:
            _FASTF1_LOAD_TASK = None


try:
    initialize_fastf1_session()
except Exception as exc:  # noqa: BLE001
    logging.warning(f"FastF1 global preload failed, will retry lazily: {exc}")


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


async def poll_telemetry(
    session_key: str | int = 9161,
    driver_number: int | None = 1,
    interval_seconds: float = 1.5,
):
    resolved_driver = driver_number if driver_number is not None else 1
    resolved_session_key = str(session_key)

    await get_fastf1_session()
    session = _FASTF1_SESSION
    if session is None:
        raise RuntimeError("FastF1 session is not initialized")

    # Matches the requested baseline retrieval of historical telemetry.
    car_data = _FASTF1_SESSION.car_data.get("1")
    if resolved_driver != 1:
        driver_car_data = _FASTF1_SESSION.car_data.get(str(resolved_driver))
        if driver_car_data is not None and not driver_car_data.empty:
            car_data = driver_car_data

    if car_data is None or car_data.empty:
        logging.warning("FastF1 returned no car data for requested driver")
        while True:
            yield {
                "type": "telemetry",
                "session_key": resolved_session_key,
                "driver_number": resolved_driver,
                "health": {"score": 0, "warnings": ["NO_DATA"], "snapshot": {}},
                "new_records": 0,
                "latest": {},
            }
            await asyncio.sleep(5)

    records = [
        _row_to_record(row, resolved_session_key, resolved_driver)
        for _, row in car_data.iterrows()
    ]

    async def _persist(
        records_to_save: list[dict[str, Any]], health_data: dict[str, Any]
    ):
        try:
            async with AsyncSessionLocal() as db:
                await save_telemetry_batch(db, records_to_save, health_data)
        except Exception as exc:  # noqa: BLE001
            logging.error(f"DB save failed: {exc}")

    while True:
        for i, record in enumerate(records):
            try:
                recent_records = records[max(0, i - 9) : i + 1]
                health = compute_vehicle_health(recent_records)

                # Convert record to dict
                record_dict = (
                    record.to_dict() if hasattr(record, "to_dict") else dict(record)
                )

                # Fix serialization: convert Timestamp/datetime and numpy scalars.
                for key, value in record_dict.items():
                    if isinstance(value, float) and (
                        math.isnan(value) or math.isinf(value)
                    ):
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

                asyncio.create_task(_persist([record_dict], health))

                yield {
                    "type": "telemetry",
                    "session_key": resolved_session_key,
                    "driver_number": resolved_driver,
                    "health": health,
                    "new_records": 1,
                    "latest": record_dict,
                }

                await asyncio.sleep(interval_seconds)
            except Exception as exc:  # noqa: BLE001
                logging.error(f"Error in replay loop: {exc}")
                await asyncio.sleep(1)

        logging.info("Restarting telemetry replay loop...")


async def _demo() -> None:
    session = await get_fastf1_session()
    car_data = session.car_data.get("1")
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
