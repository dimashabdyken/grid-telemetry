from __future__ import annotations

from pydantic import BaseModel, Field


class TelemetryRecordSchema(BaseModel):
    date: str
    driver_number: int
    speed: float | None
    throttle: float | None
    brake: float | None
    rpm: int | None
    n_gear: int | None
    drs: int | None
    id: int = Field(alias="_id")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }
