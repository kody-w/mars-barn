"""Mars Barn — Simulation Runner

Wires all modules together into a complete Mars habitat simulation.
Runs a configurable number of sols and outputs a survival report.

Usage:
    python src/main.py                  # 30 sols, default location
    python src/main.py --sols 100       # 100 sols
    python src/main.py --seed 42        # reproducible
    python src/main.py --lat -4.5       # Jezero Crater latitude
"""
import sys
import os
import random

# Add src/ to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from terrain import generate_heightmap, elevation_stats
from atmosphere import atmosphere_profile, temperature_at_altitude
from solar import daily_energy, surface_irradiance
from thermal import thermal_step
from constants import HABITAT_TARGET_TEMP_K as TARGET_TEMP_K, MARS_SOL_HOURS, MARS_LS_PER_SOL
from events import generate_events, tick_events, aggregate_effects
from state_serial import create_state, snapshot, diff_states
from viz import render_terrain, render_dashboard, render_events
from validate import run_all_validations
from survival import check as survival_check, colony_alive
from food_production import step_food
from water_recycling import tick_water
from power_grid import step_power
from population import create_population, tick_population, population_report
from habitat import Habitat
from mars_climate import dust_storm_stats


def run_simulation(
    num_sols: int = 30,
    latitude: float = -4.5,
    longitude: float = 137.4,
    seed: int = 42,
    verbose: bool = True,
) -> dict:
    """Run the full Mars habitat simulation.

    Returns the final state and simulation report.
    """
    # Generate terrain
    if verbose:
        print("Generating Mars terrain...")
    terrain = generate_heightmap(32, 32, seed=seed)
    stats = elevation_stats(terrain)
    if verbose:
        print(f"  Terrain: {stats['size']}, [{stats['min_m']}m, {stats['max_m']}m]")
        print(render_terrain(terrain, width=48))
        print()

    # Initialize state
    state = create_state(
        sol=0, terrain=terrain,
        latitude=latitude, longitude=longitude,
    )

    # Guard against invalid sol count
    if num_sols <= 0:
        if verbose:
            print("  Warning: num_sols <= 0, nothing to simulate.")
        return {
            "state": state,
            "snapshots": [snapshot(state)],
            "event_log": [],
            "validation": {"passed": 0, "total": 0, "results": []},
            "summary": {
                "sols_survived": 0,
                "colony_alive": True,
                "cause_of_death": "nominal",
                "total_power_kwh": 0,
                "total_heating_kwh": 0,
                "events_survived": 0,
                "final_temp_c": round(state["habitat"]["interior_temp_k"] - 273.15, 1),
                "stored_energy_kwh": round(state["habitat"]["stored_energy_kwh"], 1),
                "validation_passed": 0,
                "validation_total": 0,
            },
        }

    # Typed habitat interface
    hab = Habitat(state)

    # Subsystem tracking
    sols_since_water_maintenance = 0
    water_reservoir_l = state.get("resources", {}).get("h2o_liters", 200.0)

    # Population dynamics
    rng = random.Random(seed)
    pop = create_population(crew=state["habitat"]["crew_size"])

    # Simulation history
    snapshots = [snapshot(state)]
    event_log = []

    if verbose:
        print(f"Simulating {num_sols} sols at lat {latitude}°, lon {longitude}°...")
        print()

    for sol in range(1, num_sols + 1):
        # Solar longitude advances ~0.5° per sol
        state["solar_longitude"] = (state["solar_longitude"] + MARS_LS_PER_SOL) % 360

        # Seasonal dust probability from real NASA data (mars_climate.py)
        ls_current = state["solar_longitude"]
        any_prob, _reg, _glob, mean_sev, _max_sev = dust_storm_stats(ls_current)

        # Generate and manage events
        new_events = generate_events(sol, seed=seed, active_events=state["active_events"])
        state["active_events"].extend(new_events)
        state["active_events"] = tick_events(state["active_events"], sol)
        effects = aggregate_effects(state["active_events"])

        if new_events and verbose:
            for e in new_events:
                print(f"  Sol {sol:>3d}: ⚡ {e['description']}")

        # Simulate 24.6 hours in 1-hour steps
        hours_per_sol = MARS_SOL_HOURS
        step_hours = 0.25  # 15-min steps for thermal accuracy
        sol_heating_kwh = 0.0
        sol_power_kwh = 0.0

        num_steps = int(hours_per_sol / step_hours)
        for step_idx in range(num_steps):
            hour = step_idx * step_hours
            state["hour"] = hour

            # Exterior conditions
            dust_storm = any(e["type"].startswith("dust_storm") for e in state["active_events"])
            ext_temp = temperature_at_altitude(0, latitude, state["solar_longitude"], hour, dust_storm)
            irr = surface_irradiance(
                latitude, state["solar_longitude"], hour,
                dust_storm=dust_storm,
            )
            # Apply event-driven solar multiplier (e.g., dust storms)
            irr *= effects.get("solar_multiplier", 1.0)

            # Solar power generation
            panel_area = state["habitat"]["solar_panel_area_m2"]
            panel_eff = state["habitat"]["solar_panel_efficiency"]
            power_w = irr * panel_area * panel_eff
            state["habitat"]["power_kw"] = round(power_w / 1000, 2)
            sol_power_kwh += power_w * step_hours / 1000

            # Heating decision: proportional control — modulate based on temp deficit
            heater_power = state["habitat"].get("heater_power_w", 8000.0)
            temp_deficit = TARGET_TEMP_K - state["habitat"]["interior_temp_k"]
            heater_fraction = max(0.0, min(1.0, temp_deficit / 5.0))  # linear ramp over 5K range
            heater_w = heater_power * heater_fraction

            # Thermal step
            result = thermal_step(
                state["habitat"]["interior_temp_k"],
                ext_temp, irr, heater_w,
                r_value=state["habitat"].get("insulation_r_value", 12.0),
                dt_seconds=step_hours * 3600,
            )

            state["habitat"]["interior_temp_k"] = result["interior_temp_k"]
            if heater_w > 0:
                sol_heating_kwh += heater_w * step_hours / 1000

        # Update energy storage
        net_energy = sol_power_kwh - sol_heating_kwh
        state["habitat"]["stored_energy_kwh"] = max(0, state["habitat"]["stored_energy_kwh"] + net_energy)

        # Power grid — allocate solar + battery to subsystems
        dust_storm = any(e["type"].startswith("dust_storm") for e in state["active_events"])
        power_result = step_power(
            solar_energy_kwh=sol_power_kwh,
            battery_kwh=state["habitat"]["stored_energy_kwh"],
            panel_degradation_sols=sol,
            dust_storm=dust_storm,
        )
        state["habitat"]["stored_energy_kwh"] = power_result["battery_kwh"]
        state["power"] = power_result
        if verbose and power_result["grid_status"] != "nominal" and sol % 10 == 0:
            print(f"  Sol {sol:>3d}: ⚡ Grid {power_result['grid_status']}, "
                  f"battery {power_result['battery_kwh']:.0f} kWh")

        # Food production — greenhouse output depends on solar, water, and maturity
        food_result = step_food(
            population=state["habitat"]["crew_size"],
            water_available=water_reservoir_l,
            solar_energy_kwh=sol_power_kwh,
            sol=sol,
        )
        # Feed production back into resource tracking
        if "resources" in state:
            state["resources"]["food_kcal"] += food_result["food_produced_kcal"]
        # Track food metrics
        state["metrics"]["total_food_produced_kcal"] = (
            state["metrics"].get("total_food_produced_kcal", 0.0)
            + food_result["food_produced_kcal"]
        )

        # Water recycling — recovery, ISRU, reservoir tracking
        crew = state["habitat"]["crew_size"]
        water_result = tick_water(
            reservoir_l=water_reservoir_l,
            crew_size=crew,
            sols_since_maintenance=sols_since_water_maintenance,
        )
        water_reservoir_l = water_result["reservoir_l"] - food_result["water_consumed_l"]
        water_reservoir_l = max(0.0, water_reservoir_l)
        if "resources" in state:
            state["resources"]["h2o_liters"] = water_reservoir_l
        state["water"] = water_result
        sols_since_water_maintenance += 1
        if sols_since_water_maintenance >= 30:
            sols_since_water_maintenance = 0

        # Population dynamics — morale, attrition, arrivals
        # Grace period: skip attrition during crop maturity (first 60 sols)
        # to avoid false starvation deaths before the greenhouse can produce
        resources = state.get("resources", {})
        if sol <= 60:
            grace_resources = dict(resources)
            grace_resources["food_kcal"] = max(resources.get("food_kcal", 0), 50000.0)
            pop_changes = tick_population(
                pop, grace_resources, sol,
                events=new_events,
                rng_roll=rng.random(),
            )
        else:
            pop_changes = tick_population(
                pop, resources, sol,
                events=new_events,
                rng_roll=rng.random(),
            )
        state["habitat"]["crew_size"] = pop["crew"]
        state["population"] = {
            "crew": pop["crew"],
            "morale": round(pop["morale"], 3),
            "total_deaths": pop["total_deaths"],
            "total_arrivals": pop["total_arrivals"],
        }

        if verbose and pop_changes["deaths"] > 0:
            print(f"  Sol {sol:>3d}: ☠️  Crew lost — {pop_changes['cause']}"
                  f" (morale {pop['morale']:.0%}, crew {pop['crew']})")
        if verbose and pop_changes["arrivals"] > 0:
            print(f"  Sol {sol:>3d}: 🚀 {pop_changes['arrivals']} new crew arrived"
                  f" (crew {pop['crew']})")

        if verbose and sol % 10 == 0:
            stage = food_result["growth_stage"]
            fed = food_result["fed_population"]
            print(f"  Sol {sol:>3d}: 🌱 Growth {stage:.0%}, feeding {fed}/{crew}, "
                  f"💧 {water_reservoir_l:.0f}L")

        state["sol"] = sol
        state["metrics"]["sols_survived"] = sol
        state["metrics"]["total_power_generated_kwh"] += sol_power_kwh
        state["metrics"]["total_heat_lost_kwh"] += sol_heating_kwh
        state["metrics"]["events_survived"] += len(new_events)

        # Survival check — resource consumption, production, cascade detection
        state = survival_check(state)
        if not colony_alive(state):
            cascade = state.get("resources", {}).get("cascade_state", "unknown")
            if verbose:
                print(f"  Sol {sol:>3d}: ☠️  Colony died — {cascade}")
            break

        # Snapshot every 5 sols
        if sol % 5 == 0:
            snapshots.append(snapshot(state))

        # Log event activity
        if new_events:
            event_log.extend(new_events)

        # Print progress
        if verbose and sol % 10 == 0:
            print(f"  Sol {sol:>3d}: {hab.status_line()}, "
                  f"{len(state['active_events'])} active events")

    # Final report
    if verbose:
        print()
        print(render_dashboard(state))

    # Run validation
    atm_profile = atmosphere_profile(50000, 10)
    solar = daily_energy(latitude_deg=latitude, solar_longitude=state["solar_longitude"])
    validation = run_all_validations(
        terrain_grid=terrain,
        atm_profile=atm_profile,
        solar_energy=solar,
    )

    if verbose:
        if validation["passed"] == validation["total"]:
            print(f"  Validation:      {validation['passed']}/{validation['total']} ✓ all checks passed")
        else:
            print(f"  Validation:      {validation['passed']}/{validation['total']} checks passed")
            for r in validation["results"]:
                if not r["passed"]:
                    print(f"    ❌ {r['check']}: {r['detail']}")

    return {
        "state": state,
        "snapshots": snapshots,
        "event_log": event_log,
        "validation": validation,
        "summary": {
            "sols_survived": state["metrics"]["sols_survived"],
            "colony_alive": colony_alive(state),
            "cause_of_death": state.get("resources", {}).get("cascade_state", "nominal"),
            "total_power_kwh": round(state["metrics"]["total_power_generated_kwh"], 1),
            "total_heating_kwh": round(state["metrics"]["total_heat_lost_kwh"], 1),
            "events_survived": state["metrics"]["events_survived"],
            "final_temp_c": round(state["habitat"]["interior_temp_k"] - 273.15, 1),
            "stored_energy_kwh": round(state["habitat"]["stored_energy_kwh"], 1),
            "final_crew": pop["crew"],
            "total_deaths": pop["total_deaths"],
            "final_morale": round(pop["morale"], 3),
            "validation_passed": validation["passed"],
            "validation_total": validation["total"],
        },
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mars Barn Habitat Simulation")
    parser.add_argument("--sols", type=int, default=30, help="Number of sols to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--lat", type=float, default=-4.5, help="Latitude (degrees)")
    parser.add_argument("--lon", type=float, default=137.4, help="Longitude (degrees)")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()

    result = run_simulation(
        num_sols=args.sols, latitude=args.lat, longitude=args.lon,
        seed=args.seed, verbose=not args.quiet,
    )

    s = result["summary"]
    alive = "SURVIVED" if s.get("colony_alive", True) else f"DIED ({s.get('cause_of_death', '?')})"
    print(f"\n{'='*50}")
    print(f"  SIMULATION COMPLETE — {s['sols_survived']} sols — {alive}")
    print(f"  Power generated:    {s['total_power_kwh']:>6.0f} kWh")
    print(f"  Heating used:       {s['total_heating_kwh']:>6.0f} kWh")
    print(f"  Final temp:         {s['final_temp_c']:>+6.1f} °C")
    print(f"  Energy reserves:    {s['stored_energy_kwh']:>6.0f} kWh")
    print(f"  Events survived:    {s['events_survived']:>6d}")
    print(f"  Final crew:         {s['final_crew']:>6d}")
    print(f"  Total deaths:       {s['total_deaths']:>6d}")
    print(f"  Final morale:       {s['final_morale']:>5.0%}")
    print(f"  Validation:         {s['validation_passed']}/{s['validation_total']} ✓")
    print(f"{'='*50}")
