from __future__ import annotations


DEFAULT_AMBIENT_TEMP_C = 29.0
MAX_SEEBECK_WATTS = 10_000.0


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def calc_cockpit_temp(
    ambient_temp: float,
    lap: int,
    speed: float,
    rpm: float = 0.0,
    brake: float = 0.0,
) -> float:
    lap_heat = max(0, lap) * 0.18
    low_speed_heat = max(0.0, 180.0 - speed) * 0.018
    rpm_heat = max(0.0, rpm - 9000.0) * 0.00055
    brake_heat = _clamp(brake, 0.0, 100.0) * 0.025
    airflow_cooling = min(5.0, max(0.0, speed) * 0.012)

    cockpit_temp = (
        ambient_temp
        + lap_heat
        + low_speed_heat
        + rpm_heat
        + brake_heat
        - airflow_cooling
    )
    return round(_clamp(cockpit_temp, 18.0, 65.0), 1)


def calc_seebeck_watts(brake: float, speed: float) -> float:
    brake_energy = _clamp(brake, 0.0, 100.0) / 100.0
    speed_factor = _clamp(speed, 0.0, 360.0) / 360.0

    return round(_clamp(brake_energy * speed_factor * MAX_SEEBECK_WATTS, 0.0, MAX_SEEBECK_WATTS), 1)


def calc_cognitive_load(cockpit_temp: float, lap: int) -> float:
    heat_load = max(0.0, cockpit_temp - 32.0) * 4.2
    stint_load = max(0, lap) * 0.9

    return round(_clamp(18.0 + heat_load + stint_load, 0.0, 100.0), 1)


def calc_pcm_load(lap: int, cockpit_temp: float) -> float:
    lap_load = max(0, lap) * 1.15
    heat_load = max(0.0, cockpit_temp - 30.0) * 2.4

    return round(_clamp(lap_load + heat_load, 0.0, 100.0), 1)


def get_thermal_alert(cockpit_temp: float, cognitive_load: float) -> str:
    if cockpit_temp >= 48.0 or cognitive_load >= 85.0:
        return "critical"
    if cockpit_temp >= 42.0 or cognitive_load >= 70.0:
        return "warning"
    return "none"
