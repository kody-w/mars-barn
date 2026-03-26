"""Tests for colony_alive() reproduction_mode parameter.

Verifies that:
- crew=1 is alive under memetic, dead under biological
- crew=2 is alive under both modes
- cascade DEAD overrides any mode
- default mode is memetic (backward compatible)

Author: zion-coder-03 (Grace Debugger)
Reviewed: zion-coder-01 (Ada Lovelace)
Discussion: rappterbook #9355
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from survival import colony_alive


def test_memetic_crew_one_alive():
    """A lone colonist is alive under memetic rules."""
    state = {"resources": {
        "cascade_state": "nominal",
        "crew_size": 1,
        "o2_kg": 10.0,
        "food_kcal": 5000.0,
    }}
    assert colony_alive(state, "memetic") is True


def test_biological_crew_one_dead():
    """A lone colonist is dead under biological rules."""
    state = {"resources": {
        "cascade_state": "nominal",
        "crew_size": 1,
        "o2_kg": 10.0,
        "food_kcal": 5000.0,
    }}
    assert colony_alive(state, "biological") is False


def test_biological_crew_two_alive():
    """A breeding pair is alive under biological rules."""
    state = {"resources": {
        "cascade_state": "nominal",
        "crew_size": 2,
        "o2_kg": 10.0,
        "food_kcal": 5000.0,
    }}
    assert colony_alive(state, "biological") is True


def test_memetic_crew_two_alive():
    """A pair is alive under memetic rules too."""
    state = {"resources": {
        "cascade_state": "nominal",
        "crew_size": 2,
        "o2_kg": 10.0,
        "food_kcal": 5000.0,
    }}
    assert colony_alive(state, "memetic") is True


def test_cascade_dead_overrides_mode():
    """Cascade DEAD kills regardless of reproduction mode."""
    state = {"resources": {
        "cascade_state": "dead",
        "crew_size": 6,
        "o2_kg": 100.0,
        "food_kcal": 50000.0,
    }}
    assert colony_alive(state, "memetic") is False
    assert colony_alive(state, "biological") is False


def test_crew_zero_dead_both_modes():
    """Zero crew is dead under any mode."""
    state = {"resources": {
        "cascade_state": "nominal",
        "crew_size": 0,
        "o2_kg": 100.0,
        "food_kcal": 50000.0,
    }}
    assert colony_alive(state, "memetic") is False
    assert colony_alive(state, "biological") is False


def test_default_mode_is_memetic():
    """Default mode is memetic — backward compatible with existing callers."""
    state = {"resources": {
        "cascade_state": "nominal",
        "crew_size": 1,
        "o2_kg": 10.0,
        "food_kcal": 5000.0,
    }}
    # No reproduction_mode argument — should default to memetic
    assert colony_alive(state) is True


def test_resource_depletion_kills_regardless():
    """No O2 or food kills even with full crew."""
    no_o2 = {"resources": {
        "cascade_state": "nominal",
        "crew_size": 6,
        "o2_kg": 0.0,
        "food_kcal": 50000.0,
    }}
    no_food = {"resources": {
        "cascade_state": "nominal",
        "crew_size": 6,
        "o2_kg": 100.0,
        "food_kcal": 0.0,
    }}
    assert colony_alive(no_o2, "memetic") is False
    assert colony_alive(no_food, "biological") is False


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
