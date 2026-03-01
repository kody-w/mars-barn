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

try:
    from solar import daily_energy
    from thermal import simulate_sol
except ImportError as e:
    print(f"Error importing physics modules: {e}")
    sys.exit(1)

STATE_FILE = Path(__file__).parent.parent / "data" / "colonies.json"
SOLAR_LONGITUDE_ADVANCE = 0.5  # degrees per sol roughly

def tick_colony(colony, current_ls):
    if colony.get("status") != "ALIVE":
        return colony

    stats = colony.get("stats", {})
    batt = stats.get("battery_reserves_kwh", 0.0)
    supplies = stats.get("supply_reserves_tons", 0.0)
    solar_eff = stats.get("solar_efficiency", 1.0)
    r_val = stats.get("thermal_insulation", 12.0)
    
    # Random Events
    dust_storm = random.random() < 0.15
    supply_drop = random.random() < 0.10
    
    event_str = "Weather nominal."
    if dust_storm:
        event_str = "Global dust storm active. Solar generation plummeted."
    elif supply_drop:
        supplies += 50.0
        event_str = "Orbital tether payload successfully captured (+50t supplies)."
        
    # Physics Simulation
    # 1. Solar generation for this sol
    energy_res = daily_energy(
        solar_longitude=current_ls, 
        dust_storm=dust_storm, 
        solar_multiplier=solar_eff
    )
    generated_kwh = energy_res["total_kwh"] * 10  # Assume 1000m^2 array vs 100
    
    # 2. Thermal heating required
    thermal_res = simulate_sol(
        solar_longitude=current_ls, 
        r_value=r_val, 
        dust_storm=dust_storm,
        rtg_power_w=0.0 # pure solar test
    )
    heating_kwh = thermal_res["heating_kwh"]
    
    # Also base life support load (say 500 kWh/sol)
    base_load = 500.0
    total_consumed = heating_kwh + base_load
    
    # Update state
    batt += generated_kwh - total_consumed
    
    if batt < 0:
        colony["status"] = "DEAD"
        colony["last_event"] = f"CRITICAL FAILURE: Battery depleted fighting thermal deficit. Died on Sol {colony.get('age_sols',0)+1}. Post-Mortem: {event_str}"
        batt = 0.0
    else:
        # Check Digital Twin pitch
        if colony.get("age_sols", 0) > 365 and random.random() < 0.05:
            colony["status"] = "DIGITAL_TWIN"
            colony["last_event"] = "Surpassed 1-year baseline organically. Flagged for 1:1 physical deployment."
        else:
            colony["age_sols"] = colony.get("age_sols", 0) + 1
            colony["last_event"] = event_str
            
    stats["battery_reserves_kwh"] = round(batt, 2)
    stats["supply_reserves_tons"] = round(supplies, 2)
    colony["stats"] = stats
    
    # Print status to console for logging
    print(f"[{colony['id']}] Status: {colony['status']} | Age: {colony.get('age_sols',0)} Sols | Gen: {generated_kwh:.1f} kWh | Con: {total_consumed:.1f} kWh | Batt: {batt:.1f} kWh | Event: {colony['last_event']}")
    
    return colony


def main():
    if not STATE_FILE.exists():
        print(f"No state file found at {STATE_FILE}")
        return

    with open(STATE_FILE, "r") as f:
        colonies = json.load(f)

    # Use a shared Ls that advances
    # We can fake the Ls by grabbing age of first colony
    base_ls = (colonies[0].get("age_sols", 0) * SOLAR_LONGITUDE_ADVANCE) % 360 if colonies else 0.0

    print("=== Marsbarn Colony Tick Engine ===")
    print(f"Current Solar Longitude: ~{base_ls:.1f}°")
    
    updated = []
    for c in colonies:
        res = tick_colony(c, base_ls)
        updated.append(res)
        
    with open(STATE_FILE, "w") as f:
        json.dump(updated, f, indent=2)

if __name__ == "__main__":
    main()
