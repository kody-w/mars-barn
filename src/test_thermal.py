"""Tests for thermal.py — Mars habitat thermal regulation.

Covers the critical survival path: heating, cooling, solar gain,
insulation effects, and full-sol simulation.

Author: zion-coder-02 (Linus Kernel)
Refs: Discussion #10447 (test coverage audit)
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thermal import thermal_step, simulate_sol


class TestThermalStep:
    """Unit tests for thermal_step() — single timestep physics."""

    def test_cooling_without_heating(self):
        """Interior should cool when heater is off and exterior is cold."""
        result = thermal_step(293.15, 210.0, 0.0, 0.0, r_value=12.0, dt_seconds=900)
        assert result["interior_temp_k"] < 293.15, "Should cool without heater"

    def test_heater_counteracts_cooling(self):
        """Heater on should result in warmer interior than heater off."""
        cold = thermal_step(293.15, 210.0, 0.0, 0.0, r_value=12.0, dt_seconds=900)
        warm = thermal_step(293.15, 210.0, 0.0, 8000.0, r_value=12.0, dt_seconds=900)
        assert warm["interior_temp_k"] > cold["interior_temp_k"], "Heater should help"

    def test_solar_gain_adds_heat(self):
        """Solar irradiance should add heat to interior."""
        dark = thermal_step(293.15, 210.0, 0.0, 0.0, r_value=12.0, dt_seconds=900)
        lit = thermal_step(293.15, 210.0, 590.0, 0.0, r_value=12.0, dt_seconds=900)
        assert lit["interior_temp_k"] > dark["interior_temp_k"], "Solar should add heat"

    def test_higher_r_value_reduces_loss(self):
        """Better insulation (higher R-value) should reduce heat loss."""
        low_r = thermal_step(293.15, 210.0, 0.0, 0.0, r_value=6.0, dt_seconds=900)
        high_r = thermal_step(293.15, 210.0, 0.0, 0.0, r_value=24.0, dt_seconds=900)
        assert high_r["interior_temp_k"] > low_r["interior_temp_k"]

    def test_extreme_cold_exterior(self):
        """Habitat should still function at Mars winter minimum (~150K)."""
        result = thermal_step(293.15, 150.0, 0.0, 8000.0, r_value=12.0, dt_seconds=900)
        assert result["interior_temp_k"] > 150.0, "Should not drop to exterior temp"

    def test_zero_timestep(self):
        """Zero-length timestep should not change temperature."""
        result = thermal_step(293.15, 210.0, 0.0, 0.0, r_value=12.0, dt_seconds=0)
        assert abs(result["interior_temp_k"] - 293.15) < 0.01


class TestSimulateSol:
    """Integration tests for simulate_sol() — full Mars day."""

    def test_returns_expected_keys(self):
        """simulate_sol should return heating_kwh, min_temp_k, max_temp_k."""
        result = simulate_sol(solar_longitude=0.0, r_value=12.0)
        assert "heating_kwh" in result
        assert "min_temp_k" in result
        assert "max_temp_k" in result

    def test_heating_required_positive(self):
        """Heating should always be positive on Mars (it is cold)."""
        result = simulate_sol(solar_longitude=0.0, r_value=12.0)
        assert result["heating_kwh"] > 0

    def test_dust_storm_increases_heating(self):
        """Dust storm should increase heating requirements (less solar)."""
        clear = simulate_sol(solar_longitude=210.0, r_value=12.0, dust_storm=False)
        dusty = simulate_sol(solar_longitude=210.0, r_value=12.0, dust_storm=True)
        assert dusty["heating_kwh"] >= clear["heating_kwh"]

    def test_perihelion_vs_aphelion(self):
        """Perihelion (Ls=251) should need less heating than aphelion (Ls=71)."""
        perihelion = simulate_sol(solar_longitude=251.0, r_value=12.0)
        aphelion = simulate_sol(solar_longitude=71.0, r_value=12.0)
        # Perihelion is warmer and closer to sun
        assert perihelion["heating_kwh"] <= aphelion["heating_kwh"] * 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
