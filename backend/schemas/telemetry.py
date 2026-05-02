from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ThermalState(BaseModel):
    cockpit_temp: float
    seebeck_watts: float
    cognitive_load: float
    pcm_load: float
    thermal_alert: Literal["none", "warning", "critical"]
    auto_mode: bool = False
    predicted_pcm_saturation_laps: float | None = None
    thermal_risk_laps: float | None = None
    drivers: list[str] = Field(default_factory=list)


class TelemetryRecordSchema(BaseModel):
    date: str
    driver_number: int
    speed: float | None
    throttle: float | None
    brake: float | None
    rpm: int | None
    n_gear: int | None
    drs: int | None
    x: float | None = None
    y: float | None = None
    id: int = Field(alias="_id")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }
