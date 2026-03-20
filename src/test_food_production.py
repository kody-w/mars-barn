"""Tests for food_production.py

Acceptance criteria from rappterbook Discussion #6614/#6640 (debater-03 template).
Author: zion-coder-03
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from food_production import (
    step_food,
    crop_maturity_factor,
    water_availability_factor,
    solar_availability_factor,
    CROP_MATURITY_SOLS,
    GREENHOUSE_KCAL_PER_SOL,
    MIN_SOLAR_KWH_FOR_GROWTH,
    LIGHT_SATURATION_KWH,
)


def test_maturity_at_sol_zero():
    """Acceptance criteria: crop maturity at sol 0 -> food output = 0."""
    result = step_food(population=4, water_available=100.0, solar_energy_kwh=50.0, sol=0)
    assert result["food_produced_kcal"] == 0.0
    assert result["growth_stage"] == 0.0


def test_no_water_no_food():
    """Acceptance criteria: water_available = 0 -> food output = 0."""
    result = step_food(population=4, water_available=0.0, solar_energy_kwh=50.0, sol=100)
    assert result["food_produced_kcal"] == 0.0
    assert result["water_consumed_l"] == 0.0


def test_no_solar_no_food():
    """Acceptance criteria: solar_energy = 0 -> food output = 0."""
    result = step_food(population=4, water_available=100.0, solar_energy_kwh=0.0, sol=100)
    assert result["food_produced_kcal"] == 0.0


def test_food_always_non_negative():
    """Acceptance criteria: food_output is always non-negative."""
    for sol in range(0, 200, 10):
        for water in [0.0, 1.0, 50.0]:
            for solar in [0.0, 3.0, 20.0, 50.0]:
                result = step_food(4, water, solar, sol)
                assert result["food_produced_kcal"] >= 0.0
                assert result["water_consumed_l"] >= 0.0
                assert result["deficit_kcal"] >= 0.0


def test_water_consumed_le_available():
    """Acceptance criteria: water consumed <= water available."""
    for water in [0.0, 0.5, 2.0, 5.0, 100.0]:
        result = step_food(4, water, 50.0, 100)
        assert result["water_consumed_l"] <= water + 0.01  # float tolerance


def test_maturity_reaches_full():
    """Acceptance criteria: maturity curve reaches full output after maturity_period."""
    result_at_maturity = step_food(4, 100.0, 50.0, CROP_MATURITY_SOLS)
    result_past_maturity = step_food(4, 100.0, 50.0, CROP_MATURITY_SOLS + 50)
    assert result_at_maturity["growth_stage"] == 1.0
    assert result_past_maturity["growth_stage"] == 1.0
    assert result_at_maturity["food_produced_kcal"] == result_past_maturity["food_produced_kcal"]


def test_full_production_feeds_crew():
    """At full maturity with plenty of resources, greenhouse should produce food."""
    result = step_food(population=4, water_available=100.0, solar_energy_kwh=50.0, sol=100)
    assert result["food_produced_kcal"] > 0
    assert result["growth_stage"] == 1.0
    assert result["fed_population"] >= 0


def test_maturity_curve_is_linear():
    """Maturity factor should scale linearly from 0 to 1."""
    assert crop_maturity_factor(0) == 0.0
    assert crop_maturity_factor(CROP_MATURITY_SOLS // 2) == 0.5
    assert crop_maturity_factor(CROP_MATURITY_SOLS) == 1.0
    assert crop_maturity_factor(CROP_MATURITY_SOLS * 2) == 1.0


if __name__ == "__main__":
    test_maturity_at_sol_zero()
    test_no_water_no_food()
    test_no_solar_no_food()
    test_food_always_non_negative()
    test_water_consumed_le_available()
    test_maturity_reaches_full()
    test_full_production_feeds_crew()
    test_maturity_curve_is_linear()
    print("All 8 tests passed!")
