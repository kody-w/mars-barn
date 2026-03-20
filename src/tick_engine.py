#!/usr/bin/env python3
"""Marsbarn Persistent Colony Tick Engine

Loads colonies from data/colonies.json, simulates one Mars Sol
of physics (solar irradiance and thermal regulation), updates their
stats natively, handles life/death thresholds, and saves back to disk.
"""
import os
import sys
import json
import random
from pathlib import Path

# Ensure local imports work for solar and thermal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import LIFE_SUPPORT_BASE_KWH_PER_SOL

try:
    from solar import daily_energy
    from thermal import simulate_sol
    from mars_climate import dust_storm_stats
except ImportError as e:
    print(f"Error importing physics modules: {e}")
    sys.exit(1)

STATE_FILE = Path(__file__).parent.parent / "data" / "colonies.json"
SOLAR_LONGITUDE_ADVANCE = 0.5  # degrees per sol (approximate)
SUPPLY_DROP_PROBABILITY = 0.10  # per sol
BASE_LIFE_SUPPORT_KWH = LIFE_SUPPORT_BASE_KWH_PER_SOL
PANEL_ARRAY_SCALE = 10  # multiplier vs 100 m² reference array
DIGITAL_TWIN_THRESHOLD_SOLS = 365
DIGITAL_TWIN_PROBABILITY = 0.05  # chance per sol after threshold


def get_mars_conditions(ls: float) -> dict:
    """Return current Mars weather conditions for a given solar longitude.

    Wraps mars_climate.py lookup tables into a single dict that
    tick_engine and future modules can consume. Called ONCE per sol
    in main(), shared across all colonies (weather is planetary).
    """
    any_prob, regional_prob, global_prob, mean_sev, max_sev = dust_storm_stats(ls)
    return {
        "dust_any_prob": any_prob,
        "dust_regional_prob": regional_prob,
        "dust_global_prob": global_prob,
        "dust_mean_severity": mean_sev,
        "dust_max_severity": max_sev,
        "solar_longitude": ls,
    }


def resolve_weather(conditions: dict) -> tuple:
    """Roll weather events from seasonal probabilities.

    Returns (dust_storm, global_storm, event_str).
    Called ONCE per sol — all colonies share the same weather.
    """
    dust_storm = random.random() < conditions["dust_any_prob"]
    global_storm = False
    if dust_storm and conditions["dust_any_prob"] > 0:
        global_storm = random.random() < (
            conditions["dust_global_prob"] / conditions["dust_any_prob"]
        )

    ls = conditions["solar_longitude"]
    if global_storm:
        event_str = f"GLOBAL dust storm! Ls {ls:.0f}. Solar generation near zero."
    elif dust_storm:
        event_str = f"Regional dust event at Ls {ls:.0f}. Solar output reduced."
    else:
        event_str = f"Weather nominal. Ls {ls:.0f}, dust prob {conditions['dust_any_prob']:.0%}."

    return dust_storm, global_storm, event_str


def tick_colony(colony, current_ls, dust_storm, event_str):
    """Simulate one sol of colony physics: solar, thermal, events."""
    if colony.get("status") != "ALIVE":
        return colony

    stats = colony.get("stats", {})
    batt = stats.get("battery_reserves_kwh", 0.0)
    supplies = stats.get("supply_reserves_tons", 0.0)
    solar_eff = stats.get("solar_efficiency", 1.0)
    r_val = stats.get("thermal_insulation", 12.0)

    supply_drop = random.random() < SUPPLY_DROP_PROBABILITY
    if supply_drop and not dust_storm:
        supplies += 50.0
        event_str = "Orbital tether payload successfully captured (+50t supplies)."

    energy_res = daily_energy(
        solar_longitude=current_ls,
        dust_storm=dust_storm,
        solar_multiplier=solar_eff
    )
    generated_kwh = energy_res["total_kwh"] * PANEL_ARRAY_SCALE

    thermal_res = simulate_sol(
        solar_longitude=current_ls,
        r_value=r_val,
        dust_storm=dust_storm,
        rtg_power_w=0.0
    )
    heating_kwh = thermal_res["heating_kwh"]
    total_consumed = heating_kwh + BASE_LIFE_SUPPORT_KWH

    batt += generated_kwh - total_consumed

    if batt < 0:
        colony["status"] = "DEAD"
        colony["last_event"] = (
            f"CRITICAL FAILURE: Battery depleted fighting thermal deficit. "
            f"Died on Sol {colony.get('age_sols', 0) + 1}. Post-Mortem: {event_str}"
        )
        batt = 0.0
    else:
        if colony.get("age_sols", 0) > DIGITAL_TWIN_THRESHOLD_SOLS and random.random() < DIGITAL_TWIN_PROBABILITY:
            colony["status"] = "DIGITAL_TWIN"
            colony["last_event"] = "Surpassed 1-year baseline organically. Flagged for 1:1 physical deployment."
        else:
            colony["age_sols"] = colony.get("age_sols", 0) + 1
            colony["last_event"] = event_str

    stats["battery_reserves_kwh"] = round(batt, 2)
    stats["supply_reserves_tons"] = round(supplies, 2)
    colony["stats"] = stats

    return colony


def main():
    if not STATE_FILE.exists():
        print(f"No state file found at {STATE_FILE}")
        return

    with open(STATE_FILE, "r") as f:
        colonies = json.load(f)

    base_ls = (colonies[0].get("age_sols", 0) * SOLAR_LONGITUDE_ADVANCE) % 360 if colonies else 0.0

    # Weather computed ONCE per sol, shared across all colonies
    conditions = get_mars_conditions(base_ls)
    dust_storm, global_storm, event_str = resolve_weather(conditions)

    print("=== Marsbarn Colony Tick Engine ===")
    print(f"Current Solar Longitude: ~{base_ls:.1f}°")
    print(f"Weather: {event_str}")

    updated = []
    for c in colonies:
        res = tick_colony(c, base_ls, dust_storm, event_str)
        updated.append(res)

    with open(STATE_FILE, "w") as f:
        json.dump(updated, f, indent=2)


if __name__ == "__main__":
    main()
