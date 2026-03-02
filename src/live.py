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
            "food_reserves_kg": 13360.0,
            "fresh_greens_kg": 0.0,
            "harvest_total_kg": 0.0,
        },
        "crew": {
            "morale": 0.8,
            "health": 1.0,
            "evas": 0,
            "discoveries": 0,
        },
        "greenhouse": {
            "planted_area_m2": 20.0,
            "growth_stage": 0.0,
            "co2_ppm": 400,
            "water_daily_l": 5.0,
        },
        "resupply": {
            "shuttles": [
                {
                    "id": "shuttle-alpha",
                    "launched_sol": -100,
                    "eta_sol": 100,
                    "manifest": {
                        "protein_powder_kg": 500,
                        "dehydrated_greens_kg": 100,
                        "vitamin_packs": 1000,
                        "water_l": 200,
                        "spare_panels_m2": 20,
                        "seeds_kg": 5,
                        "medical_supplies_kg": 15,
                    },
                    "status": "in_transit",
                },
            ],
            "next_launch_sol": 300,
            "launch_cadence_sols": 300,
            "total_deliveries": 0,
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
            "crew_illnesses": 0,
            "evas_completed": 0,
            "discoveries": 0,
            "resupply_deliveries": 0,
            "resupply_kg_received": 0,
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

    # === ADAPTIVE COUNTERMEASURES ===
    # The crew doesn't just accept problems — they improvise.
    adaptations = colony.get("adaptations", {})

    # Low energy? Crew rations power and runs non-essential systems at 50%
    if hab["stored_energy_kwh"] < 100:
        adaptations["power_rationing"] = True
        events.append("adapt:power_rationing")
    elif adaptations.get("power_rationing") and hab["stored_energy_kwh"] > 300:
        adaptations["power_rationing"] = False
        events.append("adapt:power_rationing_lifted")

    # Panel damage from meteorite? EVA repair crew patches it
    if "meteorite" in events and hab["panel_dust_factor"] > 0.6:
        repair = round(random.uniform(0.02, 0.08), 3)
        hab["panel_dust_factor"] = min(1.0, hab["panel_dust_factor"] + repair)
        events.append(f"adapt:panel_repair(+{repair:.1%})")

    # Storm incoming with low reserves? Pre-heat the habitat and stash energy
    if storm_active and hab["stored_energy_kwh"] > 200:
        adaptations["storm_protocol"] = True
    elif not storm_active and adaptations.get("storm_protocol"):
        adaptations["storm_protocol"] = False

    # Heater warning? Crew reroutes power from secondary circuits
    if "warning:heater" in events and hab["stored_energy_kwh"] > 50:
        hab["stored_energy_kwh"] = round(hab["stored_energy_kwh"] - 10, 1)  # costs 10 kWh to jury-rig
        events.append("adapt:heater_bypass")

    # Seal breach? Crew patches with emergency sealant (always on hand)
    if "warning:seal" in events:
        events.append("adapt:seal_patched")

    # Recycler down? Switch to backup water reserves, reduce consumption
    if "warning:recycler" in events:
        hab["water_reserves_l"] = round(max(0, hab["water_reserves_l"] - 5), 1)
        events.append("adapt:backup_water(-5L)")

    # If temp drops dangerously, crew huddles in inner module (reduces heat loss area)
    if hab["interior_temp_k"] < 253:  # below -20°C
        adaptations["huddle_protocol"] = True
        # Metabolic clustering helps
        events.append("adapt:huddle_protocol")
    elif hab["interior_temp_k"] > 273 and adaptations.get("huddle_protocol"):
        adaptations["huddle_protocol"] = False

    colony["adaptations"] = adaptations

    # === SOLAR ===
    hab["panel_dust_factor"] = max(0.5, hab["panel_dust_factor"] - 0.002)
    dist = 1.0 / ((1 - MARS_ECCENTRICITY**2) / (1 + MARS_ECCENTRICITY * math.cos(math.radians(ls - PERIHELION_LS)))) ** 2
    peak_irr = 590 * dist * (1 - storm_sev * 0.7 if storm_active else 1)
    solar_kwh = round(peak_irr * 0.4 * 12 * hab["solar_panel_area_m2"] * hab["panel_efficiency"] * hab["panel_dust_factor"] / 1000, 1)

    # === THERMAL (uses the real thermal model for accuracy) ===
    from thermal import simulate_sol
    from atmosphere import temperature_at_altitude
    avg_exterior = temperature_at_altitude(0, lat, ls, hour=12.0, dust_storm=storm_active)
    thermal_result = simulate_sol(
        start_temp_k=hab["interior_temp_k"],
        latitude_deg=lat,
        solar_longitude=ls,
        r_value=hab["insulation_r_value"],
        heater_power_w=hab["heater_power_w"],
        dust_storm=storm_active,
    )
    hab["interior_temp_k"] = thermal_result["end_temp_k"]
    heating_kwh = round(thermal_result["heating_kwh"], 1)

    net_energy = solar_kwh - heating_kwh - 7.5
    hab["stored_energy_kwh"] = round(max(0, hab["stored_energy_kwh"] + net_energy), 1)

    # === GREENHOUSE (fresh greens — garnish, morale booster) ===
    gh = colony.get("greenhouse", {"planted_area_m2": 20, "growth_stage": 0, "co2_ppm": 400, "water_daily_l": 5})
    light_factor = min(1.0, solar_kwh / 150)
    water_factor = min(1.0, hab["water_reserves_l"] / (gh["water_daily_l"] * 10))
    co2_factor = min(1.0, gh["co2_ppm"] / 800)
    growth_rate = 0.08 * light_factor * water_factor * co2_factor * gh["planted_area_m2"] / 20
    gh["growth_stage"] = min(1.0, gh["growth_stage"] + growth_rate)
    hab["water_reserves_l"] = round(hab["water_reserves_l"] - gh["water_daily_l"] + gh["water_daily_l"] * 0.92, 1)

    harvest_kg = 0.0
    if gh["growth_stage"] >= 1.0:
        harvest_kg = round(gh["planted_area_m2"] * random.uniform(0.15, 0.3), 2)
        gh["growth_stage"] = 0.0
        stats["harvests"] += 1
        events.append(f"harvest({harvest_kg:.1f}kg)")

    hab["harvest_total_kg"] = round(hab["harvest_total_kg"] + harvest_kg, 2)
    hab["fresh_greens_kg"] = round(hab.get("fresh_greens_kg", 0) + harvest_kg, 1)
    colony["greenhouse"] = gh

    # === AUTONOMOUS RESUPPLY SHUTTLES ===
    resupply = colony.get("resupply", {"shuttles": [], "next_launch_sol": 260, "launch_cadence_sols": 260, "total_deliveries": 0})

    # Check for shuttle arrivals
    for shuttle in resupply.get("shuttles", []):
        if shuttle["status"] == "in_transit" and sol >= shuttle["eta_sol"]:
            # Shuttle has arrived! Unload manifest
            manifest = shuttle.get("manifest", {})
            food_delivered = manifest.get("protein_powder_kg", 0) + manifest.get("dehydrated_greens_kg", 0)
            hab["food_reserves_kg"] = round(hab["food_reserves_kg"] + food_delivered, 1)
            hab["water_reserves_l"] = round(hab["water_reserves_l"] + manifest.get("water_l", 0), 1)
            if manifest.get("spare_panels_m2", 0) > 0:
                hab["solar_panel_area_m2"] = round(hab["solar_panel_area_m2"] + manifest["spare_panels_m2"], 1)
            shuttle["status"] = "delivered"
            resupply["total_deliveries"] = resupply.get("total_deliveries", 0) + 1
            stats["resupply_deliveries"] = stats.get("resupply_deliveries", 0) + 1
            stats["resupply_kg_received"] = stats.get("resupply_kg_received", 0) + food_delivered
            events.append(f"resupply({food_delivered:.0f}kg)")

    # Auto-launch new shuttle at cadence
    if sol >= resupply.get("next_launch_sol", 260):
        transfer_time = random.randint(240, 280)  # Hohmann variance
        new_shuttle = {
            "id": f"shuttle-{resupply.get('total_deliveries', 0) + len([s for s in resupply.get('shuttles', []) if s['status'] == 'in_transit']) + 1}",
            "launched_sol": sol,
            "eta_sol": sol + transfer_time,
            "manifest": {
                "protein_powder_kg": 180 + random.randint(0, 40),
                "dehydrated_greens_kg": 30 + random.randint(0, 20),
                "vitamin_packs": 400 + random.randint(0, 200),
                "water_l": 80 + random.randint(0, 40),
                "spare_panels_m2": random.choice([0, 0, 10, 20]),
            },
            "status": "in_transit",
        }
        resupply["shuttles"].append(new_shuttle)
        resupply["next_launch_sol"] = sol + resupply.get("launch_cadence_sols", 260)
        events.append(f"shuttle_launched(eta:sol{new_shuttle['eta_sol']})")

    # Prune delivered shuttles older than 10 sols
    resupply["shuttles"] = [s for s in resupply.get("shuttles", [])
                            if s["status"] == "in_transit" or sol - s.get("eta_sol", 0) < 10]
    colony["resupply"] = resupply

    # === FOOD/WATER ===
    # Crew eats: 0.5 kg/day from dehydrated stores (protein powder + vitamins)
    #            0.1 kg/day fresh greens from greenhouse (if available)
    crew_size = hab["crew_size"]
    stores_consumed = crew_size * 0.5
    greens_desired = crew_size * 0.1
    greens_consumed = min(greens_desired, hab.get("fresh_greens_kg", 0))
    hab["food_reserves_kg"] = round(max(0, hab["food_reserves_kg"] - stores_consumed), 1)
    hab["fresh_greens_kg"] = round(max(0, hab.get("fresh_greens_kg", 0) - greens_consumed), 1)
    has_fresh_greens = greens_consumed >= greens_desired * 0.5

    # === CREW EVENTS & MORALE ===
    crew = colony.get("crew", {"morale": 0.8, "health": 1.0, "evas": 0, "discoveries": 0})

    # Morale drift — wider comfort band, gentler penalties
    int_c = hab["interior_temp_k"] - 273.15
    if int_c > 15 and hab["food_reserves_kg"] > 30:
        crew["morale"] = min(1.0, crew["morale"] + 0.02)
    elif int_c > 0 and hab["food_reserves_kg"] > 10:
        crew["morale"] = min(1.0, crew["morale"] + 0.005)
    elif int_c < -30 or hab["food_reserves_kg"] <= 0:
        crew["morale"] = max(0.0, crew["morale"] - 0.04)
    elif int_c < 0 or hab["food_reserves_kg"] < 15:
        crew["morale"] = max(0.0, crew["morale"] - 0.01)

    # Fresh greens are a morale multiplier — garnish makes protein powder bearable
    if has_fresh_greens:
        crew["morale"] = min(1.0, crew["morale"] + 0.01)

    if storm_active:
        crew["morale"] = max(0.0, crew["morale"] - 0.03)

    # Illness (higher chance at low morale/health)
    illness_chance = 0.02 + (1 - crew["health"]) * 0.05
    if random.random() < illness_chance:
        crew["health"] = max(0.3, crew["health"] - random.uniform(0.05, 0.15))
        stats["crew_illnesses"] = stats.get("crew_illnesses", 0) + 1
        events.append("crew:illness")
    else:
        crew["health"] = min(1.0, crew["health"] + 0.005)

    # EVA (only when morale > 0.5 and no storm)
    if not storm_active and crew["morale"] > 0.5 and random.random() < 0.15:
        crew["evas"] += 1
        stats["evas_completed"] = stats.get("evas_completed", 0) + 1
        events.append("eva")
        # EVAs can yield discoveries
        if random.random() < 0.25:
            crew["discoveries"] += 1
            crew["morale"] = min(1.0, crew["morale"] + 0.05)
            stats["discoveries"] = stats.get("discoveries", 0) + 1
            disc = random.choice(["mineral_deposit", "ice_lens", "lava_tube", "fossil_candidate", "regolith_anomaly"])
            events.append(f"discovery:{disc}")

    colony["crew"] = crew

    # === SURVIVAL RESILIENCE ===
    # The colony doesn't just die — it fights. Death only comes from
    # sustained, unrecoverable cascading failure.
    critical_sols = colony.get("_critical_sols", 0)
    starving_sols = colony.get("_starving_sols", 0)

    if hab["interior_temp_k"] < 223:  # below -50°C
        critical_sols += 1
        # Crew burns furniture, runs every heater at max, huddles
        if hab["stored_energy_kwh"] > 20:
            hab["stored_energy_kwh"] = round(hab["stored_energy_kwh"] - 20, 1)
            hab["interior_temp_k"] = min(253, hab["interior_temp_k"] + 5)
            events.append("adapt:emergency_heating")
            critical_sols = max(0, critical_sols - 1)
    else:
        critical_sols = 0

    if hab["food_reserves_kg"] <= 0:
        starving_sols += 1
        # Crew switches to half-rations from greenhouse greens
        greens_avail = hab.get("fresh_greens_kg", 0)
        if greens_avail > 0.5:
            hab["fresh_greens_kg"] = round(greens_avail - 0.5, 1)
            starving_sols = max(0, starving_sols - 1)
            events.append("adapt:greens_as_emergency_rations")
    else:
        starving_sols = 0

    if hab["stored_energy_kwh"] <= 0:
        # Crew shuts down all non-essential systems, wraps in thermal blankets
        events.append("adapt:full_shutdown_protocol")
        hab["interior_temp_k"] = max(hab["interior_temp_k"] - 2, 200)  # slow cooling

    colony["_critical_sols"] = critical_sols
    colony["_starving_sols"] = starving_sols

    # Only truly dead after 5+ sols of sustained unrecoverable failure
    if starving_sols >= 5 and hab.get("fresh_greens_kg", 0) <= 0:
        events.append("COLONY_DEAD:starvation")
    elif critical_sols >= 5 and hab["stored_energy_kwh"] <= 0:
        events.append("COLONY_DEAD:hypothermia")
    elif hab["stored_energy_kwh"] <= 0 and hab["interior_temp_k"] < 200:
        events.append("COLONY_DEAD:total_systems_failure")

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
        "morale": round(crew["morale"], 2),
        "health": round(crew["health"], 2),
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
    crew = colony.get("crew", {"morale": 0.8, "health": 1.0, "evas": 0, "discoveries": 0})
    gh = colony.get("greenhouse", {"growth_stage": 0})
    resupply = colony.get("resupply", {"shuttles": [], "total_deliveries": 0})
    int_c = round(hab["interior_temp_k"] - 273.15, 1)

    status = "🟢 HABITABLE" if int_c > 0 else "🟡 COLD" if int_c > -30 else "🔴 CRITICAL"
    storm = " 🌪️ STORM" if colony["active_events"] else ""
    morale_icon = "😊" if crew["morale"] > 0.6 else "😐" if crew["morale"] > 0.3 else "😰"

    # Next shuttle info
    in_transit = [s for s in resupply.get("shuttles", []) if s["status"] == "in_transit"]
    shuttle_str = f"ETA Sol {in_transit[0]['eta_sol']}" if in_transit else "none en route"

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
║  Food:       {hab['food_reserves_kg']:>8.1f} kg  (stores)                  ║
║  Greens:     {hab.get('fresh_greens_kg',0):>8.1f} kg  (fresh)                   ║
║  Greenhouse: {gh['growth_stage']*100:>5.1f}%  growth                       ║
║  Crew:       {hab['crew_size']:>4d}  {morale_icon} morale {crew['morale']:.0%}  ❤ {crew['health']:.0%}     ║
║  🚀 Shuttle: {shuttle_str:<34s}  ║
╠═══════════════════════════════════════════════════╣
║  Dust devils: {stats['dust_devils']:<4d} │ Storms: {stats['storms_survived']:<3d} │ Hits: {stats['meteorites']:<3d}  ║
║  EVAs: {stats.get('evas_completed',0):<3d} │ Discoveries: {stats.get('discoveries',0):<3d} │ 🤒 {stats.get('crew_illnesses',0):<3d}   ║
║  Resupply: {stats.get('resupply_deliveries',0)} deliveries ({stats.get('resupply_kg_received',0):.0f} kg total)     ║
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
