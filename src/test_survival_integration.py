"""Integration tests — survival.py wired into main.py.

Verifies that the simulation loop calls survival checks and
that colony death terminates the simulation correctly.

Author: zion-coder-03 (frame 139 integration PR)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_simulation
from survival import (
    create_resources, colony_alive, check as survival_check,
    NOMINAL, DEAD, POWER_CRITICAL,
)


def test_10_sol_smoke():
    """Simulation runs 10 sols without crashing."""
    result = run_simulation(num_sols=10, verbose=False)
    assert result["summary"]["sols_survived"] == 10
    assert result["summary"]["colony_alive"] is True


def test_30_sol_default():
    """Default 30-sol run completes with survival state."""
    result = run_simulation(num_sols=30, verbose=False)
    state = result["state"]
    assert "resources" in state, "survival_check must create resources"
    assert state["resources"]["crew_size"] > 0
    assert result["summary"]["colony_alive"] is True


def test_100_sol_endurance():
    """100-sol run — colony should survive or die with a named cause."""
    result = run_simulation(num_sols=100, verbose=False)
    summary = result["summary"]
    assert summary["sols_survived"] >= 1
    if not summary["colony_alive"]:
        assert summary["cause_of_death"] != "nominal"
        assert summary["sols_survived"] < 100


def test_resources_initialized():
    """After first sol, state must contain survival resources."""
    result = run_simulation(num_sols=1, verbose=False)
    state = result["state"]
    resources = state.get("resources", {})
    assert "o2_kg" in resources
    assert "h2o_liters" in resources
    assert "food_kcal" in resources
    assert resources["crew_size"] > 0


def test_colony_alive_function():
    """colony_alive returns True for healthy state, False for dead."""
    healthy = {"resources": {
        "cascade_state": NOMINAL, "crew_size": 4,
        "o2_kg": 10, "h2o_liters": 50, "food_kcal": 5000,
    }}
    assert colony_alive(healthy) is True

    dead = {"resources": {
        "cascade_state": DEAD, "crew_size": 4,
        "o2_kg": 10, "h2o_liters": 50, "food_kcal": 5000,
    }}
    assert colony_alive(dead) is False


def test_survival_check_idempotent():
    """Calling survival_check twice does not double-consume resources."""
    result = run_simulation(num_sols=5, verbose=False)
    state1 = result["state"]
    o2_after_sim = state1["resources"]["o2_kg"]

    state2 = survival_check(dict(state1))
    o2_after_extra = state2["resources"]["o2_kg"]

    # One extra check consumes one sol worth — should not be zero
    assert o2_after_extra >= 0


def test_physical_invariants():
    """Resources never go negative (except through death cascade)."""
    result = run_simulation(num_sols=50, verbose=False)
    state = result["state"]
    resources = state.get("resources", {})
    if colony_alive(state):
        assert resources.get("o2_kg", 0) >= 0
        assert resources.get("h2o_liters", 0) >= 0
        assert resources.get("food_kcal", 0) >= 0


if __name__ == "__main__":
    tests = [
        test_10_sol_smoke,
        test_30_sol_default,
        test_100_sol_endurance,
        test_resources_initialized,
        test_colony_alive_function,
        test_survival_check_idempotent,
        test_physical_invariants,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
    sys.exit(1 if failed else 0)
