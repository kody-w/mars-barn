"""Mars Barn Test Suite

Tests for all simulation modules.
Run: python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from terrain import generate_heightmap, elevation_stats
from atmosphere import pressure_at_altitude, temperature_at_altitude, atmosphere_profile
from solar import surface_irradiance, daily_energy, distance_factor as solar_distance_factor
from events import generate_events, tick_events, aggregate_effects
from state_serial import create_state, snapshot, diff_states


class TestTerrain:
    def test_heightmap_dimensions(self):
        grid = generate_heightmap(32, 16, seed=1)
        assert len(grid) == 16
        assert len(grid[0]) == 32

    def test_heightmap_has_relief(self):
        grid = generate_heightmap(32, 32, seed=1)
        stats = elevation_stats(grid)
        assert stats["max_m"] > stats["min_m"] + 100

    def test_heightmap_in_mars_range(self):
        grid = generate_heightmap(32, 32, seed=1)
        stats = elevation_stats(grid)
        assert stats["min_m"] >= -9000
        assert stats["max_m"] <= 22000

    def test_seed_reproducibility(self):
        g1 = generate_heightmap(16, 16, seed=42)
        g2 = generate_heightmap(16, 16, seed=42)
        assert g1 == g2


class TestAtmosphere:
    def test_surface_pressure_range(self):
        p = pressure_at_altitude(0)
        assert 400 <= p <= 900

    def test_pressure_decreases_with_altitude(self):
        p0 = pressure_at_altitude(0)
        p10k = pressure_at_altitude(10000)
        assert p10k < p0

    def test_temperature_range(self):
        t = temperature_at_altitude(0)
        assert 130 <= t <= 310

    def test_dust_storm_reduces_pressure(self):
        p_clear = pressure_at_altitude(0, dust_storm=False)
        p_storm = pressure_at_altitude(0, dust_storm=True)
        assert p_storm < p_clear

    def test_profile_length(self):
        profile = atmosphere_profile(50000, 10)
        assert len(profile) == 11


class TestSolar:
    def test_no_irradiance_at_night(self):
        irr = surface_irradiance(latitude_deg=0, hour=0)
        assert irr == 0.0

    def test_peak_irradiance_at_noon(self):
        irr = surface_irradiance(latitude_deg=0, solar_longitude_deg=0, hour=12)
        assert irr > 0

    def test_dust_storm_reduces_irradiance(self):
        clear = surface_irradiance(latitude_deg=0, hour=12, dust_storm=False)
        storm = surface_irradiance(latitude_deg=0, hour=12, dust_storm=True)
        assert storm < clear

    def test_daily_energy_positive(self):
        e = daily_energy(latitude_deg=0, solar_longitude=0)
        assert e["total_kwh"] > 0
        assert e["daylight_hours"] > 6

    def test_distance_factor_varies(self):
        peri = solar_distance_factor(251)  # perihelion
        aph = solar_distance_factor(71)    # aphelion
        assert peri > aph


class TestEvents:
    def test_generate_returns_list(self):
        events = generate_events(1, seed=42)
        assert isinstance(events, list)

    def test_tick_removes_expired(self):
        events = [{"type": "test", "sol_start": 1, "duration_sols": 3, "effects": {}}]
        remaining = tick_events(events, 5)
        assert len(remaining) == 0

    def test_tick_keeps_active(self):
        events = [{"type": "test", "sol_start": 1, "duration_sols": 10, "effects": {}}]
        remaining = tick_events(events, 5)
        assert len(remaining) == 1

    def test_aggregate_default(self):
        effects = aggregate_effects([])
        assert effects["solar_multiplier"] == 1.0


class TestStateSerialization:
    def test_create_state(self):
        state = create_state(sol=0)
        assert state["sol"] == 0
        assert state["habitat"]["crew_size"] == 4

    def test_snapshot_strips_terrain(self):
        state = create_state(terrain=[[1, 2], [3, 4]])
        snap = snapshot(state)
        assert "terrain" not in snap

    def test_diff_detects_changes(self):
        s1 = {"sol": 0, "temp": 293}
        s2 = {"sol": 10, "temp": 290}
        diff = diff_states(s1, s2)
        assert "sol" in diff
        assert "temp" in diff

    def test_diff_empty_on_same(self):
        s = {"sol": 5}
        diff = diff_states(s, s)
        assert len(diff) == 0
