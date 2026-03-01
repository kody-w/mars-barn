#!/usr/bin/env python3
"""Mars Barn Live — real-time persistent simulation.

The colony advances 1 sol per real Earth day. Run this anytime —
it catches up to the current sol automatically.

Fork this repo to run YOUR colony with YOUR parameters.

Usage:
    python src/live.py                # advance to current sol, print status
    python src/live.py --reset        # restart from Sol 0
    python src/live.py --status       # print current state without advancing

State is saved to state/colony.json — committed to your repo.
"""
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "state" / "colony.json"

# Your colony launched when you forked the repo.
# Override with COLONY_LAUNCH_DATE env var (ISO format).
DEFAULT_LAUNCH = "2026-02-28T00:00:00Z"
EARTH_DAYS_PER_SOL = 1.02749

# Mars orbital
MARS_ECCENTRICITY = 0.0934
MARS_AXIAL_TILT = 25.19
PERIHELION_LS = 251.0


def current_sol(launch_date: str) -> int:
    launch = datetime.fromisoformat(launch_date.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    elapsed = (now - launch).total_seconds() / 86400
    return max(0, int(elapsed / EARTH_DAYS_PER_SOL))


def mars_solar_longitude() -> float:
    now = datetime.now(timezone.utc)
    months = (now.year - 2023) * 12 + now.month + now.day / 30.0
    return round((months * 19.38) % 360, 1)


def default_colony() -> dict:
    return {
        "name": os.environ.get("COLONY_NAME", "Mars Barn"),
        "launch_date": os.environ.get("COLONY_LAUNCH_DATE", DEFAULT_LAUNCH),
        "sol": 0,
        "solar_longitude": mars_solar_longitude(),
        "location": {
            "latitude": float(os.environ.get("LATITUDE", "-4.5")),
            "longitude": float(os.environ.get("LONGITUDE", "137.4")),
            "name": os.environ.get("LOCATION_NAME", "Jezero Crater"),
        },
        "habitat": {
            "interior_temp_k": 293.0,
            "stored_energy_kwh": 500.0,
            "solar_panel_area_m2": float(os.environ.get("PANEL_AREA", "400")),
            "panel_efficiency": 0.22,
            "panel_dust_factor": 1.0,
            "insulation_r_value": float(os.environ.get("R_VALUE", "12")),
            "heater_power_w": float(os.environ.get("HEATER_POWER", "8000")),
            "ground_coupling_depth_m": float(os.environ.get("GROUND_DEPTH", "0")),
            "crew_size": int(os.environ.get("CREW_SIZE", "4")),
            "water_reserves_l": 200.0,
            "food_reserves_kg": 120.0,
            "harvest_total_kg": 0.0,
        },
        "active_events": [],
        "log": [],
        "stats": {
            "sols_survived": 0,
            "total_power_kwh": 0.0,
            "total_heating_kwh": 0.0,
            "dust_devils": 0,
            "storms_survived": 0,
            "meteorites": 0,
            "min_temp_k": 293.0,
            "max_temp_k": 293.0,
            "harvests": 0,
        },
        "_meta": {
            "version": 2,
            "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated": "",
            "engine": "mars-barn-live-v2",
        },
    }


def load_colony() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return default_colony()


def save_colony(colony: dict) -> None:
    colony["_meta"]["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(colony, f, indent=2)
        f.write("\n")


def tick_sol(colony: dict, sol: int) -> dict:
    """Simulate one sol. Returns log entry."""
    random.seed(sol * 7919 + hash(colony["name"]))

    ls = (colony["solar_longitude"] + 0.524) % 360
    colony["solar_longitude"] = round(ls, 1)
    hab = colony["habitat"]
    stats = colony["stats"]
    lat = colony["location"]["latitude"]

    # === EVENTS ===
    events = []
    colony["active_events"] = [e for e in colony["active_events"] if e.get("end_sol", 0) > sol]

    if random.random() < 0.8:
        cleaning = round(random.uniform(0.02, 0.1), 3)
        hab["panel_dust_factor"] = min(1.0, hab["panel_dust_factor"] + cleaning)
        events.append("dust_devil")
        stats["dust_devils"] += 1

    if random.random() < 0.03:
        sev = round(random.uniform(0.3, 0.7), 2)
        dur = random.randint(2, 8)
        colony["active_events"].append({"type": "storm", "severity": sev, "end_sol": sol + dur})
        events.append(f"dust_storm({sev:.0%})")
        stats["storms_survived"] += 1

    if random.random() < 0.02:
        events.append("meteorite")
        stats["meteorites"] += 1

    if random.random() < 0.008:
        system = random.choice(["panel", "recycler", "heater", "seal"])
        events.append(f"warning:{system}")

    storm_active = any(e["type"] == "storm" for e in colony["active_events"])
    storm_sev = max((e.get("severity", 0) for e in colony["active_events"] if e.get("type") == "storm"), default=0)

    # === SOLAR ===
    hab["panel_dust_factor"] = max(0.5, hab["panel_dust_factor"] - 0.002)
    dist = 1.0 / ((1 - MARS_ECCENTRICITY**2) / (1 + MARS_ECCENTRICITY * math.cos(math.radians(ls - PERIHELION_LS)))) ** 2
    peak_irr = 590 * dist * (1 - storm_sev * 0.7 if storm_active else 1)
    solar_kwh = round(peak_irr * 0.4 * 12 * hab["solar_panel_area_m2"] * hab["panel_efficiency"] * hab["panel_dust_factor"] / 1000, 1)

    # === THERMAL ===
    seasonal = 15 * math.sin(math.radians(ls - 250))
    lat_effect = 40 * (1 - math.cos(math.radians(lat)))
    base_temp = 210 + seasonal - lat_effect
    diurnal_swing = 42
    avg_exterior = base_temp

    # Ground coupling reduces effective exterior temp toward ground temp
    ground_depth = hab.get("ground_coupling_depth_m", 0)
    if ground_depth > 0:
        ground_temp = 210  # stable subsurface
        blend = min(1.0, ground_depth / 3.0)
        avg_exterior = avg_exterior * (1 - blend * 0.3) + ground_temp * blend * 0.3

    delta_t = hab["interior_temp_k"] - avg_exterior
    r_val = hab["insulation_r_value"]
    surface_area = hab["solar_panel_area_m2"]  # rough proxy
    cond_loss_w = surface_area * delta_t / r_val
    heating_kwh = round(min(hab["heater_power_w"] * 20 / 1000, solar_kwh * 0.6), 1)

    net_energy = solar_kwh - heating_kwh - 7.5
    hab["stored_energy_kwh"] = round(max(0, hab["stored_energy_kwh"] + net_energy), 1)

    thermal_mass = surface_area * 5 * 1005
    net_heat_w = (heating_kwh * 1000 / 24.6) - cond_loss_w
    temp_change = (net_heat_w * 24.6 * 3600) / thermal_mass
    hab["interior_temp_k"] = round(max(150, min(310, hab["interior_temp_k"] + temp_change)), 1)

    # === FOOD/WATER ===
    hab["water_reserves_l"] = round(hab["water_reserves_l"] - 3 + 3, 1)
    hab["food_reserves_kg"] = round(hab["food_reserves_kg"] - hab["crew_size"] * 0.6, 1)
    if sol % 7 == 0 and sol > 0:
        harvest = round(random.uniform(0.3, 1.2), 2)
        hab["harvest_total_kg"] = round(hab["harvest_total_kg"] + harvest, 2)
        hab["food_reserves_kg"] = round(hab["food_reserves_kg"] + harvest, 1)
        stats["harvests"] += 1

    # === STATS ===
    colony["sol"] = sol
    stats["sols_survived"] = sol
    stats["total_power_kwh"] = round(stats["total_power_kwh"] + solar_kwh, 1)
    stats["total_heating_kwh"] = round(stats["total_heating_kwh"] + heating_kwh, 1)
    stats["min_temp_k"] = min(stats["min_temp_k"], hab["interior_temp_k"])
    stats["max_temp_k"] = max(stats["max_temp_k"], hab["interior_temp_k"])

    int_c = round(hab["interior_temp_k"] - 273.15, 1)
    ext_c = round(avg_exterior - 273.15, 1)

    entry = {
        "sol": sol, "ls": round(ls, 1),
        "int_c": int_c, "ext_c": ext_c,
        "solar_kwh": solar_kwh, "heat_kwh": heating_kwh,
        "stored_kwh": round(hab["stored_energy_kwh"], 0),
        "dust": round(hab["panel_dust_factor"], 3),
        "food_kg": round(hab["food_reserves_kg"], 1),
        "events": events, "storm": storm_active,
    }
    colony["log"].append(entry)
    if len(colony["log"]) > 100:
        colony["log"] = colony["log"][-100:]

    return entry


def print_status(colony: dict) -> None:
    hab = colony["habitat"]
    stats = colony["stats"]
    loc = colony["location"]
    int_c = round(hab["interior_temp_k"] - 273.15, 1)

    status = "🟢 HABITABLE" if int_c > 0 else "🟡 COLD" if int_c > -30 else "🔴 CRITICAL"
    storm = " 🌪️ STORM" if colony["active_events"] else ""

    print(f"""
╔═══════════════════════════════════════════════════╗
║  {colony['name']:^47s}  ║
╠═══════════════════════════════════════════════════╣
║  Sol {colony['sol']:>4d}  │  Ls {colony['solar_longitude']:>5.1f}°  │  {status}{storm:8s}  ║
║  {loc['name']:^47s}  ║
╠═══════════════════════════════════════════════════╣
║  Interior:   {int_c:>+6.1f}°C                              ║
║  Power:      {stats['total_power_kwh']:>8.0f} kWh generated (total)       ║
║  Reserves:   {hab['stored_energy_kwh']:>8.1f} kWh                         ║
║  Panels:     {hab['panel_dust_factor']*100:>6.1f}%  efficiency                  ║
║  Food:       {hab['food_reserves_kg']:>8.1f} kg  ({hab['harvest_total_kg']:.1f} kg harvested)    ║
║  Crew:       {hab['crew_size']:>4d}                                    ║
╠═══════════════════════════════════════════════════╣
║  Dust devils: {stats['dust_devils']:<4d} │ Storms: {stats['storms_survived']:<3d} │ Hits: {stats['meteorites']:<3d}  ║
║  Temp range:  {stats['min_temp_k']-273.15:>+.0f}°C to {stats['max_temp_k']-273.15:>+.0f}°C                   ║
║  Survived:    {stats['sols_survived']} sols                             ║
╚═══════════════════════════════════════════════════╝

  Fork this repo to start YOUR colony.
  Tweak parameters in state/colony.json or via env vars:
    COLONY_NAME, PANEL_AREA, R_VALUE, HEATER_POWER,
    GROUND_DEPTH, CREW_SIZE, LATITUDE, LONGITUDE
""")


def main():
    if "--reset" in sys.argv:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("Colony reset. Run again to start fresh.")
        return

    colony = load_colony()

    if "--status" in sys.argv:
        print_status(colony)
        return

    target = current_sol(colony["launch_date"])
    cur = colony["sol"]

    if cur >= target:
        print(f"Colony is current at Sol {cur}.")
        print_status(colony)
        return

    print(f"Advancing {colony['name']} from Sol {cur} to Sol {target}...")
    for sol in range(cur + 1, target + 1):
        entry = tick_sol(colony, sol)
        ev = ", ".join(entry["events"]) if entry["events"] else "quiet"
        print(f"  Sol {sol:>3d}: {entry['int_c']:>+6.1f}°C | {entry['solar_kwh']:>5.0f} kWh | {entry['stored_kwh']:>5.0f} res | {ev}")

    save_colony(colony)
    print_status(colony)


if __name__ == "__main__":
    main()
