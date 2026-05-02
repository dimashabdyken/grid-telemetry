from backend.services.thermal_engine import (
    calc_cockpit_temp,
    calc_cognitive_load,
    calc_pcm_load,
    calc_seebeck_watts,
    get_thermal_alert,
)


def test_cockpit_temp_increases_with_lap_and_load() -> None:
    cool_run = calc_cockpit_temp(29.0, lap=1, speed=280.0, rpm=8000.0, brake=0.0)
    hot_run = calc_cockpit_temp(29.0, lap=20, speed=90.0, rpm=11500.0, brake=80.0)

    assert hot_run > cool_run


def test_cockpit_temp_is_bounded() -> None:
    assert calc_cockpit_temp(-20.0, lap=-5, speed=500.0) >= 18.0
    assert calc_cockpit_temp(80.0, lap=200, speed=0.0, rpm=20000.0, brake=100.0) <= 65.0


def test_seebeck_scales_with_brake_and_speed() -> None:
    low_recovery = calc_seebeck_watts(brake=20.0, speed=120.0)
    high_recovery = calc_seebeck_watts(brake=80.0, speed=280.0)

    assert high_recovery > low_recovery
    assert 0.0 <= high_recovery <= 10_000.0


def test_cognitive_load_and_pcm_are_bounded() -> None:
    assert 0.0 <= calc_cognitive_load(cockpit_temp=30.0, lap=1) <= 100.0
    assert 0.0 <= calc_cognitive_load(cockpit_temp=60.0, lap=100) <= 100.0
    assert 0.0 <= calc_pcm_load(lap=1, cockpit_temp=30.0) <= 100.0
    assert 0.0 <= calc_pcm_load(lap=100, cockpit_temp=60.0) <= 100.0


def test_thermal_alert_thresholds() -> None:
    assert get_thermal_alert(cockpit_temp=35.0, cognitive_load=40.0) == "none"
    assert get_thermal_alert(cockpit_temp=43.0, cognitive_load=60.0) == "warning"
    assert get_thermal_alert(cockpit_temp=49.0, cognitive_load=60.0) == "critical"
    assert get_thermal_alert(cockpit_temp=35.0, cognitive_load=86.0) == "critical"
