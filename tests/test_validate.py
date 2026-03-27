"""Tests for Mars Barn validation suite.

Covers run_all_validations() and individual check functions.
Previously untested — closes the validation coverage gap.

Author: zion-coder-01 (Ada Lovelace)
"""
import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from validate import (
    validate_terrain,
    validate_atmosphere,
    validate_solar,
    validate_thermal,
    run_all_validations,
)


class TestValidateTerrain(unittest.TestCase):
    def test_terrain_passes_on_valid_data(self):
        # Should not raise — default terrain is within Mars bounds
        validate_terrain()

    def test_terrain_uses_known_mars_bounds(self):
        # Mars elevation extremes: Hellas Basin ~-8200m, Olympus Mons ~21229m
        # Terrain generator should stay within these bounds
        validate_terrain()  # implicit assertion — no exception = pass


class TestValidateAtmosphere(unittest.TestCase):
    def test_atmosphere_passes_nominal(self):
        validate_atmosphere()

    def test_surface_pressure_range(self):
        # Mars surface pressure: ~600 Pa (500-700 nominal)
        from atmosphere import pressure_at_altitude
        p = pressure_at_altitude(0)
        self.assertGreaterEqual(p, 500)
        self.assertLessEqual(p, 700)


class TestValidateSolar(unittest.TestCase):
    def test_solar_passes_nominal(self):
        validate_solar()

    def test_no_sun_at_midnight(self):
        from solar import surface_irradiance
        self.assertEqual(surface_irradiance(hour=0), 0)


class TestValidateThermal(unittest.TestCase):
    def test_thermal_passes_nominal(self):
        validate_thermal()

    def test_night_heating_exceeds_day(self):
        from thermal import calculate_required_heating
        night = calculate_required_heating(external_temp_k=150.0, solar_irradiance_w_m2=0.0)
        day = calculate_required_heating(external_temp_k=290.0, solar_irradiance_w_m2=500.0)
        self.assertGreater(night, day)


class TestRunAllValidations(unittest.TestCase):
    def test_all_pass_on_clean_state(self):
        result = run_all_validations()
        self.assertEqual(result["passed"], 4)
        self.assertEqual(result["total"], 4)
        for r in result["results"]:
            self.assertTrue(r["passed"], f"{r['check']} failed: {r['detail']}")

    def test_returns_correct_structure(self):
        result = run_all_validations()
        self.assertIn("passed", result)
        self.assertIn("total", result)
        self.assertIn("results", result)
        self.assertIsInstance(result["results"], list)
        self.assertEqual(len(result["results"]), 4)

    def test_individual_check_names(self):
        result = run_all_validations()
        check_names = [r["check"] for r in result["results"]]
        self.assertEqual(check_names, ["terrain", "atmosphere", "solar", "thermal"])

    def test_catches_validation_failure(self):
        """Verify run_all_validations catches and reports failures."""
        with patch("validate.validate_terrain", side_effect=AssertionError("forced")):
            result = run_all_validations()
        self.assertEqual(result["passed"], 3)
        self.assertFalse(result["results"][0]["passed"])
        self.assertIn("forced", result["results"][0]["detail"])

    def test_continues_after_failure(self):
        """Other checks still run even when one fails."""
        with patch("validate.validate_terrain", side_effect=AssertionError("fail")):
            result = run_all_validations()
        # terrain failed but the other 3 should pass
        passing = [r for r in result["results"] if r["passed"]]
        self.assertEqual(len(passing), 3)


if __name__ == "__main__":
    unittest.main()
