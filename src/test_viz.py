"""Mars Barn — Visualization Module Tests

Unit tests for terrain rendering, atmosphere profiles, dashboards,
and event log formatting.

Author: zion-coder-05 (via Rappterbook frame 293)
"""
from __future__ import annotations

import unittest

from terrain import generate_heightmap
from viz import (
    render_terrain,
    render_atmosphere,
    render_dashboard,
    render_events,
)


class TestRenderTerrain(unittest.TestCase):
    """Tests for ASCII terrain rendering."""

    def test_basic_render(self):
        grid = generate_heightmap(8, 8, seed=42)
        output = render_terrain(grid)
        lines = output.strip().split("\n")
        self.assertEqual(len(lines), 8)
        for line in lines:
            self.assertEqual(len(line), 16)  # 8 cols * repeat=2

    def test_custom_width(self):
        grid = generate_heightmap(4, 4, seed=7)
        output = render_terrain(grid, width=20)
        lines = output.strip().split("\n")
        self.assertEqual(len(lines), 4)


class TestRenderAtmosphere(unittest.TestCase):
    """Tests for atmosphere profile table."""

    def test_has_header(self):
        output = render_atmosphere()
        self.assertIn("Alt (km)", output)
        self.assertIn("Pressure (Pa)", output)

    def test_multiple_rows(self):
        output = render_atmosphere()
        lines = output.strip().split("\n")
        self.assertGreater(len(lines), 3)


class TestRenderDashboard(unittest.TestCase):
    """Tests for simulation dashboard."""

    def test_empty_state(self):
        output = render_dashboard({})
        self.assertIn("Sol 0", output)
        self.assertIn("MARS BARN", output)

    def test_populated_state(self):
        state = {
            "sol": 147,
            "habitat": {
                "interior_temp_k": 293.0,
                "stored_energy_kwh": 420.0,
                "power_kw": 3.5,
                "solar_panel_area_m2": 400,
                "solar_panel_efficiency": 0.22,
            },
            "metrics": {
                "events_survived": 3,
                "total_power_generated_kwh": 1200,
                "total_heat_lost_kwh": 800,
            },
        }
        output = render_dashboard(state)
        self.assertIn("Sol 147", output)
        self.assertIn("420", output)


class TestRenderEvents(unittest.TestCase):
    """Tests for event log formatting."""

    def test_empty_events(self):
        output = render_events([])
        self.assertIn("No events", output)

    def test_with_events(self):
        events = [
            {"sol": 30, "type": "dust_storm", "description": "Regional dust storm", "severity": "major"},
            {"sol": 60, "type": "equipment", "description": "Panel degradation"},
        ]
        output = render_events(events)
        self.assertIn("Sol  30", output)
        self.assertIn("⚡", output)
        self.assertIn("Panel degradation", output)


if __name__ == "__main__":
    unittest.main()

