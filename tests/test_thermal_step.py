"""Tests for thermal_step() — the function that was missing.

Verifies that the thermal simulation loop produces physically
reasonable results with constants.py values.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from thermal import thermal_step, habitat_thermal_balance, calculate_required_heating
from constants import (
    HABITAT_EMISSIVITY,
    HABITAT_INSULATION_R_VALUE,
    HABITAT_TARGET_TEMP_K,
    MARS_SURFACE_TEMP_K,
)


def test_thermal_step_returns_dict():
    """thermal_step must return a dict with required keys."""
    result = thermal_step(293.0, 210.0, 0.0, 8000.0)
    assert isinstance(result, dict)
    assert "interior_temp_k" in result
    assert "net_power_w" in result
    assert "heating_w" in result


def test_thermal_step_heater_warms():
    """With heater on and no solar, interior should warm or hold steady."""
    result = thermal_step(280.0, 210.0, 0.0, 8000.0, dt_seconds=900)
    assert result["interior_temp_k"] >= 280.0, "Heater should warm the habitat"


def test_thermal_step_no_heat_cools():
    """With no heater and no solar, interior should cool toward exterior."""
    result = thermal_step(293.0, 210.0, 0.0, 0.0, dt_seconds=3600)
    assert result["interior_temp_k"] < 293.0, "No heating should let habitat cool"


def test_emissivity_uses_constants():
    """Verify low-e coating value from constants.py is used."""
    assert HABITAT_EMISSIVITY == 0.05, f"Expected 0.05, got {HABITAT_EMISSIVITY}"


def test_required_heating_reasonable():
    """Required heating at night should be under 10 kW with low-e coating."""
    req = calculate_required_heating(MARS_SURFACE_TEMP_K, 0.0)
    assert req < 10000.0, f"Required heating {req:.0f}W exceeds 10kW — check emissivity"
    assert req > 0.0, "Some heating always needed at -63C"


def test_thermal_balance_net_positive_with_heater():
    """With 8kW heater, net power should be positive at reasonable temps."""
    net = habitat_thermal_balance(210.0, 293.0, 0.0, active_heating_w=8000.0)
    assert net > 0.0, f"8kW heater should produce positive net power, got {net:.0f}W"
