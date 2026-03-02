"""Mars Barn — Multi-Planet Climate Statistics

Climate data for all rocky/habitable-zone bodies in the solar system.
Each planet has measured/estimated statistics enabling backtest simulations.
Data from NASA Planetary Fact Sheets, mission measurements, and GCMs.

Usage:
    from planetary_climate import get_planet_climate, backtest_planet
"""

import math
import random

# ── Planet Climate Profiles ─────────────────────────────────────────────
# Each profile has: surface_temp_K (mean, min, max), pressure_Pa,
# gravity_m_s2, solar_constant_Wm2, day_length_hours,
# atmosphere_density, dust_storm_probability, and seasonal variation.

PLANETS = {
    "mercury": {
        "name": "Mercury",
        "surface_temp_k": {"mean": 440, "min": 100, "max": 700},
        "diurnal_swing_k": 300,  # extreme: 100K night, 700K day
        "pressure_pa": 0,  # no atmosphere
        "gravity_m_s2": 3.7,
        "solar_constant_wm2": 9083,  # 1361 / 0.387²
        "day_hours": 4222.6,  # 176 Earth days
        "atmosphere": "none",
        "dust_storm_prob": 0.0,
        "challenges": ["extreme thermal cycling", "no atmosphere", "solar radiation"],
        "habitat_penalty": 3.0,  # multiplier on heating/cooling requirements
    },
    "venus": {
        "name": "Venus",
        "surface_temp_k": {"mean": 737, "min": 720, "max": 750},
        "diurnal_swing_k": 5,  # almost none due to thick atmosphere
        "pressure_pa": 9200000,  # 92 atm
        "gravity_m_s2": 8.87,
        "solar_constant_wm2": 2601,  # 1361 / 0.723²
        "day_hours": 2802,  # 116.75 Earth days (retrograde)
        "atmosphere": "CO2 96.5%, N2 3.5%",
        "dust_storm_prob": 0.0,  # no dust, but sulfuric acid clouds
        "challenges": ["crushing pressure", "extreme heat", "sulfuric acid"],
        "habitat_penalty": 5.0,
    },
    "moon": {
        "name": "Moon",
        "surface_temp_k": {"mean": 250, "min": 100, "max": 400},
        "diurnal_swing_k": 150,
        "pressure_pa": 0,
        "gravity_m_s2": 1.62,
        "solar_constant_wm2": 1361,  # same as Earth distance
        "day_hours": 708.7,  # 29.5 Earth days
        "atmosphere": "none",
        "dust_storm_prob": 0.0,
        "challenges": ["no atmosphere", "micrometeorites", "14-day nights", "regolith dust"],
        "habitat_penalty": 2.0,
    },
    "mars": {
        "name": "Mars",
        "surface_temp_k": {"mean": 210, "min": 130, "max": 300},
        "diurnal_swing_k": 80,
        "pressure_pa": 636,
        "gravity_m_s2": 3.721,
        "solar_constant_wm2": 586,
        "day_hours": 24.66,
        "atmosphere": "CO2 95.3%, N2 2.7%, Ar 1.6%",
        "dust_storm_prob": 0.096,  # from our MDAD data
        "challenges": ["thin atmosphere", "dust storms", "cold", "radiation"],
        "habitat_penalty": 1.0,  # baseline
    },
    "europa": {
        "name": "Europa (Jupiter moon)",
        "surface_temp_k": {"mean": 102, "min": 86, "max": 132},
        "diurnal_swing_k": 20,
        "pressure_pa": 0.1,  # trace O2 atmosphere
        "gravity_m_s2": 1.315,
        "solar_constant_wm2": 50.5,  # 1361 / 5.2²
        "day_hours": 85.2,  # tidally locked to Jupiter
        "atmosphere": "trace O2",
        "dust_storm_prob": 0.0,
        "challenges": ["extreme cold", "radiation belts", "ice surface", "no solar"],
        "habitat_penalty": 4.0,
    },
    "titan": {
        "name": "Titan (Saturn moon)",
        "surface_temp_k": {"mean": 94, "min": 90, "max": 98},
        "diurnal_swing_k": 3,  # thick atmosphere buffers
        "pressure_pa": 146700,  # 1.45 atm (thicker than Earth!)
        "gravity_m_s2": 1.352,
        "solar_constant_wm2": 15.0,  # 1361 / 9.54²
        "day_hours": 382.7,  # 15.9 Earth days
        "atmosphere": "N2 98.4%, CH4 1.4%",
        "dust_storm_prob": 0.01,  # methane weather
        "challenges": ["extreme cold", "methane lakes", "almost no solar", "hydrocarbon rain"],
        "habitat_penalty": 4.5,
    },
    "jupiter_cloud": {
        "name": "Jupiter (cloud station at 1 bar)",
        "surface_temp_k": {"mean": 165, "min": 110, "max": 200},
        "diurnal_swing_k": 10,
        "pressure_pa": 100000,  # floating at 1 bar level
        "gravity_m_s2": 24.79,
        "solar_constant_wm2": 50.5,
        "day_hours": 9.93,  # fastest rotation
        "atmosphere": "H2 89.8%, He 10.2%",
        "dust_storm_prob": 0.3,  # constant storms
        "challenges": ["extreme gravity", "radiation", "no surface", "wind shear"],
        "habitat_penalty": 6.0,
    },
    "saturn_ring_lab": {
        "name": "Saturn (ring laboratory)",
        "surface_temp_k": {"mean": 134, "min": 82, "max": 160},
        "diurnal_swing_k": 15,
        "pressure_pa": 0,  # in orbit among rings
        "gravity_m_s2": 0.0,  # microgravity
        "solar_constant_wm2": 14.9,  # 1361 / 9.58²
        "day_hours": 10.66,
        "atmosphere": "none (orbital)",
        "dust_storm_prob": 0.05,  # ring particle impacts
        "challenges": ["microgravity", "ring debris", "cold", "no solar for heating"],
        "habitat_penalty": 5.0,
    },
}


def get_planet_climate(planet_id: str) -> dict:
    """Get climate profile for a planet."""
    return PLANETS.get(planet_id, PLANETS["mars"])


def simulate_planet_sol(
    planet_id: str,
    interior_temp_k: float,
    stored_energy_kwh: float,
    sol: int,
    panel_area_m2: float = 400,
    heater_power_w: float = 8000,
    r_value: float = 12.0,
) -> dict:
    """Simulate one sol on any planet using its climate profile."""
    p = PLANETS.get(planet_id, PLANETS["mars"])
    random.seed(sol * 7919 + hash(planet_id))

    # Exterior temperature with diurnal variation
    base_temp = p["surface_temp_k"]["mean"]
    seasonal_mod = p["diurnal_swing_k"] * 0.3 * math.sin(sol * 0.01)  # slow seasonal drift
    ext_temp = base_temp + seasonal_mod + random.gauss(0, p["diurnal_swing_k"] * 0.1)

    # Solar energy (adjusted for distance and day length)
    solar_fraction = min(1.0, p["day_hours"] / 24.66)  # Mars-normalized
    effective_solar = p["solar_constant_wm2"] * solar_fraction
    dust_event = random.random() < p["dust_storm_prob"]
    if dust_event:
        effective_solar *= random.uniform(0.2, 0.6)

    solar_kwh = effective_solar * 0.4 * 12 * panel_area_m2 * 0.22 * 0.998 / 1000

    # Thermal: simplified model scaled by habitat_penalty
    penalty = p["habitat_penalty"]
    delta_t = interior_temp_k - ext_temp
    surface_area = 200  # standard habitat

    # Heat losses (scaled by penalty for harder environments)
    cond_loss_w = surface_area * abs(delta_t) / r_value * penalty
    rad_loss_w = 0.05 * 5.67e-8 * surface_area * abs(interior_temp_k**4 - ext_temp**4) * 0.1
    metabolic_w = 4 * 120  # crew heat

    # Heating demand
    total_loss = cond_loss_w + rad_loss_w - metabolic_w
    if interior_temp_k < 293.0 and total_loss > 0:
        heating_w = min(heater_power_w, total_loss * 1.2)
    elif interior_temp_k > 293.0 and ext_temp > 293.0:
        heating_w = -min(heater_power_w, (interior_temp_k - 293.0) * 100)  # cooling
    else:
        heating_w = 0

    heating_kwh = abs(heating_w) * 24.66 / 1000

    # Energy balance
    net_energy = solar_kwh - heating_kwh - 7.5
    new_energy = max(0, stored_energy_kwh + net_energy)

    # Temperature update
    thermal_mass = 150 * 1.2 * 1005 * 20
    net_heat = heating_w - cond_loss_w - rad_loss_w + metabolic_w
    dt = (net_heat * 24.66 * 3600) / thermal_mass
    new_temp = max(100, min(400, interior_temp_k + dt * 0.1))  # damped for stability

    temp_c = new_temp - 273.15
    alive = -60 < temp_c < 80 and new_energy > 0

    return {
        "sol": sol,
        "planet": planet_id,
        "interior_temp_c": round(temp_c, 1),
        "exterior_temp_c": round(ext_temp - 273.15, 1),
        "solar_kwh": round(solar_kwh, 1),
        "heating_kwh": round(heating_kwh, 1),
        "energy_kwh": round(new_energy, 1),
        "dust_event": dust_event,
        "alive": alive,
        "interior_temp_k": round(new_temp, 2),
        "stored_energy_kwh": round(new_energy, 1),
    }


def backtest_planet(planet_id: str, num_sols: int = 669) -> dict:
    """Run a full backtest for any planet."""
    p = PLANETS.get(planet_id, PLANETS["mars"])
    temp_k = 293.0
    energy = 500.0
    timeline = []
    alive = True
    storms = 0

    for sol in range(1, num_sols + 1):
        result = simulate_planet_sol(planet_id, temp_k, energy, sol)
        temp_k = result["interior_temp_k"]
        energy = result["stored_energy_kwh"]
        if result["dust_event"]:
            storms += 1
        if not result["alive"]:
            alive = False
            timeline.append(result)
            break
        if sol % 50 == 0 or sol <= 3:
            timeline.append(result)

        # Resupply every 30 sols
        if sol % 30 == 0:
            energy += 200  # supply drop energy
            # food handled separately

    survived = sol if not alive else num_sols
    temps = [t["interior_temp_c"] for t in timeline]

    return {
        "planet": planet_id,
        "planet_name": p["name"],
        "sols_simulated": num_sols,
        "survived_sols": survived,
        "alive": alive,
        "min_temp_c": min(temps) if temps else 0,
        "max_temp_c": max(temps) if temps else 0,
        "storms_weathered": storms,
        "challenges": p["challenges"],
        "habitat_penalty": p["habitat_penalty"],
        "timeline_sample": timeline[:20],
    }


def multi_planet_backtest(num_sols: int = 669) -> list:
    """Backtest all planets and rank by survival."""
    results = []
    for pid in PLANETS:
        print(f"  Backtesting {PLANETS[pid]['name']}...")
        r = backtest_planet(pid, num_sols)
        results.append(r)
    results.sort(key=lambda r: (-r["survived_sols"], r["habitat_penalty"]))
    return results


if __name__ == "__main__":
    import json
    import sys

    sols = int(sys.argv[1]) if len(sys.argv) > 1 else 669

    print(f"=== Multi-Planet Backtest ({sols} sols) ===\n")
    results = multi_planet_backtest(sols)

    print(f"\n{'='*70}")
    print(f"  MULTI-PLANET SURVIVAL RANKING ({sols} sols)")
    print(f"{'='*70}\n")

    for i, r in enumerate(results):
        status = "✅ ALIVE" if r["alive"] else f"❌ DEAD at Sol {r['survived_sols']}"
        print(f"  #{i+1} {r['planet_name']:<30s} {status}")
        print(f"      Temp: {r['min_temp_c']:+.0f}°C to {r['max_temp_c']:+.0f}°C | "
              f"Storms: {r['storms_weathered']} | Penalty: {r['habitat_penalty']}×")
        print()

    # Save results
    output_path = "state/multiplanet-backtest.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {output_path}")
