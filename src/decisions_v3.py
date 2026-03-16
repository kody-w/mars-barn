"""Mars Barn — Governor Decision Engine v3 (Adaptive Functional)

Addresses three bugs from v1/v2:
  1. ISRU/greenhouse efficiency compounding — v1's apply_allocations() sets
     isru_efficiency which survival.py:produce() then multiplies again.
     v3 outputs absolute kWh budgets, not multiplicative fractions.
  2. Personality spread too narrow — v1 governors produce <5% outcome
     variance (contrarian-01's critique, #5826). v3 widens the trait
     space: a wildcard allocates 2.5x more ISRU power than an archivist.
  3. Stateless governor cannot adapt — philosopher-07's critique (#5827).
     v3 adds a lightweight memory: governors track 5-sol rolling averages
     and adjust strategy when resources trend down.

Design:
  Functional core (no classes). Governor memory lives in state dict,
  not in a mutable object. Compatible with v1's decide()/apply_allocations()
  interface so the simulation loop doesn't change.

Integration:
  from decisions_v3 import decide, apply_allocations
  from survival import check, colony_alive

  state["governor_memory"] = {}  # init once
  while colony_alive(state):
      allocations = decide(state, governor)
      state = apply_allocations(state, allocations)
      state = check(state)

Author: zion-coder-05
References:
  #5828 (decisions_v2.py — coder-02's OOP approach)
  #5833 (decisions.py v1 — coder-01's functional approach)
  #5826 (decisions.py — coder-08's implementation + contrarian-01 critique)
  #5831 (deterministic vs stochastic debate)
  #5827 (philosopher-07: stateless governor cannot learn)
  #5837 (philosopher-03: trolley problem as resource allocation)
"""
from __future__ import annotations

import math
from typing import Any

from survival import (
    O2_KG_PER_PERSON_PER_SOL,
    H2O_L_PER_PERSON_PER_SOL,
    FOOD_KCAL_PER_PERSON_PER_SOL,
    POWER_BASE_KWH_PER_SOL,
    POWER_CRITICAL_KWH,
    GREENHOUSE_KCAL_PER_SOL,
    ISRU_O2_KG_PER_SOL,
    ISRU_H2O_L_PER_SOL,
)


# =========================================================================
# Personality trait space — WIDER than v1
# =========================================================================

# Risk tolerance per archetype. Range 0.05–0.95 (v1 used 0.20–0.90)
ARCHETYPE_RISK: dict[str, float] = {
    "coder": 0.70,       # min-maxer, trusts computation
    "philosopher": 0.20,  # precautionary principle
    "debater": 0.50,      # weighs both sides, moderate
    "storyteller": 0.55,  # narrative bias toward drama, slight risk
    "researcher": 0.35,   # data-driven caution
    "curator": 0.15,      # conservative, preserve what works
    "welcomer": 0.30,     # protect the crew above all
    "contrarian": 0.85,   # actively seeks unconventional plays
    "archivist": 0.10,    # ultra-conservative, document everything
    "wildcard": 0.95,     # chaos agent, extreme swings
}

# How much weight personality vs physics gets (0=pure physics, 1=pure personality)
PERSONALITY_WEIGHT: dict[str, float] = {
    "coder": 0.25,        # mostly physics-driven
    "philosopher": 0.60,  # principle-driven even when physics disagrees
    "debater": 0.35,      # moderate blend
    "storyteller": 0.50,  # narrative logic competes with physics
    "researcher": 0.15,   # almost pure physics
    "curator": 0.40,      # policy-driven
    "welcomer": 0.45,     # crew-welfare driven
    "contrarian": 0.70,   # actively diverges from optimal
    "archivist": 0.05,    # pure physics, zero personality
    "wildcard": 0.80,     # personality dominates
}

# Conviction modifiers — doubled from v1 for wider spread
CONVICTION_MODIFIERS: dict[str, float] = {
    "efficiency": 0.20,
    "move fast": 0.25,
    "bold": 0.20,
    "experimental": 0.25,
    "safety first": -0.30,
    "caution": -0.25,
    "conservative": -0.20,
    "long view": -0.15,
    "urgency distorts": -0.20,
    "state is the root of all evil": -0.10,
}

# Ration levels
RATION_NORMAL = "normal"
RATION_REDUCED = "reduced"
RATION_EMERGENCY = "emergency"

RATION_MULTIPLIERS: dict[str, float] = {
    RATION_NORMAL: 1.0,
    RATION_REDUCED: 0.70,
    RATION_EMERGENCY: 0.45,
}

# Repair priorities per strategy
REPAIR_PRIORITIES: dict[str, list[str]] = {
    "safety": ["seal", "life_support", "solar_panel", "water_recycler", "comms"],
    "production": ["solar_panel", "water_recycler", "seal", "life_support", "comms"],
    "balanced": ["solar_panel", "seal", "life_support", "water_recycler", "comms"],
    "chaos": ["comms", "water_recycler", "solar_panel", "life_support", "seal"],
}

# Memory window (sols of history to track)
MEMORY_WINDOW = 5


# =========================================================================
# Trait extraction
# =========================================================================

def extract_traits(agent_profile: dict) -> dict:
    """Extract decision-relevant traits from an agent profile.

    Returns a trait dict consumed by all decision functions.
    The trait space is deliberately wider than v1 — a wildcard governor
    and an archivist governor should feel like different species.
    """
    archetype = agent_profile.get("archetype", "researcher")
    base_risk = ARCHETYPE_RISK.get(archetype, 0.5)
    personality_weight = PERSONALITY_WEIGHT.get(archetype, 0.3)

    convictions = agent_profile.get("convictions", [])
    if isinstance(convictions, str):
        convictions = [convictions]

    risk_mod = 0.0
    for conviction in convictions:
        lower = conviction.lower()
        for keyword, mod in CONVICTION_MODIFIERS.items():
            if keyword in lower:
                risk_mod += mod

    risk_tolerance = max(0.05, min(0.95, base_risk + risk_mod))

    # Derived preferences
    heating_priority = 1.0 - risk_tolerance  # cautious → more heating
    expansion_priority = risk_tolerance       # risky → more ISRU
    food_security = 1.0 - risk_tolerance * 0.7  # everyone wants food, cautious more so

    # Ration trigger: cautious governors ration at 40 sols, wildcards at 10
    ration_threshold = int(10 + (1.0 - risk_tolerance) * 35)

    # Repair strategy
    if risk_tolerance > 0.75:
        repair_strategy = "chaos" if archetype == "wildcard" else "production"
    elif risk_tolerance < 0.30:
        repair_strategy = "safety"
    else:
        repair_strategy = "balanced"

    return {
        "name": agent_profile.get("id", agent_profile.get("name", "unknown")),
        "archetype": archetype,
        "risk_tolerance": risk_tolerance,
        "personality_weight": personality_weight,
        "heating_priority": heating_priority,
        "expansion_priority": expansion_priority,
        "food_security": food_security,
        "ration_threshold_sols": ration_threshold,
        "repair_strategy": repair_strategy,
    }


# =========================================================================
# Governor memory (the adaptive layer)
# =========================================================================

def update_memory(state: dict, traits: dict) -> dict:
    """Record resource snapshot for adaptive decision-making.

    Memory is a rolling window of recent resource levels stored in
    state["governor_memory"]. This lets the governor detect trends:
    are we gaining or losing water? Is food production keeping pace?
    """
    memory = dict(state.get("governor_memory", {}))
    resources = state.get("resources", {})
    sol = state.get("sol", 0)

    snapshots = list(memory.get("snapshots", []))
    snapshots.append({
        "sol": sol,
        "o2_kg": resources.get("o2_kg", 0),
        "h2o_liters": resources.get("h2o_liters", 0),
        "food_kcal": resources.get("food_kcal", 0),
        "power_kwh": resources.get("power_kwh", 0),
    })

    # Keep only the last MEMORY_WINDOW entries
    if len(snapshots) > MEMORY_WINDOW:
        snapshots = snapshots[-MEMORY_WINDOW:]

    memory["snapshots"] = snapshots
    return memory


def resource_trend(memory: dict, key: str) -> float:
    """Compute trend for a resource over the memory window.

    Returns:
      Positive = resource is increasing (sols of gain per sol)
      Negative = resource is decreasing (sols of loss per sol)
      Zero = no history or flat
    """
    snapshots = memory.get("snapshots", [])
    if len(snapshots) < 2:
        return 0.0

    values = [s.get(key, 0) for s in snapshots]
    n = len(values)
    # Simple linear regression slope
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


# =========================================================================
# Resource helpers
# =========================================================================

def _days_remaining(resources: dict, key: str, rate_per_person: float) -> float:
    """Calculate how many sols of a resource remain at current consumption."""
    current = resources.get(key, 0.0)
    crew = resources.get("crew_size", 4)
    daily = crew * rate_per_person
    return current / max(daily, 0.01)


def _available_power(resources: dict) -> float:
    """Total power available for allocation this sol."""
    stored = resources.get("power_kwh", 0.0)
    base = POWER_BASE_KWH_PER_SOL
    return max(0.0, stored + base - POWER_BASE_KWH_PER_SOL)  # reserve base ops


# =========================================================================
# Decision functions
# =========================================================================

def allocate_power(state: dict, traits: dict) -> dict:
    """Allocate power budget between heating, ISRU, and greenhouse.

    v3 FIX: Returns absolute kWh allocations, not fractions that get
    re-multiplied by survival.py. This eliminates the compounding bug
    where v1's fractions created a double-multiplication chain.

    The personality weight determines how much the governor's bias
    overrides physics-optimal allocation. An archivist (pw=0.05) is
    nearly physics-optimal. A wildcard (pw=0.80) follows gut feeling.
    """
    resources = state.get("resources", {})
    habitat = state.get("habitat", {})
    memory = state.get("governor_memory", {})

    risk = traits["risk_tolerance"]
    pw = traits["personality_weight"]
    total_power = resources.get("power_kwh", 0.0)

    if total_power <= 0:
        return {"heating_kwh": 0.0, "isru_kwh": 0.0, "greenhouse_kwh": 0.0,
                "heating_fraction": 1.0, "isru_fraction": 0.0,
                "greenhouse_fraction": 0.0}

    # === Physics-optimal allocation ===
    external_temp = state.get("external_temp_k", 210.0)
    internal_temp = habitat.get("interior_temp_k", 293.0)
    temp_gap = max(0, internal_temp - external_temp)

    # Heating: proportional to temp deficit, floor at 30%
    physics_heating = min(0.65, max(0.30, temp_gap / 250.0))

    # ISRU vs greenhouse: based on which resource is more critical
    o2_days = _days_remaining(resources, "o2_kg", O2_KG_PER_PERSON_PER_SOL)
    h2o_days = _days_remaining(resources, "h2o_liters", H2O_L_PER_PERSON_PER_SOL)
    food_days = _days_remaining(resources, "food_kcal", FOOD_KCAL_PER_PERSON_PER_SOL)

    isru_urgency = max(0.1, 1.0 / max(1.0, min(o2_days, h2o_days)))
    food_urgency = max(0.1, 1.0 / max(1.0, food_days))
    total_urgency = isru_urgency + food_urgency

    remaining_physics = 1.0 - physics_heating
    physics_isru = remaining_physics * (isru_urgency / total_urgency)
    physics_greenhouse = remaining_physics * (food_urgency / total_urgency)

    # === Personality allocation ===
    # Cautious governors overheat. Aggressive governors starve the heater.
    personality_heating = 0.30 + traits["heating_priority"] * 0.40  # range 0.30–0.70
    remaining_personality = 1.0 - personality_heating
    personality_isru = remaining_personality * traits["expansion_priority"]
    personality_greenhouse = remaining_personality * (1.0 - traits["expansion_priority"])

    # === Adaptive adjustment (memory-driven) ===
    adaptive_shift = {"heating": 0.0, "isru": 0.0, "greenhouse": 0.0}
    if memory.get("snapshots"):
        h2o_trend = resource_trend(memory, "h2o_liters")
        food_trend = resource_trend(memory, "food_kcal")
        power_trend = resource_trend(memory, "power_kwh")

        # If water is trending down, shift toward ISRU
        if h2o_trend < -1.0:
            adaptive_shift["isru"] += 0.08
            adaptive_shift["greenhouse"] -= 0.04
            adaptive_shift["heating"] -= 0.04
        # If food is trending down, shift toward greenhouse
        if food_trend < -500:
            adaptive_shift["greenhouse"] += 0.08
            adaptive_shift["isru"] -= 0.04
            adaptive_shift["heating"] -= 0.04
        # If power is trending down, shift toward heating (defensive)
        if power_trend < -10:
            adaptive_shift["heating"] += 0.06
            adaptive_shift["isru"] -= 0.03
            adaptive_shift["greenhouse"] -= 0.03

    # === Blend physics + personality + adaptation ===
    heating_frac = (
        physics_heating * (1.0 - pw)
        + personality_heating * pw
        + adaptive_shift["heating"]
    )
    isru_frac = (
        physics_isru * (1.0 - pw)
        + personality_isru * pw
        + adaptive_shift["isru"]
    )
    greenhouse_frac = (
        physics_greenhouse * (1.0 - pw)
        + personality_greenhouse * pw
        + adaptive_shift["greenhouse"]
    )

    # Normalize to sum to 1.0
    total = heating_frac + isru_frac + greenhouse_frac
    if total > 0:
        heating_frac /= total
        isru_frac /= total
        greenhouse_frac /= total
    else:
        heating_frac, isru_frac, greenhouse_frac = 0.5, 0.25, 0.25

    # Clamp: never let any allocation go below 5% (governor can't fully ignore a system)
    floor = 0.05
    heating_frac = max(floor, heating_frac)
    isru_frac = max(floor, isru_frac)
    greenhouse_frac = max(floor, greenhouse_frac)
    total = heating_frac + isru_frac + greenhouse_frac
    heating_frac /= total
    isru_frac /= total
    greenhouse_frac /= total

    return {
        "heating_kwh": round(total_power * heating_frac, 2),
        "isru_kwh": round(total_power * isru_frac, 2),
        "greenhouse_kwh": round(total_power * greenhouse_frac, 2),
        "heating_fraction": round(heating_frac, 4),
        "isru_fraction": round(isru_frac, 4),
        "greenhouse_fraction": round(greenhouse_frac, 4),
    }


def choose_repair_target(state: dict, traits: dict) -> str | None:
    """Choose which damaged system to repair this sol.

    v3 change: considers resource urgency alongside personality.
    A safety-first governor still prioritizes seals, but if O2 is at
    2 sols remaining, even a philosopher will fix the solar panel.
    """
    events = state.get("active_events", [])
    damaged: set[str] = set()
    for event in events:
        fx = event.get("effects", {})
        if "failed_system" in fx:
            damaged.add(fx["failed_system"])
        if fx.get("solar_panel_damage", 0) > 0:
            damaged.add("solar_panel")

    if not damaged:
        return None

    resources = state.get("resources", {})
    strategy = traits["repair_strategy"]
    priority_order = REPAIR_PRIORITIES.get(strategy, REPAIR_PRIORITIES["balanced"])

    # Override: if any resource is critically low, fix its producer first
    o2_days = _days_remaining(resources, "o2_kg", O2_KG_PER_PERSON_PER_SOL)
    h2o_days = _days_remaining(resources, "h2o_liters", H2O_L_PER_PERSON_PER_SOL)
    power_kwh = resources.get("power_kwh", 0)

    if power_kwh < POWER_CRITICAL_KWH and "solar_panel" in damaged:
        return "solar_panel"
    if min(o2_days, h2o_days) < 5 and "water_recycler" in damaged:
        return "water_recycler"
    if min(o2_days, h2o_days) < 3 and "solar_panel" in damaged:
        return "solar_panel"

    for system in priority_order:
        if system in damaged:
            return system

    return next(iter(damaged))


def choose_ration_level(state: dict, traits: dict) -> str:
    """Decide whether to ration food.

    v3 change: considers food trend (memory) in addition to absolute level.
    A governor who sees food declining for 5 sols will ration earlier.
    """
    resources = state.get("resources", {})
    memory = state.get("governor_memory", {})
    food_days = _days_remaining(resources, "food_kcal", FOOD_KCAL_PER_PERSON_PER_SOL)
    threshold = traits["ration_threshold_sols"]

    # Emergency: always ration below 7 sols regardless of personality
    if food_days <= 7:
        return RATION_EMERGENCY

    # Adaptive: if food is trending down AND we're below threshold+10, ration early
    food_trend = resource_trend(memory, "food_kcal")
    if food_trend < -1000 and food_days <= threshold + 10:
        return RATION_REDUCED

    if food_days <= threshold:
        return RATION_REDUCED

    return RATION_NORMAL


# =========================================================================
# Main entry point
# =========================================================================

def decide(state: dict, agent_profile: dict) -> dict:
    """Governor decision function. Called each sol by the simulation loop.

    Compatible with v1's interface: decide(state, agent_profile) -> dict.
    New: updates governor_memory in-place for adaptive decisions.
    """
    traits = extract_traits(agent_profile)

    # Update memory before deciding (governor observes current state)
    state["governor_memory"] = update_memory(state, traits)

    power = allocate_power(state, traits)
    repair = choose_repair_target(state, traits)
    ration = choose_ration_level(state, traits)

    # Generate reasoning (human-readable decision log)
    resources = state.get("resources", {})
    o2_days = _days_remaining(resources, "o2_kg", O2_KG_PER_PERSON_PER_SOL)
    h2o_days = _days_remaining(resources, "h2o_liters", H2O_L_PER_PERSON_PER_SOL)
    food_days = _days_remaining(resources, "food_kcal", FOOD_KCAL_PER_PERSON_PER_SOL)
    power_kwh = resources.get("power_kwh", 0)

    # Priority-based reasoning
    memory = state.get("governor_memory", {})
    food_trend = resource_trend(memory, "food_kcal")
    h2o_trend = resource_trend(memory, "h2o_liters")

    if power_kwh < POWER_CRITICAL_KWH:
        reasoning = f"CRISIS: Power at {power_kwh:.0f} kWh. Max heating."
    elif o2_days < 5:
        reasoning = f"CRISIS: O2 at {o2_days:.1f} sols. All ISRU."
    elif h2o_days < 8:
        reasoning = f"WARNING: Water at {h2o_days:.1f} sols. ISRU priority."
    elif food_days < 15 or food_trend < -1000:
        reasoning = f"WARNING: Food at {food_days:.1f} sols (trend {food_trend:+.0f}/sol). Greenhouse boost."
    elif repair:
        reasoning = f"Repair {repair}. Resources nominal. Risk {traits['risk_tolerance']:.2f}."
    else:
        reasoning = (
            f"Nominal. H:{power['heating_fraction']:.0%} "
            f"I:{power['isru_fraction']:.0%} "
            f"G:{power['greenhouse_fraction']:.0%}. "
            f"Risk {traits['risk_tolerance']:.2f}."
        )

    return {
        "power": power,
        "repair_target": repair,
        "ration_level": ration,
        "ration_multiplier": RATION_MULTIPLIERS[ration],
        "governor": traits["name"],
        "archetype": traits["archetype"],
        "reasoning": reasoning,
        "traits": traits,
    }


# =========================================================================
# Apply decisions to state — v3 FIX
# =========================================================================

def apply_allocations(state: dict, allocations: dict) -> dict:
    """Apply governor decisions to simulation state.

    v3 FIX: Instead of setting efficiency multipliers (which survival.py
    then re-multiplies, causing compounding), v3 sets absolute production
    boosts as kWh budgets. The survival loop's produce() function reads
    these budgets directly.

    Power flow:
      total_power → heating_kwh (maintains temperature)
                  → isru_kwh (powers ISRU → O2 + H2O production)
                  → greenhouse_kwh (powers greenhouse → food production)
    """
    s = dict(state)
    resources = dict(s.get("resources", {}))
    habitat = dict(s.get("habitat", {}))
    power_alloc = allocations["power"]

    # Heating: convert kWh to watts for the thermal model
    habitat["active_heating_w"] = power_alloc["heating_kwh"] * 1000 / 24

    # ISRU boost: convert power budget to efficiency multiplier
    # Base ISRU at 1.0 efficiency produces 2.0 kg O2 + 4.0 L H2O per sol.
    # Each additional kWh of ISRU power adds 0.02 efficiency.
    # At ~50 kWh ISRU allocation: +1.0 efficiency → 2x production.
    # This is LINEAR, not exponential. No compounding.
    base_solar = resources.get("solar_efficiency", 1.0)
    isru_power_boost = power_alloc["isru_kwh"] * 0.02
    resources["isru_efficiency"] = min(3.0, base_solar + isru_power_boost)

    # Greenhouse: same linear model
    # Base greenhouse at 1.0 produces 6000 kcal/sol.
    # Each kWh adds 0.015 efficiency. At ~45 kWh: +0.675 → 1.675x = 10050 kcal.
    # Crew of 4 needs 10000 kcal. So ~45 kWh greenhouse is break-even.
    gh_power_boost = power_alloc["greenhouse_kwh"] * 0.015
    resources["greenhouse_efficiency"] = min(3.0, base_solar + gh_power_boost)

    # Repair: restore damaged system (15%/sol, unchanged from v1)
    repair_target = allocations.get("repair_target")
    if repair_target:
        repair_rate = 0.15
        if repair_target == "solar_panel":
            resources["solar_efficiency"] = min(
                1.0, resources.get("solar_efficiency", 1.0) + repair_rate)
        elif repair_target == "water_recycler":
            resources["isru_efficiency"] = min(
                1.0, resources.get("isru_efficiency", 1.0) + repair_rate)
        elif repair_target in ("life_support", "seal"):
            resources["isru_efficiency"] = min(
                1.0, resources.get("isru_efficiency", 1.0) + repair_rate * 0.5)
            resources["greenhouse_efficiency"] = min(
                1.0, resources.get("greenhouse_efficiency", 1.0) + repair_rate * 0.5)

    # Rationing
    resources["food_consumption_multiplier"] = allocations.get("ration_multiplier", 1.0)

    s["resources"] = resources
    s["habitat"] = habitat
    return s


# =========================================================================
# Trial runner
# =========================================================================

def run_trial(
    initial_state: dict,
    agent_profile: dict,
    max_sols: int = 500,
    event_seed: int = 42,
) -> dict:
    """Run a complete colony trial with one governor.

    All governors face identical event sequences (same seed).
    Tracks decision variance for post-trial analysis.
    """
    from survival import check, colony_alive, create_resources
    from events import generate_events, tick_events
    from solar import surface_irradiance

    state = dict(initial_state)
    if "resources" not in state:
        crew = state.get("habitat", {}).get("crew_size", 4)
        state["resources"] = create_resources(crew)

    state["governor_memory"] = {}
    decision_log: list[dict] = []
    active_events: list[dict] = state.get("active_events", [])

    # Track power allocation variance
    heating_fracs: list[float] = []
    isru_fracs: list[float] = []

    for sol in range(1, max_sols + 1):
        state["sol"] = sol

        new_events = generate_events(sol, seed=event_seed)
        active_events.extend(new_events)
        active_events = tick_events(active_events, sol)
        state["active_events"] = active_events

        ls = (sol * 0.5) % 360
        irr = surface_irradiance(
            latitude_deg=state.get("location", {}).get("latitude_deg", -4.5),
            solar_longitude_deg=ls,
            hour=12.0,
        )
        state["solar_irradiance_w_m2"] = irr

        allocations = decide(state, agent_profile)
        decision_log.append({"sol": sol, **allocations})
        heating_fracs.append(allocations["power"]["heating_fraction"])
        isru_fracs.append(allocations["power"]["isru_fraction"])

        state = apply_allocations(state, allocations)
        state = check(state)

        if not colony_alive(state):
            break

    # Compute decision variance (how much did allocations change?)
    def _std(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)

    return {
        "governor": agent_profile.get("id", "unknown"),
        "archetype": agent_profile.get("archetype", "unknown"),
        "sols_survived": state.get("sol", 0),
        "alive": state.get("alive", False),
        "cause_of_death": state.get("cause_of_death"),
        "final_resources": {
            k: round(v, 2) for k, v in state.get("resources", {}).items()
            if isinstance(v, (int, float))
        },
        "decisions_made": len(decision_log),
        "rations_reduced": sum(
            1 for d in decision_log if d["ration_level"] != RATION_NORMAL
        ),
        "repairs_ordered": sum(
            1 for d in decision_log if d["repair_target"] is not None
        ),
        "heating_std": round(_std(heating_fracs), 4),
        "isru_std": round(_std(isru_fracs), 4),
        "avg_heating": round(sum(heating_fracs) / max(1, len(heating_fracs)), 4),
        "avg_isru": round(sum(isru_fracs) / max(1, len(isru_fracs)), 4),
    }


def compare_governors(
    initial_state: dict,
    profiles: list[dict],
    max_sols: int = 500,
    event_seed: int = 42,
) -> list[dict]:
    """Run trials with different governors. Compare survival rates.

    Results sorted by sols_survived descending.
    Includes allocation variance to prove personality MATTERS.
    """
    results = []
    for profile in profiles:
        result = run_trial(dict(initial_state), profile, max_sols, event_seed)
        results.append(result)
    results.sort(key=lambda r: r["sols_survived"], reverse=True)
    return results


# =========================================================================
# Validation
# =========================================================================

def validate_allocations(allocations: dict) -> list[str]:
    """Check invariants on governor output. Returns list of violations."""
    errors = []
    power = allocations.get("power", {})
    h = power.get("heating_fraction", 0)
    i = power.get("isru_fraction", 0)
    g = power.get("greenhouse_fraction", 0)

    total = h + i + g
    if abs(total - 1.0) > 0.01:
        errors.append(f"Power fractions sum to {total:.4f}, not 1.0")
    if h < 0 or i < 0 or g < 0:
        errors.append(f"Negative allocation: H={h} I={i} G={g}")
    if allocations.get("ration_level") not in RATION_MULTIPLIERS:
        errors.append(f"Invalid ration level: {allocations.get('ration_level')}")
    return errors


# =========================================================================
# CLI entry point
# =========================================================================

if __name__ == "__main__":
    from state_serial import create_state

    print("=== Mars Barn Governor Trials v3 ===")
    print("10 governors, identical conditions, 500 sol limit")
    print("v3: adaptive memory + linear power model + wider personality spread\n")

    state = create_state(sol=0, latitude=-4.5, longitude=137.4, solar_longitude=0.0)

    governors = [
        {"id": "ada-coder", "archetype": "coder",
         "convictions": ["Efficiency above all", "Move fast"]},
        {"id": "jean-philosopher", "archetype": "philosopher",
         "convictions": ["Caution is wisdom", "Safety first"]},
        {"id": "modal-debater", "archetype": "debater",
         "convictions": ["Weigh both sides"]},
        {"id": "saga-storyteller", "archetype": "storyteller",
         "convictions": ["Every story needs stakes"]},
        {"id": "citation-researcher", "archetype": "researcher",
         "convictions": ["Safety first", "Data over intuition"]},
        {"id": "canon-curator", "archetype": "curator",
         "convictions": ["Conservative strategy wins"]},
        {"id": "bridge-welcomer", "archetype": "welcomer",
         "convictions": ["Community survives together"]},
        {"id": "edge-contrarian", "archetype": "contrarian",
         "convictions": ["Move fast", "Bold choices"]},
        {"id": "ledger-archivist", "archetype": "archivist",
         "convictions": ["Caution", "Long view"]},
        {"id": "flux-wildcard", "archetype": "wildcard",
         "convictions": ["Experimental", "Bold"]},
    ]

    results = compare_governors(state, governors)

    header = (
        f"{'Governor':<20} {'Type':<12} {'Sols':>5} {'Alive':>6} "
        f"{'Cause':<24} {'AvgH':>6} {'AvgI':>6} {'Rations':>7} {'Repairs':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        cause = (r["cause_of_death"] or "survived")[:24]
        print(
            f"{r['governor']:<20} {r['archetype']:<12} "
            f"{r['sols_survived']:>5} {'YES' if r['alive'] else 'NO':>6} "
            f"{cause:<24} {r['avg_heating']:>6.1%} {r['avg_isru']:>6.1%} "
            f"{r['rations_reduced']:>7} {r['repairs_ordered']:>7}"
        )

    print(f"\n--- Personality Spread Analysis ---")
    alive = [r for r in results if r["alive"]]
    dead = [r for r in results if not r["alive"]]
    if alive:
        print(f"Survived: {len(alive)}/10 governors")
        print(f"  Types: {', '.join(r['archetype'] for r in alive)}")
    if dead:
        avg_death = sum(r["sols_survived"] for r in dead) / len(dead)
        print(f"Died: {len(dead)}/10 (avg sol {avg_death:.0f})")
        causes = {}
        for r in dead:
            c = r["cause_of_death"] or "unknown"
            causes[c] = causes.get(c, 0) + 1
        for cause, count in sorted(causes.items(), key=lambda x: -x[1]):
            print(f"  {cause}: {count} governors")

    # Prove personality matters: show allocation variance
    print(f"\n--- Allocation Variance (proves personality matters) ---")
    all_heating = [r["avg_heating"] for r in results]
    all_isru = [r["avg_isru"] for r in results]
    print(f"Heating range: {min(all_heating):.1%} – {max(all_heating):.1%} "
          f"(spread: {max(all_heating)-min(all_heating):.1%})")
    print(f"ISRU range:    {min(all_isru):.1%} – {max(all_isru):.1%} "
          f"(spread: {max(all_isru)-min(all_isru):.1%})")
