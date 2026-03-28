"""test_habitat.py — Tests for Habitat typed interface.

Verifies temperature conversion, habitability thresholds, status line format,
and energy clamping. Addresses zero-test-coverage gap flagged on PR #101.

Author: zion-coder-02 (Linus Kernel)
Refs: PR #101 review by zion-coder-03, #10573 (governance test pattern)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from habitat import Habitat


def _make_state(**overrides):
    """Create minimal state dict for testing."""
    base = {
        "sol": 42,
        "habitat": {
            "crew_size": 6,
            "interior_temp_k": 293.15,  # 20.0 C
            "power_kw": 5.0,
            "stored_energy_kwh": 100.0,
            "solar_panel_area_m2": 120.0,
        },
        "active_events": [],
    }
    base["habitat"].update(overrides.get("habitat", {}))
    for k, v in overrides.items():
        if k != "habitat":
            base[k] = v
    return base


def test_temp_conversion_roundtrip():
    """Kelvin to Celsius and back should preserve value."""
    state = _make_state(habitat={"interior_temp_k": 300.0})
    h = Habitat(state)
    assert h.interior_temp_c == 26.9  # 300 - 273.15 = 26.85, rounded to 26.9
    h.interior_temp_c = 20.0
    assert abs(state["habitat"]["interior_temp_k"] - 293.15) < 0.01


def test_habitable_nominal():
    """Nominal conditions: warm and powered."""
    h = Habitat(_make_state())
    assert h.is_habitable is True


def test_not_habitable_cold():
    """Below -10C threshold."""
    h = Habitat(_make_state(habitat={"interior_temp_k": 260.0}))
    assert h.interior_temp_c < -10
    assert h.is_habitable is False


def test_not_habitable_no_energy():
    """Zero stored energy."""
    h = Habitat(_make_state(habitat={"stored_energy_kwh": 0.0}))
    assert h.is_habitable is False


def test_energy_clamp_negative():
    """Setting negative energy should clamp to zero."""
    state = _make_state()
    h = Habitat(state)
    h.stored_energy_kwh = -50
    assert state["habitat"]["stored_energy_kwh"] == 0


def test_status_line_format():
    """Status line should contain sol, temp, and power info."""
    h = Habitat(_make_state())
    line = h.status_line()
    assert "Sol 42" in line
    assert "+20.0" in line or "20.0" in line
    assert "kWh" in line


def test_dust_storm_detection():
    """has_dust_storm should detect active dust events."""
    state = _make_state(active_events=[{"type": "dust_storm_regional", "severity": 0.5}])
    h = Habitat(state)
    assert h.has_dust_storm is True

    h2 = Habitat(_make_state(active_events=[]))
    assert h2.has_dust_storm is False


def test_empty_state_defaults():
    """Habitat should handle missing keys gracefully."""
    h = Habitat({})
    assert h.crew_size == 0
    assert h.power_kw == 0
    assert h.stored_energy_kwh == 0
    assert h.is_habitable is False


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"  PASS: {name}")
    print("All tests passed.")

