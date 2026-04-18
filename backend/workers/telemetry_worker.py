from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import requests

from backend.db.base import AsyncSessionLocal
from backend.db.service import save_telemetry_batch

OPENF1_BASE = "https://api.openf1.org/v1"
RPM_REDLINE = 14500
THROTTLE_WOT = 95
BRAKE_HEAVY = 90
DRS_FAULT_CODES = {14}


def _get_car_data_sync(
    session_key: str | int, driver_number: int | None = None
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number

    response = requests.get(f"{OPENF1_BASE}/car_data", params=params, timeout=10)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _get_session_sync(session_key: str | int = "latest") -> dict[str, Any]:
    params: dict[str, Any] = {}
    if session_key != "latest":
        params["session_key"] = session_key

    response = requests.get(f"{OPENF1_BASE}/sessions", params=params, timeout=10)
    response.raise_for_status()
    sessions = response.json()
    if not isinstance(sessions, list) or not sessions:
        return {}
    return sessions[-1]


def _get_drivers_sync(session_key: str | int) -> list[dict[str, Any]]:
    response = requests.get(
        f"{OPENF1_BASE}/drivers",
        params={"session_key": session_key},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


async def fetch_car_data(
    session_key: str | int, driver_number: int | None = None
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_get_car_data_sync, session_key, driver_number)


async def fetch_session(session_key: str | int = "latest") -> dict[str, Any]:
    return await asyncio.to_thread(_get_session_sync, session_key)


async def fetch_drivers(session_key: str | int) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_get_drivers_sync, session_key)


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
    session_key: str | int = "latest",
    driver_number: int | None = None,
    interval_seconds: float = 1.5,
):
    seen_ids: set[Any] = set()

    resolved_session_key = session_key
    if session_key == "latest":
        session = await fetch_session("latest")
        resolved_session_key = session.get("session_key", "latest")

    while True:
        try:
            records = await fetch_car_data(
                resolved_session_key, driver_number=driver_number
            )

            new_records: list[dict[str, Any]] = []
            for record in records:
                record_id = record.get("_id")
                if record_id is None:
                    new_records.append(record)
                    continue
                if record_id in seen_ids:
                    continue
                seen_ids.add(record_id)
                new_records.append(record)

            if new_records:
                health = compute_vehicle_health(new_records)

                async def _persist(records_to_save, health_data):
                    try:
                        async with AsyncSessionLocal() as db:
                            await save_telemetry_batch(db, records_to_save, health_data)
                    except Exception as e:
                        logging.error(f"DB save failed: {e}")

                asyncio.create_task(_persist(new_records, health))

                yield {
                    "type": "telemetry",
                    "session_key": resolved_session_key,
                    "driver_number": driver_number,
                    "health": health,
                    "new_records": len(new_records),
                    "latest": new_records[-1],
                }
        except Exception as exc:  # noqa: BLE001
            yield {"type": "error", "message": str(exc)}

        await asyncio.sleep(interval_seconds)


async def _demo() -> None:
    session = await fetch_session("latest")
    session_key = session.get("session_key", "latest")
    session_name = session.get("session_name", "UNKNOWN")
    session_date = session.get("date_start", "UNKNOWN")

    records = await fetch_car_data(session_key)
    health = compute_vehicle_health(records)

    print(f"Session: {session_name} ({session_date})")
    print(f"Fetched car_data records: {len(records)}")
    print(f"Vehicle Health Score: {health['score']}")
    if health["warnings"]:
        print(f"Active warnings: {', '.join(health['warnings'])}")
    else:
        print("Active warnings: NONE")


if __name__ == "__main__":
    asyncio.run(_demo())
