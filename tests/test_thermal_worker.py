from backend.workers.telemetry_worker import (
    _compute_thermal_state,
    _get_thermal_warning_codes,
    _merge_live_warnings,
)


def _thermal_series(
    *,
    speed: float,
    rpm: float,
    brake: float,
    ticks: int,
) -> tuple[dict, set[str]]:
    pcm_load: float | None = None
    all_warnings: set[str] = set()
    thermal = {}

    for tick in range(ticks):
        health = {"snapshot": {"lap": 1 + tick // 2}}
        latest = {"speed": speed, "rpm": rpm, "brake": brake}
        thermal = _compute_thermal_state(latest, health, pcm_load)
        pcm_load = float(thermal["pcm_load"])
        all_warnings.update(_get_thermal_warning_codes(thermal))

    return thermal, all_warnings


def test_fast_cool_stint_does_not_trigger_thermal_alarm() -> None:
    thermal, warnings = _thermal_series(speed=280.0, rpm=9000.0, brake=10.0, ticks=40)

    assert thermal["thermal_alert"] == "none"
    assert not {"THERMAL_WARNING", "PCM_SATURATED", "COGNITIVE_DEGRADED"} & warnings


def test_hot_slow_stint_eventually_triggers_pcm_and_cognitive_risk() -> None:
    thermal, warnings = _thermal_series(speed=80.0, rpm=12500.0, brake=90.0, ticks=120)

    assert thermal["auto_mode"] is True
    assert thermal["thermal_alert"] == "critical"
    assert "PCM_SATURATED" in warnings
    assert "COGNITIVE_DEGRADED" in warnings


def test_seebeck_active_is_not_promoted_to_live_master_warning() -> None:
    health = {"warnings": [], "active_warnings": [], "new_warnings": []}

    _merge_live_warnings(health, ["SEEBECK_ACTIVE", "THERMAL_WARNING"])

    assert "SEEBECK_ACTIVE" not in health["warnings"]
    assert "THERMAL_WARNING" in health["warnings"]
