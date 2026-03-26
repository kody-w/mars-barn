"""test_constants.py - Validate Mars Barn physical constants against NASA references.

Part of the 3-PR seed: this is the ADD operation.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constants import (
    MARS_GRAVITY_M_S2,
    MARS_SURFACE_PRESSURE_PA,
    MARS_SURFACE_TEMP_K,
    STEFAN_BOLTZMANN,
    BOLTZMANN,
    HABITAT_TARGET_TEMP_K,
    HABITAT_CREW_SIZE,
    MARS_SOL_SECONDS,
    SOLAR_CONSTANT_MARS,
    HABITAT_EMISSIVITY,
)


class TestMarsConstants(unittest.TestCase):
    """Validate physical constants against NASA Mars Fact Sheet."""

    def test_mars_gravity_range(self):
        self.assertAlmostEqual(MARS_GRAVITY_M_S2, 3.721, delta=0.005)

    def test_mars_surface_pressure(self):
        self.assertGreater(MARS_SURFACE_PRESSURE_PA, 600)
        self.assertLess(MARS_SURFACE_PRESSURE_PA, 700)

    def test_mars_surface_temp(self):
        self.assertAlmostEqual(MARS_SURFACE_TEMP_K, 210, delta=10)

    def test_stefan_boltzmann(self):
        self.assertAlmostEqual(STEFAN_BOLTZMANN, 5.67e-8, delta=1e-10)

    def test_boltzmann(self):
        self.assertAlmostEqual(BOLTZMANN, 1.381e-23, delta=1e-25)

    def test_habitat_temp_livable(self):
        self.assertGreaterEqual(HABITAT_TARGET_TEMP_K, 291)
        self.assertLessEqual(HABITAT_TARGET_TEMP_K, 298)

    def test_crew_size_positive(self):
        self.assertGreaterEqual(HABITAT_CREW_SIZE, 1)

    def test_sol_length(self):
        self.assertEqual(MARS_SOL_SECONDS, 88775)

    def test_solar_constant(self):
        self.assertAlmostEqual(SOLAR_CONSTANT_MARS, 586.2, delta=12)

    def test_emissivity_range(self):
        self.assertGreater(HABITAT_EMISSIVITY, 0)
        self.assertLessEqual(HABITAT_EMISSIVITY, 1)


if __name__ == "__main__":
    unittest.main()
