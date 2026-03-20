"""Tests for population.py — Mars Barn population dynamics.

Covers all 7 public functions. Physical invariants:
- Crew count is never negative
- Morale stays in [0.0, 1.0]
- Resource stress stays in [0.0, 1.0]
- Deaths require a named cause
- Arrivals only at supply windows with capacity

Author: zion-coder-10 (claimed on Discussion #6681, #6689)
"""
from __future__ import annotations

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
    ARRIVAL_BATCH_SIZE,
    BASE_MORALE,
    MORALE_CRITICAL,
)


# --- create_population ---

def test_create_population_defaults():
    pop = create_population()
    assert pop["crew"] == INITIAL_CREW
    assert pop["max_crew"] == MAX_CREW_PER_HABITAT
    assert pop["morale"] == BASE_MORALE
    assert pop["total_arrivals"] == INITIAL_CREW
    assert pop["total_deaths"] == 0
    assert pop["death_log"] == []


def test_create_population_custom_crew():
    pop = create_population(crew=3)
    assert pop["crew"] == 3
    assert pop["total_arrivals"] == 3


# --- resource_stress ---

def test_resource_stress_abundant():
    resources = {"o2_kg": 1000.0, "h2o_liters": 1000.0, "food_kcal": 500000.0}
    s = resource_stress(resources, 6)
    assert s < 0.1, f"Expected low stress with abundant resources, got {s}"


def test_resource_stress_critical():
    resources = {"o2_kg": 0.0, "h2o_liters": 0.0, "food_kcal": 0.0}
    s = resource_stress(resources, 6)
    assert s == 1.0, f"Expected max stress with zero resources, got {s}"


def test_resource_stress_zero_crew():
    resources = {"o2_kg": 0.0, "h2o_liters": 0.0, "food_kcal": 0.0}
    s = resource_stress(resources, 0)
    assert s == 0.0, "Zero crew should mean zero stress"


def test_resource_stress_partial():
    resources = {"o2_kg": 25.0, "h2o_liters": 75.0, "food_kcal": 75000.0}
    s = resource_stress(resources, 6)
    assert 0.0 < s < 1.0, f"Partial resources should give partial stress, got {s}"


# --- update_morale ---

def test_update_morale_recovery_low_stress():
    pop = create_population()
    pop["morale"] = 0.5
    new_morale = update_morale(pop, stress=0.1)
    assert new_morale > 0.5, "Low stress should recover morale"


def test_update_morale_decay_high_stress():
    pop = create_population()
    pop["morale"] = 0.8
    new_morale = update_morale(pop, stress=0.8)
    assert new_morale < 0.8, "High stress should decay morale"


def test_update_morale_clamped_high():
    pop = create_population()
    pop["morale"] = 0.999
    new_morale = update_morale(pop, stress=0.0)
    assert new_morale <= 1.0, "Morale must not exceed 1.0"


def test_update_morale_clamped_low():
    pop = create_population()
    pop["morale"] = 0.001
    new_morale = update_morale(pop, stress=1.0)
    assert new_morale >= 0.0, "Morale must not go below 0.0"


def test_update_morale_dust_storm_hurts():
    pop = create_population()
    pop["morale"] = 0.5
    no_event = update_morale(pop, stress=0.3)
    pop["morale"] = 0.5
    with_storm = update_morale(pop, stress=0.3, events=[{"type": "dust_storm"}])
    assert with_storm < no_event, "Dust storm should reduce morale"


def test_update_morale_supply_helps():
    pop = create_population()
    pop["morale"] = 0.5
    no_event = update_morale(pop, stress=0.3)
    pop["morale"] = 0.5
    with_supply = update_morale(pop, stress=0.3, events=[{"type": "supply_drop"}])
    assert with_supply > no_event, "Supply drop should boost morale"


# --- check_attrition ---

def test_check_attrition_no_o2():
    pop = create_population()
    resources = {"o2_kg": 0.0, "h2o_liters": 100.0, "food_kcal": 100000.0}
    cause = check_attrition(pop, resources, rng_roll=0.5)
    assert cause == "asphyxiation"


def test_check_attrition_no_water():
    pop = create_population()
    resources = {"o2_kg": 100.0, "h2o_liters": 0.0, "food_kcal": 100000.0}
    cause = check_attrition(pop, resources, rng_roll=0.5)
    assert cause == "dehydration"


def test_check_attrition_no_food():
    pop = create_population()
    resources = {"o2_kg": 100.0, "h2o_liters": 100.0, "food_kcal": 0.0}
    cause = check_attrition(pop, resources, rng_roll=0.5)
    assert cause == "starvation"


def test_check_attrition_healthy_crew():
    pop = create_population()
    resources = {"o2_kg": 100.0, "h2o_liters": 100.0, "food_kcal": 100000.0}
    cause = check_attrition(pop, resources, rng_roll=0.5)
    assert cause is None, "Healthy crew should have no attrition"


def test_check_attrition_zero_crew():
    pop = create_population()
    pop["crew"] = 0
    resources = {"o2_kg": 0.0, "h2o_liters": 0.0, "food_kcal": 0.0}
    cause = check_attrition(pop, resources, rng_roll=0.0)
    assert cause is None, "Zero crew means nobody can die"


def test_check_attrition_low_morale_high_roll():
    pop = create_population()
    pop["morale"] = 0.1
    resources = {"o2_kg": 1.0, "h2o_liters": 1.0, "food_kcal": 1000.0}
    cause = check_attrition(pop, resources, rng_roll=0.99)
    assert cause is None, "High roll should prevent attrition"


# --- check_arrivals ---

def test_check_arrivals_at_window():
    pop = create_population()
    arrivals = check_arrivals(pop, sol=SUPPLY_WINDOW_SOLS)
    assert arrivals > 0, f"Should get arrivals at sol {SUPPLY_WINDOW_SOLS}"
    assert arrivals <= ARRIVAL_BATCH_SIZE


def test_check_arrivals_off_window():
    pop = create_population()
    arrivals = check_arrivals(pop, sol=100)
    assert arrivals == 0, "No arrivals outside supply window"


def test_check_arrivals_full_colony():
    pop = create_population(crew=MAX_CREW_PER_HABITAT)
    arrivals = check_arrivals(pop, sol=SUPPLY_WINDOW_SOLS)
    assert arrivals == 0, "Full colony cannot accept arrivals"


def test_check_arrivals_partial_capacity():
    pop = create_population(crew=MAX_CREW_PER_HABITAT - 2)
    arrivals = check_arrivals(pop, sol=SUPPLY_WINDOW_SOLS)
    assert arrivals == 2, "Should only fill remaining capacity"


# --- tick_population ---

def test_tick_population_normal_sol():
    pop = create_population()
    resources = {"o2_kg": 500.0, "h2o_liters": 500.0, "food_kcal": 300000.0}
    changes = tick_population(pop, resources, sol=10)
    assert changes["deaths"] == 0
    assert changes["arrivals"] == 0
    assert pop["crew"] == INITIAL_CREW


def test_tick_population_death_sol():
    pop = create_population()
    resources = {"o2_kg": 0.0, "h2o_liters": 100.0, "food_kcal": 100000.0}
    changes = tick_population(pop, resources, sol=10, rng_roll=0.5)
    assert changes["deaths"] == 1
    assert changes["cause"] == "asphyxiation"
    assert pop["crew"] == INITIAL_CREW - 1
    assert len(pop["death_log"]) == 1


def test_tick_population_arrival_sol():
    pop = create_population()
    resources = {"o2_kg": 500.0, "h2o_liters": 500.0, "food_kcal": 300000.0}
    changes = tick_population(pop, resources, sol=SUPPLY_WINDOW_SOLS)
    assert changes["arrivals"] > 0
    assert pop["crew"] > INITIAL_CREW


def test_tick_population_crew_never_negative():
    pop = create_population(crew=2)
    empty = {"o2_kg": 0.0, "h2o_liters": 0.0, "food_kcal": 0.0}
    for sol in range(1, 101):
        tick_population(pop, empty, sol=sol, rng_roll=0.0)
        assert pop["crew"] >= 0, f"Crew went negative on sol {sol}"


# --- population_report ---

def test_population_report_format():
    pop = create_population()
    report = population_report(pop)
    assert "Crew:" in report
    assert "Morale:" in report
    assert "6/12" in report


def test_population_report_with_deaths():
    pop = create_population()
    pop["death_log"].append({"sol": 42, "cause": "asphyxiation"})
    pop["total_deaths"] = 1
    report = population_report(pop)
    assert "Last death:" in report
    assert "asphyxiation" in report


# --- Integration: 10-sol smoke test ---

def test_ten_sol_run():
    pop = create_population()
    resources = {"o2_kg": 1000.0, "h2o_liters": 1000.0, "food_kcal": 500000.0}
    for sol in range(1, 11):
        tick_population(pop, resources, sol=sol, rng_roll=0.5)
    assert pop["crew"] == INITIAL_CREW, "Colony should survive 10 comfortable sols"
    assert pop["morale"] > 0.9, "Morale should stay high with abundant resources"
    assert pop["total_deaths"] == 0
