"""test_weather_dashboard.py — Contract tests for weather_dashboard.py.

Adapted from zion-wildcard-05 contract tests (rappterbook #14041).
Tests the climate model, not the API. Deterministic — never flakes.

Run: python3 -m pytest tests/test_weather_dashboard.py -v
"""
import math
import unittest
from datetime import datetime, timezone, timedelta
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from weather_dashboard import earth_to_mars_sol, interpolate_climate, generate_forecast
from weather_dashboard import SURFACE_TEMP_BY_LS, PRESSURE_BY_LS


class TestSolConversion(unittest.TestCase):

    def test_sol_in_valid_range(self):
        for day_offset in range(0, 700, 7):
            dt = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)
            sol, ls = earth_to_mars_sol(dt)
            self.assertGreaterEqual(sol, 0)
            self.assertLess(sol, 668)

    def test_ls_in_valid_range(self):
        for day_offset in range(0, 700, 7):
            dt = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)
            sol, ls = earth_to_mars_sol(dt)
            self.assertGreaterEqual(ls, 0.0)
            self.assertLess(ls, 360.0)

    def test_ls_advances_over_consecutive_days(self):
        dt = datetime(2026, 4, 1, tzinfo=timezone.utc)
        _, ls_prev = earth_to_mars_sol(dt)
        advances = 0
        for i in range(1, 30):
            dt_next = dt + timedelta(days=i)
            _, ls_next = earth_to_mars_sol(dt_next)
            if ls_next > ls_prev or (ls_prev > 350 and ls_next < 10):
                advances += 1
            ls_prev = ls_next
        self.assertGreater(advances, 25)

    def test_known_epoch(self):
        dt = datetime(2000, 1, 6, 0, 0, 0, tzinfo=timezone.utc)
        sol, ls = earth_to_mars_sol(dt)
        self.assertEqual(sol, 0)
        self.assertAlmostEqual(ls, 277.2, delta=5.0)


class TestClimateModel(unittest.TestCase):

    def test_temperature_within_physical_bounds(self):
        for ls in range(0, 360, 5):
            temp = interpolate_climate(float(ls), SURFACE_TEMP_BY_LS)
            self.assertGreater(temp[0], 130)
            self.assertLess(temp[0], 310)

    def test_pressure_within_physical_bounds(self):
        for ls in range(0, 360, 5):
            pres = interpolate_climate(float(ls), PRESSURE_BY_LS)
            self.assertGreater(pres[0], 400)
            self.assertLess(pres[0], 1200)

    def test_interpolation_continuity(self):
        for bin_edge in range(30, 360, 30):
            t_before = interpolate_climate(float(bin_edge - 0.1), SURFACE_TEMP_BY_LS)
            t_at = interpolate_climate(float(bin_edge), SURFACE_TEMP_BY_LS)
            self.assertLess(abs(t_at[0] - t_before[0]), 2.0)


class TestForecastOutput(unittest.TestCase):

    def test_forecast_has_required_keys(self):
        fc = generate_forecast()
        for key in ['sol', 'ls', 'earth_date', 'temperature_K',
                     'temperature_C', 'pressure_Pa', 'dust_probability', 'advisories']:
            self.assertIn(key, fc)

    def test_forecast_deterministic(self):
        dt = datetime(2026, 4, 5, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(generate_forecast(dt), generate_forecast(dt))

    def test_advisories_not_empty(self):
        for month in range(1, 13):
            dt = datetime(2026, month, 15, tzinfo=timezone.utc)
            fc = generate_forecast(dt)
            self.assertGreater(len(fc['advisories']), 0)

    def test_dust_probability_bounded(self):
        for day in range(0, 700, 7):
            dt = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
            fc = generate_forecast(dt)
            self.assertGreaterEqual(fc['dust_probability'], 0.0)
            self.assertLessEqual(fc['dust_probability'], 1.0)


if __name__ == "__main__":
    unittest.main()
