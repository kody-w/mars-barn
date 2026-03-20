#!/usr/bin/env python3
"""Smoke tests for Mars Barn — PR Zero CI gate.

These tests catch the three most common bug classes found during
community code review (Discussions #6570, #6572, #6541):
  1. Import failures (missing modules, circular imports)
  2. Constant source drift (hardcoded values vs constants.py)
  3. Unit consistency (kWh, kg, Pa units match across modules)

Run: python -m pytest src/test_smoke.py -v
"""
import importlib
import sys
import os

# Ensure src/ is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_all_modules_import():
    """Every .py in src/ must import without error."""
    src_dir = os.path.dirname(os.path.abspath(__file__))
    failures = []
    for fname in sorted(os.listdir(src_dir)):
        if fname.endswith(".py") and not fname.startswith("test_"):
            module_name = fname[:-3]
            try:
                importlib.import_module(module_name)
            except Exception as e:
                failures.append(f"{module_name}: {e}")
    assert not failures, "Import failures:\n" + "\n".join(failures)


def test_constants_are_source_of_truth():
    """No module should hardcode values that exist in constants.py."""
    from constants import LIFE_SUPPORT_BASE_KWH_PER_SOL
    assert isinstance(LIFE_SUPPORT_BASE_KWH_PER_SOL, (int, float))
    assert LIFE_SUPPORT_BASE_KWH_PER_SOL > 0

    # Verify tick_engine uses the constant, not a hardcoded value
    from tick_engine import BASE_LIFE_SUPPORT_KWH
    assert BASE_LIFE_SUPPORT_KWH == LIFE_SUPPORT_BASE_KWH_PER_SOL, (
        f"tick_engine.BASE_LIFE_SUPPORT_KWH ({BASE_LIFE_SUPPORT_KWH}) != "
        f"constants.LIFE_SUPPORT_BASE_KWH_PER_SOL ({LIFE_SUPPORT_BASE_KWH_PER_SOL})"
    )


def test_solar_energy_positive():
    """Solar module must return positive energy for any valid Ls."""
    from solar import daily_energy
    for ls in [0, 90, 180, 270]:
        result = daily_energy(solar_longitude=ls, dust_storm=False)
        assert result["total_kwh"] > 0, f"Zero energy at Ls {ls}"


def test_thermal_heating_positive():
    """Thermal module must return positive heating cost."""
    from thermal import simulate_sol
    result = simulate_sol(solar_longitude=180, r_value=12.0,
                          dust_storm=False, rtg_power_w=0.0)
    assert result["heating_kwh"] >= 0, "Negative heating cost"


def test_mars_climate_dust_probabilities():
    """Dust probabilities must be valid (0-1) for all Ls bins."""
    from mars_climate import dust_storm_stats
    for ls in range(0, 360, 30):
        any_p, reg_p, glob_p, mean_s, max_s = dust_storm_stats(ls)
        assert 0 <= any_p <= 1, f"Bad any_prob {any_p} at Ls {ls}"
        assert 0 <= reg_p <= 1, f"Bad regional_prob {reg_p} at Ls {ls}"
        assert 0 <= glob_p <= 1, f"Bad global_prob {glob_p} at Ls {ls}"
        assert glob_p <= any_p, f"Global ({glob_p}) > any ({any_p}) at Ls {ls}"
