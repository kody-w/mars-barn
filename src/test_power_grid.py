"""Tests for power_grid.py -- Mars Barn Power Grid System.

Validates priority allocation, battery management, dust storm effects,
degradation curves, and grid status reporting.

Test-first as required by community spec on #6662.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from power_grid import allocate, step_power, get_power_status, SYSTEM_DEMANDS, BATTERY_CAPACITY_KWH


class TestAllocate:
    """Priority-based power allocation tests."""

    def test_sufficient_power_allocates_all(self):
        """When power exceeds demand, every system gets full allocation."""
        total_demand = sum(SYSTEM_DEMANDS.values())
        result = allocate(total_demand + 100)
        for system, demand in SYSTEM_DEMANDS.items():
            assert result[system] == pytest.approx(demand, abs=0.01)

    def test_zero_power_allocates_nothing(self):
        """No power means no allocation."""
        result = allocate(0.0)
        assert all(v == 0.0 for v in result.values())

    def test_partial_power_respects_priority(self):
        """Life support gets power first, science gets cut first."""
        result = allocate(25.0)  # Only enough for life_support (20) + 5
        assert result["life_support"] == 20.0
        assert result["thermal"] == 5.0
        assert result["water_recycling"] == 0.0
        assert result["science"] == 0.0

    def test_negative_power_treated_as_zero(self):
        """Negative input should not produce negative allocations."""
        result = allocate(-10.0)
        assert all(v >= 0.0 for v in result.values())

    def test_custom_demands(self):
        """Custom demand dict overrides defaults."""
        result = allocate(50.0, {"life_support": 30.0, "thermal": 30.0})
        assert result["life_support"] == 30.0
        assert result["thermal"] == 20.0


class TestStepPower:
    """Sol-by-sol power simulation tests."""

    def test_returns_dict(self):
        """step_power must return a dict, not mutate state."""
        result = step_power(100.0, 250.0)
        assert isinstance(result, dict)
        assert "solar_input_kwh" in result
        assert "battery_kwh" in result
        assert "allocation" in result
        assert "grid_status" in result

    def test_surplus_charges_battery(self):
        """Excess solar should increase battery level."""
        result = step_power(200.0, 100.0)
        assert result["battery_kwh"] > 100.0
        assert result["surplus_kwh"] > 0.0
        assert result["deficit_kwh"] == 0.0

    def test_deficit_drains_battery(self):
        """Insufficient solar should draw from battery."""
        result = step_power(10.0, 250.0)
        assert result["battery_kwh"] < 250.0
        assert result["grid_status"] in ("strained", "critical")

    def test_dust_storm_halves_solar(self):
        """Dust storm should reduce effective solar by 50%."""
        normal = step_power(100.0, 250.0)
        stormy = step_power(100.0, 250.0, dust_storm=True)
        assert stormy["solar_input_kwh"] == pytest.approx(
            normal["solar_input_kwh"] * 0.5, abs=0.1
        )

    def test_panel_degradation(self):
        """Old panels produce less power."""
        fresh = step_power(100.0, 250.0, panel_degradation_sols=0)
        aged = step_power(100.0, 250.0, panel_degradation_sols=1000)
        assert aged["solar_input_kwh"] < fresh["solar_input_kwh"]

    def test_battery_never_exceeds_capacity(self):
        """Battery cannot charge beyond BATTERY_CAPACITY_KWH."""
        result = step_power(10000.0, BATTERY_CAPACITY_KWH - 1)
        assert result["battery_kwh"] <= BATTERY_CAPACITY_KWH

    def test_battery_never_goes_negative(self):
        """Battery cannot discharge below zero."""
        result = step_power(0.0, 1.0)
        assert result["battery_kwh"] >= 0.0

    def test_grid_status_nominal(self):
        """Full battery + surplus solar = nominal."""
        result = step_power(200.0, 400.0)
        assert result["grid_status"] == "nominal"

    def test_grid_status_critical(self):
        """No solar + near-empty battery = critical."""
        result = step_power(0.0, 10.0)
        assert result["grid_status"] == "critical"


class TestGetPowerStatus:
    """Read-only status snapshot tests."""

    def test_returns_dict(self):
        """get_power_status returns a dict."""
        result = get_power_status({"battery_kwh": 250.0})
        assert isinstance(result, dict)
        assert "battery_fraction" in result

    def test_critical_when_low(self):
        """Low battery fraction triggers critical flag."""
        result = get_power_status({"battery_kwh": 10.0})
        assert result["is_critical"] is True

    def test_not_critical_when_healthy(self):
        """Healthy battery is not critical."""
        result = get_power_status({"battery_kwh": 400.0})
        assert result["is_critical"] is False

    def test_empty_state(self):
        """Missing battery_kwh defaults to 0."""
        result = get_power_status({})
        assert result["battery_kwh"] == 0.0
        assert result["is_critical"] is True


class TestPhysicalInvariants:
    """Property-based checks for physical correctness."""

    def test_power_conservation(self):
        """Power in must equal power allocated + surplus + battery delta."""
        for solar in [0, 10, 50, 100, 200, 500]:
            result = step_power(float(solar), 250.0)
            # Not a strict equality due to efficiency losses, but
            # allocated + surplus should never exceed solar + battery
            total_out = sum(result["allocation"].values()) + result["surplus_kwh"]
            total_in = result["solar_input_kwh"] + 250.0 * 0.95
            assert total_out <= total_in + 0.1

    def test_ten_sol_run_no_crash(self):
        """Run 10 sols of power simulation without crashing."""
        battery = 250.0
        for sol in range(10):
            dust = sol % 5 == 0
            result = step_power(80.0, battery, panel_degradation_sols=sol, dust_storm=dust)
            battery = result["battery_kwh"]
            assert battery >= 0.0
            assert result["grid_status"] in ("nominal", "strained", "critical")
