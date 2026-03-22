#!/usr/bin/env python3
"""Mars Barn — Colony Backtest

Simulates the colony BACKWARDS through historical Mars conditions.
Starting from the current colony state (Sol 1, Ls 37°), runs the
thermal model backwards through a full Mars year (669 sols) to see
how far back the colony WOULD have survived.

This answers: "If this colony had existed for the last Mars year,
would it have made it through winter? Through perihelion dust season?
Through the worst conditions Mars can throw at it?"

Usage:
    python src/backtest.py                # full Mars year backtest
    python src/backtest.py --sols 100     # shorter backtest
    python src/backtest.py --output state/backtest.json  # save results
"""
import json
import math
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from constants import (
    MARS_LS_PER_SOL,
    MARS_ECCENTRICITY,
    HABITAT_SOLAR_PANEL_AREA_M2,
    HABITAT_SOLAR_PANEL_EFFICIENCY,
    HABITAT_INSULATION_R_VALUE,
    HABITAT_HEATER_POWER_W,
)
from thermal import simulate_sol
from atmosphere import temperature_at_altitude
from solar import daily_energy, distance_factor as solar_distance_factor
from events import generate_events

ROOT = os.path.join(os.path.dirname(__file__), "..")
STATE_FILE = os.path.join(ROOT, "state", "colony.json")


def backtest(
    start_ls: float = 37.0,
    start_temp_k: float = 290.8,  # current colony interior temp
    stored_energy_kwh: float = 559.9,
    num_sols: int = 669,  # full Mars year
    latitude: float = -4.5,
    panel_area: float = HABITAT_SOLAR_PANEL_AREA_M2,
    panel_efficiency: float = HABITAT_SOLAR_PANEL_EFFICIENCY,
    r_value: float = HABITAT_INSULATION_R_VALUE,
    heater_power: float = HABITAT_HEATER_POWER_W,
    crew_size: int = 4,
    verbose: bool = True,
) -> dict:
    """Run the colony backwards through historical Mars conditions."""

    temp_k = start_temp_k
    energy_kwh = stored_energy_kwh
    ls = start_ls
    food_kg = 120.0

    timeline = []
    alive = True
    death_sol = None
    death_reason = None

    min_temp_k = temp_k
    max_temp_k = temp_k
    min_energy = energy_kwh
    worst_sol = 0
    storms_survived = 0
    total_heating_kwh = 0.0

    for sol_offset in range(1, num_sols + 1):
        # Go BACKWARDS in Ls (earlier in the Mars year)
        ls = (start_ls - sol_offset * MARS_LS_PER_SOL) % 360

        # Use real measured climate statistics for storm probability
        from mars_climate import dust_storm_stats, interpolate_climate, DUST_STORM_BY_LS
        storm_stats = interpolate_climate(ls, DUST_STORM_BY_LS)
        storm_probability = storm_stats[0]  # any_storm_prob_per_sol
        global_storm_prob = storm_stats[2]
        mean_severity = storm_stats[3]
        max_severity = storm_stats[4]

        import random
        random.seed(sol_offset * 7919 + int(ls * 100))
        dust_storm = random.random() < storm_probability
        is_global = dust_storm and random.random() < (global_storm_prob / max(storm_probability, 0.001))
        if dust_storm:
            if is_global:
                storm_severity = random.uniform(max_severity * 0.8, max_severity)
            else:
                storm_severity = random.uniform(mean_severity * 0.5, mean_severity * 1.5)
        else:
            storm_severity = 0.0

        if dust_storm:
            storms_survived += 1

        # Solar energy production
        dist_factor = solar_distance_factor(ls)
        dust_factor = 1.0 - (storm_severity * 0.7 if dust_storm else 0.0)
        peak_irr = 590 * dist_factor * dust_factor
        solar_kwh = peak_irr * 0.4 * 12 * panel_area * panel_efficiency * 0.998 / 1000

        # Thermal simulation for this sol
        thermal = simulate_sol(
            start_temp_k=temp_k,
            latitude_deg=latitude,
            solar_longitude=ls,
            r_value=r_value,
            heater_power_w=heater_power,
            dust_storm=dust_storm,
        )

        temp_k = thermal["end_temp_k"]
        heating_kwh = thermal["heating_kwh"]
        total_heating_kwh += heating_kwh

        # Energy balance
        energy_kwh += solar_kwh - heating_kwh - 7.5  # 7.5 kWh base load
        food_kg -= crew_size * 0.6
        if sol_offset % 7 == 0:
            food_kg += random.uniform(0.3, 1.2)  # harvest
        # Resupply every 30 sols (inbound supply drops — covers 30 sols of consumption)
        if sol_offset % 30 == 0:
            food_kg += crew_size * 0.6 * 30  # full resupply for 30 sols

        # Track extremes
        min_temp_k = min(min_temp_k, temp_k)
        max_temp_k = max(max_temp_k, temp_k)
        if energy_kwh < min_energy:
            min_energy = energy_kwh
            worst_sol = sol_offset

        # Check survival
        temp_c = temp_k - 273.15
        if temp_c < -40:
            alive = False
            death_sol = sol_offset
            death_reason = f"Frozen: interior reached {temp_c:.1f}°C"
        elif energy_kwh <= 0:
            alive = False
            death_sol = sol_offset
            death_reason = f"Power failure: reserves depleted at Sol -{sol_offset}"
        elif food_kg <= 0:
            alive = False
            death_sol = sol_offset
            death_reason = f"Starvation: food depleted at Sol -{sol_offset}"

        entry = {
            "sol_offset": -sol_offset,
            "ls": round(ls, 1),
            "temp_c": round(temp_c, 1),
            "energy_kwh": round(energy_kwh, 1),
            "solar_kwh": round(solar_kwh, 1),
            "heating_kwh": round(heating_kwh, 1),
            "food_kg": round(food_kg, 1),
            "dust_storm": dust_storm,
            "storm_severity": round(storm_severity, 2) if dust_storm else 0,
            "alive": alive,
        }
        timeline.append(entry)

        if verbose and (sol_offset % 50 == 0 or sol_offset <= 5 or not alive):
            storm_str = f" 🌪️ {storm_severity:.0%}" if dust_storm else ""
            status = "🟢" if temp_c > 10 else "🟡" if temp_c > 0 else "🔴"
            print(f"  Sol -{sol_offset:>4d} │ Ls {ls:>5.1f}° │ {status} {temp_c:>+6.1f}°C │ "
                  f"⚡{energy_kwh:>7.0f} kWh │ 🍔{food_kg:>5.0f} kg{storm_str}")

        if not alive:
            break

    # Summary
    survived_sols = death_sol - 1 if death_sol else num_sols
    result = {
        "survived_sols": survived_sols,
        "survived_full_year": survived_sols >= 669,
        "alive_at_end": alive,
        "death_sol": -death_sol if death_sol else None,
        "death_reason": death_reason,
        "min_temp_c": round(min_temp_k - 273.15, 1),
        "max_temp_c": round(max_temp_k - 273.15, 1),
        "min_energy_kwh": round(min_energy, 1),
        "worst_energy_sol": -worst_sol,
        "storms_survived": storms_survived,
        "total_heating_kwh": round(total_heating_kwh, 1),
        "timeline": timeline,
    }

    return result


def print_report(result: dict):
    """Print a human-readable backtest report."""
    print()
    print("=" * 66)
    print("  MARS BARN — COLONY BACKTEST REPORT")
    print("  How far back would this colony have survived?")
    print("=" * 66)

    if result["survived_full_year"]:
        print(f"\n  ✅ SURVIVED A FULL MARS YEAR ({result['survived_sols']} sols)")
        print(f"     This colony configuration can handle all seasons.")
    else:
        print(f"\n  ❌ FAILED AT SOL {result['death_sol']} ({result['survived_sols']} sols survived)")
        print(f"     Cause: {result['death_reason']}")

    print(f"\n  Temperature range: {result['min_temp_c']:+.1f}°C to {result['max_temp_c']:+.1f}°C")
    print(f"  Lowest energy: {result['min_energy_kwh']:.0f} kWh (Sol {result['worst_energy_sol']})")
    print(f"  Storms weathered: {result['storms_survived']}")
    print(f"  Total heating: {result['total_heating_kwh']:.0f} kWh")

    # Find the most dangerous period
    timeline = result["timeline"]
    if timeline:
        worst_temp = min(timeline, key=lambda t: t["temp_c"])
        worst_energy = min(timeline, key=lambda t: t["energy_kwh"])
        print(f"\n  Most dangerous moments:")
        print(f"    Coldest: {worst_temp['temp_c']:+.1f}°C at Sol {worst_temp['sol_offset']} (Ls {worst_temp['ls']}°)")
        print(f"    Lowest power: {worst_energy['energy_kwh']:.0f} kWh at Sol {worst_energy['sol_offset']} (Ls {worst_energy['ls']}°)")

        # Season analysis
        seasons = {"Spring (Ls 0-90)": [], "Summer (Ls 90-180)": [], "Autumn (Ls 180-270)": [], "Winter (Ls 270-360)": []}
        for t in timeline:
            if t["ls"] < 90: seasons["Spring (Ls 0-90)"].append(t)
            elif t["ls"] < 180: seasons["Summer (Ls 90-180)"].append(t)
            elif t["ls"] < 270: seasons["Autumn (Ls 180-270)"].append(t)
            else: seasons["Winter (Ls 270-360)"].append(t)

        print(f"\n  Season breakdown:")
        for name, entries in seasons.items():
            if entries:
                avg_temp = sum(t["temp_c"] for t in entries) / len(entries)
                storms = sum(1 for t in entries if t["dust_storm"])
                print(f"    {name}: avg {avg_temp:+.1f}°C, {storms} storms, {len(entries)} sols")

    print("=" * 66)


def main():
    parser = argparse.ArgumentParser(description="Mars Barn Colony Backtest")
    parser.add_argument("--sols", type=int, default=17400, help="Sols to simulate backwards (17400 = Viking era 1976)")
    parser.add_argument("--output", default=None, help="Save results to JSON file")
    args = parser.parse_args()

    # Load current colony state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            colony = json.load(f)
        start_ls = colony["solar_longitude"]
        start_temp = colony["habitat"]["interior_temp_k"]
        start_energy = colony["habitat"]["stored_energy_kwh"]
        latitude = colony["location"]["latitude"]
        print(f"Backtesting from current state: Sol {colony['sol']}, Ls {start_ls}°, {start_temp-273.15:+.1f}°C")
    else:
        start_ls = 37.0
        start_temp = 290.8
        start_energy = 559.9
        latitude = -4.5
        print("No colony state found, using defaults")

    print(f"Simulating {args.sols} sols backwards through Mars history...\n")

    result = backtest(
        start_ls=start_ls,
        start_temp_k=start_temp,
        stored_energy_kwh=start_energy,
        num_sols=args.sols,
        latitude=latitude,
    )

    print_report(result)

    if args.output:
        # Save without full timeline for compact output
        output = {k: v for k, v in result.items() if k != "timeline"}
        output["timeline_summary"] = {
            "total_entries": len(result["timeline"]),
            "first_5": result["timeline"][:5],
            "last_5": result["timeline"][-5:],
        }
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
