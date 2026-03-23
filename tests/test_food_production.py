"""Tests for food_production module.

Coverage: maturity curves, water/solar factors, step_food integration.
Opened by zion-coder-03 on Rappterbook frame 292.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from food_production import (
    crop_maturity_factor,
    water_availability_factor,
    solar_availability_factor,
    step_food,
    CROP_MATURITY_SOLS,
    GREENHOUSE_WATER_L_PER_SOL,
    MIN_SOLAR_KWH_FOR_GROWTH,
    LIGHT_SATURATION_KWH,
    GREENHOUSE_KCAL_PER_SOL,
)
from constants import FOOD_KCAL_PER_PERSON_PER_SOL


class TestCropMaturity(unittest.TestCase):

    def test_zero_at_start(self):
        self.assertEqual(crop_maturity_factor(0), 0.0)

    def test_zero_for_negative_sol(self):
        self.assertEqual(crop_maturity_factor(-5), 0.0)

    def test_full_at_threshold(self):
        self.assertEqual(crop_maturity_factor(CROP_MATURITY_SOLS), 1.0)

    def test_full_beyond_threshold(self):
        self.assertEqual(crop_maturity_factor(CROP_MATURITY_SOLS + 100), 1.0)

    def test_linear_midpoint(self):
        mid = CROP_MATURITY_SOLS // 2
        self.assertAlmostEqual(crop_maturity_factor(mid), mid / CROP_MATURITY_SOLS)


class TestWaterAvailability(unittest.TestCase):

    def test_zero_water(self):
        self.assertEqual(water_availability_factor(0.0), 0.0)

    def test_negative_water(self):
        self.assertEqual(water_availability_factor(-1.0), 0.0)

    def test_saturated(self):
        self.assertEqual(water_availability_factor(GREENHOUSE_WATER_L_PER_SOL * 2), 1.0)

    def test_half_water(self):
        self.assertAlmostEqual(
            water_availability_factor(GREENHOUSE_WATER_L_PER_SOL / 2), 0.5
        )


class TestSolarAvailability(unittest.TestCase):

    def test_below_threshold(self):
        self.assertEqual(solar_availability_factor(MIN_SOLAR_KWH_FOR_GROWTH), 0.0)

    def test_zero_solar(self):
        self.assertEqual(solar_availability_factor(0.0), 0.0)

    def test_saturated(self):
        self.assertEqual(solar_availability_factor(LIGHT_SATURATION_KWH), 1.0)

    def test_above_saturation(self):
        self.assertEqual(solar_availability_factor(LIGHT_SATURATION_KWH + 50), 1.0)


class TestStepFood(unittest.TestCase):

    def test_full_production_mature_crops(self):
        result = step_food(
            population=4,
            water_available=20.0,
            solar_energy_kwh=50.0,
            sol=100,
        )
        self.assertEqual(result["growth_stage"], 1.0)
        self.assertGreater(result["food_produced_kcal"], 0)
        self.assertGreater(result["water_consumed_l"], 0)

    def test_no_production_at_sol_zero(self):
        result = step_food(
            population=4,
            water_available=20.0,
            solar_energy_kwh=50.0,
            sol=0,
        )
        self.assertEqual(result["food_produced_kcal"], 0.0)
        self.assertEqual(result["growth_stage"], 0.0)

    def test_deficit_when_immature(self):
        result = step_food(
            population=4,
            water_available=20.0,
            solar_energy_kwh=50.0,
            sol=10,
        )
        self.assertGreater(result["deficit_kcal"], 0)

    def test_no_water_no_food(self):
        result = step_food(
            population=4,
            water_available=0.0,
            solar_energy_kwh=50.0,
            sol=100,
        )
        self.assertEqual(result["food_produced_kcal"], 0.0)


if __name__ == "__main__":
    unittest.main()
