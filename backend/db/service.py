"""Database service helpers for telemetry persistence and retrieval."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import WARNING_SEVERITY_MAP, TelemetryRecord, WarningEvent


async def save_telemetry_batch(
    db: AsyncSession,
    records: list[dict],
    health: dict,
) -> None:
    """Persist telemetry records and derived warning events in one transaction."""
    telemetry_rows: list[TelemetryRecord] = []
    warning_rows: list[WarningEvent] = []

    warnings = health.get("warnings") or []
    warnings_json = json.dumps(warnings)
    health_score = int(health.get("health_score", health.get("score", 0)))

    for record in records:
        session_key = str(record.get("session_key", ""))
        driver_number = int(record.get("driver_number", 0))
        raw_id = record.get("_id")
        if isinstance(raw_id, datetime):
            recorded_at = raw_id
        elif hasattr(raw_id, "generation_time"):
            recorded_at = raw_id.generation_time.replace(tzinfo=None)
        else:
            recorded_at = datetime.utcnow()

        telemetry_rows.append(
            TelemetryRecord(
                session_key=session_key,
                driver_number=driver_number,
                speed=record.get("speed"),
                throttle=record.get("throttle"),
                brake=record.get("brake"),
                rpm=record.get("rpm"),
                gear=record.get("gear"),
                drs=record.get("drs"),
                health_score=health_score,
                warnings=warnings_json,
                recorded_at=recorded_at,
            )
        )

        if warnings:
            for code in warnings:
                warning_rows.append(
                    WarningEvent(
                        session_key=session_key,
                        driver_number=driver_number,
                        code=str(code),
                        severity=WARNING_SEVERITY_MAP.get(str(code), "LOW"),
                        triggered_at=recorded_at,
                    )
                )

    db.add_all(telemetry_rows + warning_rows)
    await db.commit()


async def get_historical_telemetry(
    db: AsyncSession,
    session_key: str,
    driver_number: int,
    limit: int = 1000,
) -> list[TelemetryRecord]:
    """Return recent telemetry records ordered from newest to oldest."""
    stmt = (
        select(TelemetryRecord)
        .where(TelemetryRecord.session_key == session_key)
        .where(TelemetryRecord.driver_number == driver_number)
        .order_by(TelemetryRecord.recorded_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())