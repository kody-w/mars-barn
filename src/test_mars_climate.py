#!/usr/bin/env python3
"""Tests for Mars Climate module — validates NASA-derived data tables.

Run: python -m pytest src/test_mars_climate.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mars_climate import (
    dust_storm_stats,
    surface_temp_stats,
    get_ls_bin,
    interpolate_climate,
    annual_summary,
    SURFACE_TEMP_BY_LS,
    PRESSURE_BY_LS,
    DUST_STORM_BY_LS,
)


def test_get_ls_bin_boundaries():
    """Ls bins are multiples of 30 in [0, 330]."""
    assert get_ls_bin(0) == 0
    assert get_ls_bin(15) == 0
    assert get_ls_bin(29.9) == 0
    assert get_ls_bin(30) == 30
    assert get_ls_bin(359) == 330
    assert get_ls_bin(360) == 0  # wraps


def test_dust_storm_stats_returns_five_floats():
    """dust_storm_stats returns (any_prob, regional, global, mean_sev, max_sev)."""
    for ls in range(0, 360, 30):
        result = dust_storm_stats(ls)
        assert len(result) == 5, f"Ls={ls}: expected 5 values, got {len(result)}"
        any_p, reg_p, glob_p, mean_s, max_s = result
        assert 0 <= any_p <= 1, f"Ls={ls}: any_prob={any_p} out of [0,1]"
        assert 0 <= reg_p <= 1, f"Ls={ls}: regional_prob={reg_p} out of [0,1]"
        assert 0 <= glob_p <= 1, f"Ls={ls}: global_prob={glob_p} out of [0,1]"
        assert mean_s <= max_s, f"Ls={ls}: mean_sev > max_sev"


def test_dust_storm_season_peak():
    """Ls 210-270 should have higher storm probability than Ls 0-90."""
    peak = dust_storm_stats(210)[0]
    quiet = dust_storm_stats(0)[0]
    assert peak > quiet, f"Storm season ({peak}) should exceed quiet ({quiet})"


def test_surface_temp_perihelion_warmer():
    """Perihelion (Ls ~251) should be warmer than aphelion (Ls ~70)."""
    peri = surface_temp_stats(240)[0]
    aph = surface_temp_stats(90)[0]
    assert peri > aph, f"Perihelion ({peri}K) should exceed aphelion ({aph}K)"


def test_all_data_tables_have_12_bins():
    """Every climate table should have 12 entries (0, 30, ..., 330)."""
    assert len(SURFACE_TEMP_BY_LS) == 12
    assert len(PRESSURE_BY_LS) == 12
    assert len(DUST_STORM_BY_LS) == 12


def test_interpolation_at_bin_equals_bin_value():
    """Interpolation at exact bin should return bin value."""
    exact = surface_temp_stats(90)
    interp = interpolate_climate(90.0, SURFACE_TEMP_BY_LS)
    for a, b in zip(exact, interp):
        assert abs(a - b) < 0.01, f"At exact bin: {exact} vs {interp}"


def test_annual_summary_returns_dict():
    """annual_summary returns a dict with expected keys."""
    s = annual_summary()
    assert "temperature_K" in s
    assert "pressure_Pa" in s
    assert "mean" in s["temperature_K"]

