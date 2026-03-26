#!/usr/bin/env python3
"""Terrarium Test — Prove the colony breathes.

The community voted: the first key-holder PR must be a passing test.
Run the simulation for 1 sol. Assert clean exit. That is all.

Run: python -m pytest src/test_terrarium.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_simulation


def test_colony_breathes_1sol():
    """Run the full simulation for 1 sol and assert it exits cleanly."""
    result = run_simulation(num_sols=1, seed=42, verbose=False)
    summary = result["summary"]

    # The colony must be alive
    assert summary["colony_alive"], "Colony died after 1 sol"

    # Must have survived at least 1 sol
    assert summary["sols_survived"] >= 1, f"Only survived {summary['sols_survived']} sols"

    # All validations must pass
    assert summary["validation_passed"] == summary["validation_total"], (
        f"Validation: {summary['validation_passed']}/{summary['validation_total']} passed"
    )


def test_colony_breathes_1sol_deterministic():
    """Same test, different seed — the colony must breathe regardless."""
    for seed in [0, 1, 99, 12345]:
        result = run_simulation(num_sols=1, seed=seed, verbose=False)
        summary = result["summary"]
        assert summary["colony_alive"], f"Colony died with seed={seed}"
        assert summary["validation_passed"] == summary["validation_total"], (
            f"Validation failed with seed={seed}"
        )
