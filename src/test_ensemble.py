"""Tests for ensemble.py — Mars Barn ensemble runner.

Validates that multi-run ensemble aggregation produces correct
statistics and that all wired modules integrate correctly end-to-end.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ensemble import run_ensemble


def test_ensemble_basic():
    """Ensemble with 2 runs completes and returns expected keys."""
    result = run_ensemble(num_runs=2, num_sols=5)
    assert result["runs"] == 2
    assert result["sols_per_run"] == 5
    for key in ("survival_rate", "temp_min_c", "temp_max_c", "temp_mean_c",
                "energy_min_kwh", "energy_max_kwh", "energy_mean_kwh", "events_mean"):
        assert key in result, f"Missing key: {key}"


def test_ensemble_survival_rate_bounded():
    """Survival rate is between 0% and 100%."""
    result = run_ensemble(num_runs=3, num_sols=10)
    assert 0.0 <= result["survival_rate"] <= 100.0


def test_ensemble_temperature_ordering():
    """min_temp <= mean_temp <= max_temp always holds."""
    result = run_ensemble(num_runs=4, num_sols=10)
    assert result["temp_min_c"] <= result["temp_mean_c"]
    assert result["temp_mean_c"] <= result["temp_max_c"]


def test_ensemble_energy_non_negative():
    """Energy values are non-negative."""
    result = run_ensemble(num_runs=2, num_sols=5)
    assert result["energy_min_kwh"] >= 0
    assert result["energy_mean_kwh"] >= 0
    assert result["energy_max_kwh"] >= 0


def test_ensemble_deterministic():
    """Same parameters produce identical results."""
    a = run_ensemble(num_runs=2, num_sols=5)
    b = run_ensemble(num_runs=2, num_sols=5)
    assert a == b
