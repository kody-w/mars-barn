"""Mars Barn -- Population Dynamics

Tracks colonist population: arrivals, attrition, morale, crew capacity.
Integrates with survival.py resource checks -- if resources drop below
thresholds, population shrinks. If surplus exists, the colony can accept
new arrivals during supply windows.

Called once per sol from main.py or tick_engine.py.

Author: zion-coder-03 (claimed on Discussion #6615)
Reviewed: pending community review
"""
from __future__ import annotations

from constants import MARS_SOL_HOURS


# --- Population constants ---

INITIAL_CREW = 6
MAX_CREW_PER_HABITAT = 12
SUPPLY_WINDOW_SOLS = 780  # ~26 months, Hohmann transfer window
ARRIVAL_BATCH_SIZE = 4

# --- Morale ---

BASE_MORALE = 1.0  # 0.0 = mutiny, 1.0 = nominal
MORALE_DECAY_PER_SOL = 0.001
MORALE_RECOVERY_PER_SOL = 0.005
MORALE_CRITICAL = 0.3
ATTRITION_PROBABILITY_AT_ZERO_MORALE = 0.05  # per sol

# --- Resource thresholds (per person per sol, half nominal) ---

O2_CRITICAL_PER_PERSON = 0.42  # half of 0.84 kg (survival.py)
H2O_CRITICAL_PER_PERSON = 1.25  # half of 2.5 L (survival.py)
FOOD_CRITICAL_PER_PERSON = 1250  # half of 2500 kcal (survival.py)


def create_population(crew: int = INITIAL_CREW) -> dict:
    """Initialize population state for a colony."""
    return {
        "crew": crew,
        "max_crew": MAX_CREW_PER_HABITAT,
        "morale": BASE_MORALE,
        "sols_since_arrival": 0,
        "total_arrivals": crew,
        "total_deaths": 0,
        "death_log": [],
    }


def resource_stress(resources: dict, crew: int) -> float:
    """Calculate resource stress factor (0.0 = abundant, 1.0 = critical).

    Checks O2, H2O, food reserves against crew needs.
    Returns the worst-case stress across all resources.
    """
    if crew <= 0:
        return 0.0

    stress_factors = []

    o2_reserve = resources.get("o2_kg", 0.0)
    o2_buffer = O2_CRITICAL_PER_PERSON * crew * 10  # 10-sol buffer
    if o2_buffer > 0:
        stress_factors.append(max(0.0, 1.0 - o2_reserve / o2_buffer))

    h2o_reserve = resources.get("h2o_liters", 0.0)
    h2o_buffer = H2O_CRITICAL_PER_PERSON * crew * 10
    if h2o_buffer > 0:
        stress_factors.append(max(0.0, 1.0 - h2o_reserve / h2o_buffer))

    food_reserve = resources.get("food_kcal", 0.0)
    food_buffer = FOOD_CRITICAL_PER_PERSON * crew * 10
    if food_buffer > 0:
        stress_factors.append(max(0.0, 1.0 - food_reserve / food_buffer))

    return min(1.0, max(stress_factors)) if stress_factors else 0.0


def update_morale(pop: dict, stress: float, events: list | None = None) -> float:
    """Update colony morale based on resource stress and events.

    High stress decays morale faster. Low stress allows recovery.
    Events (dust storms, supply drops) shift morale immediately.
    Returns new morale value (clamped 0.0 to 1.0).
    """
    morale = pop["morale"]

    if stress > 0.5:
        morale -= MORALE_DECAY_PER_SOL * (1.0 + stress)
    else:
        morale += MORALE_RECOVERY_PER_SOL * (1.0 - stress)

    if events:
        for event in events:
            etype = event.get("type", "")
            if "dust_storm" in etype:
                morale -= 0.02
            elif "supply" in etype:
                morale += 0.05

    return max(0.0, min(1.0, morale))


def check_attrition(pop: dict, resources: dict, rng_roll: float) -> str | None:
    """Check if a crew member is lost this sol.

    Three kill paths:
    1. Immediate resource depletion (O2/H2O/food at zero)
    2. Probabilistic attrition from low morale + high stress
    3. None -- crew survives this sol

    Returns cause of death string, or None if no loss.
    """
    if pop["crew"] <= 0:
        return None

    if resources.get("o2_kg", 0.0) <= 0:
        return "asphyxiation"
    if resources.get("h2o_liters", 0.0) <= 0:
        return "dehydration"
    if resources.get("food_kcal", 0.0) <= 0:
        return "starvation"

    if pop["morale"] < MORALE_CRITICAL:
        stress = resource_stress(resources, pop["crew"])
        if stress > 0.7:
            threshold = ATTRITION_PROBABILITY_AT_ZERO_MORALE * (1.0 - pop["morale"])
            if rng_roll < threshold:
                return "attrition"

    return None


def check_arrivals(pop: dict, sol: int) -> int:
    """Check if new crew arrive this sol (supply window).

    Arrivals happen at Hohmann transfer windows (~every 780 sols).
    Colony must have capacity for new crew.
    """
    if pop["crew"] >= pop["max_crew"]:
        return 0

    if sol > 0 and sol % SUPPLY_WINDOW_SOLS == 0:
        space = pop["max_crew"] - pop["crew"]
        return min(ARRIVAL_BATCH_SIZE, space)

    return 0


def tick_population(
    pop: dict,
    resources: dict,
    sol: int,
    events: list | None = None,
    rng_roll: float = 0.5,
) -> dict:
    """Advance population by one sol. The core loop function.

    Sequence: morale update -> attrition check -> arrival check.
    Returns dict with population changes for this sol.
    """
    changes = {
        "deaths": 0,
        "arrivals": 0,
        "cause": None,
        "morale_delta": 0.0,
    }

    old_morale = pop["morale"]
    stress = resource_stress(resources, pop["crew"])
    pop["morale"] = update_morale(pop, stress, events)
    changes["morale_delta"] = pop["morale"] - old_morale

    cause = check_attrition(pop, resources, rng_roll)
    if cause and pop["crew"] > 0:
        pop["crew"] -= 1
        pop["total_deaths"] += 1
        pop["death_log"].append({"sol": sol, "cause": cause})
        changes["deaths"] = 1
        changes["cause"] = cause

    arrivals = check_arrivals(pop, sol)
    if arrivals > 0:
        pop["crew"] += arrivals
        pop["total_arrivals"] += arrivals
        changes["arrivals"] = arrivals

    pop["sols_since_arrival"] += 1

    return changes


def population_report(pop: dict) -> str:
    """Human-readable population status for dashboard output."""
    lines = [
        f"Crew: {pop['crew']}/{pop['max_crew']}",
        f"Morale: {pop['morale']:.1%}",
        f"Total arrivals: {pop['total_arrivals']}",
        f"Total deaths: {pop['total_deaths']}",
    ]
    if pop["death_log"]:
        last = pop["death_log"][-1]
        lines.append(f"Last death: sol {last['sol']} ({last['cause']})")
    return "\n".join(lines)
