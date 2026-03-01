"""Mars Barn — Thermal Model Tests

Tests for heat_loss_conduction, heat_loss_radiation, thermal_step,
ground coupling, and crew metabolic heat contributions.

Run: python -m pytest tests/test_thermal.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from thermal import (
    heat_loss_conduction,
    heat_loss_radiation,
    solar_heat_gain,
    electrical_heating,
    thermal_step,
)
from constants import (
    STEFAN_BOLTZMANN,
    HABITAT_SURFACE_AREA_M2,
    HABITAT_VOLUME_M3,
    MARS_SURFACE_TEMP_K,
    HABITAT_CREW_SIZE,
    HUMAN_METABOLIC_HEAT_W,
)


class TestHeatLossConduction:
    def test_positive_loss_when_interior_warmer(self):
        loss = heat_loss_conduction(293.0, 210.0, r_value=12.0)
        assert loss > 0

    def test_zero_loss_at_equilibrium(self):
        loss = heat_loss_conduction(210.0, 210.0, r_value=12.0)
        assert loss == 0.0

    def test_higher_r_value_reduces_loss(self):
        loss_low_r = heat_loss_conduction(293.0, 210.0, r_value=5.0)
        loss_high_r = heat_loss_conduction(293.0, 210.0, r_value=12.0)
        assert loss_high_r < loss_low_r

    def test_conduction_scales_with_surface_area(self):
        loss_small = heat_loss_conduction(293.0, 210.0, r_value=12.0, surface_area_m2=100.0)
        loss_large = heat_loss_conduction(293.0, 210.0, r_value=12.0, surface_area_m2=200.0)
        assert abs(loss_large - 2 * loss_small) < 0.1

    def test_conduction_in_expected_range(self):
        # 200 m², R-12, ΔT=83K → ~1383 W
        loss = heat_loss_conduction(293.0, 210.0, r_value=12.0, surface_area_m2=200.0)
        assert 1000 < loss < 2000


class TestHeatLossRadiation:
    def test_positive_loss_when_interior_warmer(self):
        loss = heat_loss_radiation(293.0, 210.0)
        assert loss > 0

    def test_low_emissivity_reduces_loss(self):
        loss_high_e = heat_loss_radiation(293.0, 210.0, emissivity=0.9)
        loss_low_e = heat_loss_radiation(293.0, 210.0, emissivity=0.05)
        assert loss_low_e < loss_high_e
        # Low-e should reduce by roughly 18x (0.9/0.05)
        ratio = loss_high_e / loss_low_e
        assert 17 < ratio < 19

    def test_low_e_loss_manageable(self):
        # At ε=0.05, radiative loss should be under 5 kW
        loss = heat_loss_radiation(293.0, 210.0, emissivity=0.05, surface_area_m2=200.0)
        assert loss < 5000

    def test_zero_loss_at_equilibrium(self):
        loss = heat_loss_radiation(210.0, 210.0)
        assert abs(loss) < 0.01


class TestSolarHeatGain:
    def test_positive_gain_with_irradiance(self):
        gain = solar_heat_gain(400.0, window_area_m2=10.0, transmittance=0.75)
        assert gain == pytest.approx(3000.0)

    def test_no_gain_at_night(self):
        gain = solar_heat_gain(0.0)
        assert gain == 0.0


class TestElectricalHeating:
    def test_heater_output(self):
        heat = electrical_heating(8000.0, efficiency=0.95)
        assert heat == pytest.approx(7600.0)

    def test_zero_power(self):
        heat = electrical_heating(0.0)
        assert heat == 0.0


class TestThermalStep:
    def test_returns_expected_keys(self):
        result = thermal_step(293.0, 210.0, dt_seconds=3600.0)
        expected_keys = [
            "interior_temp_k", "delta_t_k", "q_solar_w", "q_electric_w",
            "q_cond_loss_w", "q_rad_loss_w", "q_ground_loss_w",
            "q_metabolic_w", "q_net_w", "heating_required",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_heater_raises_temperature(self):
        result = thermal_step(280.0, 210.0, electrical_power_w=8000.0, dt_seconds=3600.0)
        assert result["interior_temp_k"] > 280.0

    def test_temperature_drops_without_heating(self):
        # No solar, no heater, interior warmer than exterior → should cool
        result = thermal_step(293.0, 210.0, solar_irradiance_wm2=0.0,
                              electrical_power_w=0.0, dt_seconds=3600.0)
        assert result["interior_temp_k"] < 293.0

    def test_metabolic_heat_present(self):
        result = thermal_step(293.0, 210.0, dt_seconds=3600.0)
        expected_metabolic = HUMAN_METABOLIC_HEAT_W * HABITAT_CREW_SIZE
        assert result["q_metabolic_w"] == pytest.approx(expected_metabolic, abs=1.0)

    def test_ground_coupling_present(self):
        # Ground coupling should show a nonzero value
        result = thermal_step(293.0, 210.0, dt_seconds=3600.0)
        assert result["q_ground_loss_w"] != 0.0

    def test_ground_coupling_is_heat_loss_when_interior_warm(self):
        # Interior at 293K, ground at ~210K → ground drains heat → positive q_ground_loss_w
        result = thermal_step(293.0, 210.0, dt_seconds=3600.0)
        assert result["q_ground_loss_w"] > 0  # loss is positive

    def test_higher_r_value_reduces_cooling_rate(self):
        result_low_r = thermal_step(293.0, 210.0, r_value=5.0, dt_seconds=3600.0)
        result_high_r = thermal_step(293.0, 210.0, r_value=12.0, dt_seconds=3600.0)
        # Higher R-value → less cooling → higher resulting temp
        assert result_high_r["interior_temp_k"] > result_low_r["interior_temp_k"]

    def test_thermal_mass_dampens_swings(self):
        # With default 20× thermal mass, a 1-hour step shouldn't change temp by more than a few degrees
        result = thermal_step(293.0, 210.0, electrical_power_w=0.0, dt_seconds=3600.0)
        delta = abs(result["delta_t_k"])
        assert delta < 10.0, f"Temperature swing too large: {delta}K in 1 hour"
