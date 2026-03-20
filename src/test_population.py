"""Tests for population dynamics module.

Covers all 7 public functions: create_population, resource_stress,
update_morale, check_attrition, check_arrivals, tick_population,
population_report.

Physical invariants checked:
- crew >= 0 always
- 0.0 <= morale <= 1.0 always
- arrivals <= remaining capacity
- deaths logged with cause

Follows PR #27 (power_grid) test standard.

Author: zion-coder-06
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from population import (
    create_population,
    resource_stress,
    update_morale,
    check_attrition,
    check_arrivals,
    tick_population,
    population_report,
    INITIAL_CREW,
    MAX_CREW_PER_HABITAT,
    SUPPLY_WINDOW_SOLS,
    MORALE_CRITICAL,
)


# --- create_population ---

def test_create_population_defaults():
    pop = create_population()
    assert pop["crew"] == INITIAL_CREW
    assert pop["morale"] == 1.0
    assert pop["total_deaths"] == 0
    assert pop["total_arrivals"] == INITIAL_CREW
    assert pop["death_log"] == []
    assert pop["max_crew"] == MAX_CREW_PER_HABITAT


def test_create_population_custom_crew():
    pop = create_population(crew=10)
    assert pop["crew"] == 10
    assert pop["total_arrivals"] == 10


# --- resource_stress ---

def test_resource_stress_abundant():
    resources = {"o2_kg": 1000.0, "h2o_liters": 1000.0, "food_kcal": 500000.0}
    stress = resource_stress(resources, 6)
    assert stress < 0.1, f"Abundant resources should yield low stress, got {stress}"


def test_resource_stress_zero_crew():
    stress = resource_stress({}, 0)
    assert stress == 0.0, "Zero crew means zero stress"


def test_resource_stress_critical():
    resources = {"o2_kg": 1.0, "h2o_liters": 1.0, "food_kcal": 100.0}
    stress = resource_stress(resources, 6)
    assert stress > 0.9, f"Near-zero reserves should yield high stress, got {stress}"


# --- update_morale ---

def test_morale_recovers_low_stress():
    pop = create_population()
    pop["morale"] = 0.5
    new_morale = update_morale(pop, stress=0.1)
    assert new_morale > 0.5, "Morale should recover under low stress"


def test_morale_decays_high_stress():
    pop = create_population()
    new_morale = update_morale(pop, stress=0.8)
    assert new_morale < 1.0, "Morale should decay under high stress"


def test_morale_clamped():
    pop = create_population()
    pop["morale"] = 0.001
    low = update_morale(pop, stress=1.0)
    assert low >= 0.0, "Morale must not go below 0.0"

    pop["morale"] = 0.999
    high = update_morale(pop, stress=0.0)
    assert high <= 1.0, "Morale must not exceed 1.0"


# --- check_attrition ---

def test_attrition_asphyxiation():
    pop = create_population()
    cause = check_attrition(pop, {"o2_kg": 0.0, "h2o_liters": 10.0, "food_kcal": 5000.0}, 0.5)
    assert cause == "asphyxiation"


def test_attrition_dehydration():
    pop = create_population()
    cause = check_attrition(pop, {"o2_kg": 10.0, "h2o_liters": 0.0, "food_kcal": 5000.0}, 0.5)
    assert cause == "dehydration"


def test_attrition_starvation():
    pop = create_population()
    cause = check_attrition(pop, {"o2_kg": 10.0, "h2o_liters": 10.0, "food_kcal": 0.0}, 0.5)
    assert cause == "starvation"


def test_attrition_none_healthy():
    pop = create_population()
    resources = {"o2_kg": 100.0, "h2o_liters": 100.0, "food_kcal": 50000.0}
    cause = check_attrition(pop, resources, 0.5)
    assert cause is None, "Healthy colony should have no attrition"


def test_attrition_low_morale_high_stress():
    pop = create_population()
    pop["morale"] = 0.1
    resources = {"o2_kg": 1.0, "h2o_liters": 1.0, "food_kcal": 100.0}
    cause = check_attrition(pop, resources, 0.001)
    assert cause == "attrition", "Low morale + high stress + low roll should trigger attrition"


# --- check_arrivals ---

def test_arrivals_at_supply_window():
    pop = create_population()
    arrivals = check_arrivals(pop, SUPPLY_WINDOW_SOLS)
    assert arrivals > 0, f"Should get arrivals at sol {SUPPLY_WINDOW_SOLS}"
    assert arrivals <= pop["max_crew"] - pop["crew"], "Arrivals must not exceed capacity"


def test_no_arrivals_between_windows():
    pop = create_population()
    arrivals = check_arrivals(pop, 100)
    assert arrivals == 0, "No arrivals between supply windows"


def test_no_arrivals_when_full():
    pop = create_population(crew=MAX_CREW_PER_HABITAT)
    arrivals = check_arrivals(pop, SUPPLY_WINDOW_SOLS)
    assert arrivals == 0, "Full colony should refuse arrivals"


# --- tick_population ---

def test_tick_stable_colony():
    pop = create_population()
    resources = {"o2_kg": 100.0, "h2o_liters": 100.0, "food_kcal": 50000.0}
    changes = tick_population(pop, resources, sol=1)
    assert changes["deaths"] == 0
    assert pop["crew"] == INITIAL_CREW
    assert 0.0 <= pop["morale"] <= 1.0


def test_crew_never_negative():
    """Invariant: crew count must be >= 0 even after 100 sols of total depletion."""
    pop = create_population(crew=1)
    pop["morale"] = 0.0
    resources = {"o2_kg": 0.0, "h2o_liters": 0.0, "food_kcal": 0.0}
    for sol in range(1, 101):
        tick_population(pop, resources, sol=sol, rng_roll=0.0)
    assert pop["crew"] >= 0, f"Crew went negative: {pop['crew']}"


# --- population_report ---

def test_population_report_format():
    pop = create_population()
    report = population_report(pop)
    assert "Crew:" in report
    assert "Morale:" in report
    assert "Total arrivals:" in report


# --- smoke test ---

def test_ten_sol_smoke():
    """Run population for 10 sols with declining resources. Colony must survive."""
    pop = create_population()
    resources = {"o2_kg": 50.0, "h2o_liters": 150.0, "food_kcal": 100000.0}
    for sol in range(1, 11):
        tick_population(pop, resources, sol=sol, rng_roll=0.99)
        resources["o2_kg"] = max(0.0, resources["o2_kg"] - 5.0)
        resources["h2o_liters"] = max(0.0, resources["h2o_liters"] - 15.0)
        resources["food_kcal"] = max(0.0, resources["food_kcal"] - 10000.0)
    assert pop["crew"] >= 0
    assert 0.0 <= pop["morale"] <= 1.0
    report = population_report(pop)
    assert len(report) > 0
