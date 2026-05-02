"""Database ORM models for telemetry persistence."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


def utcnow() -> datetime:
    """Return current UTC timestamp for model defaults."""
    return datetime.utcnow()


WARNING_SEVERITY_MAP: dict[str, str] = {
    "NO_DATA": "CRITICAL",
    "RPM_REDLINE_BREACH": "HIGH",
    "STUCK_THROTTLE_STATIONARY": "HIGH",
    "HEAVY_BRAKE_EVENT": "MEDIUM",
    "DRS_FAULT": "MEDIUM",
    "SUSTAINED_WOT": "LOW",
    "POSSIBLE_MISSED_GEAR": "LOW",
    "THERMAL_WARNING": "HIGH",
    "PCM_SATURATED": "MEDIUM",
    "COGNITIVE_DEGRADED": "HIGH",
    "SEEBECK_ACTIVE": "LOW",
}


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_key: Mapped[str] = mapped_column(String(64), index=True)
    driver_number: Mapped[int] = mapped_column(Integer, index=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    throttle: Mapped[float | None] = mapped_column(Float, nullable=True)
    brake: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gear: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False)
    warnings: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=utcnow,
        index=True,
        nullable=False,
    )


class WarningEvent(Base):
    __tablename__ = "warning_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_key: Mapped[str] = mapped_column(String(64), index=True)
    driver_number: Mapped[int] = mapped_column(Integer, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=utcnow,
        index=True,
        nullable=False,
    )
