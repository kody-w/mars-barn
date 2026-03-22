"""Solar energy — the colony's heartbeat. No sun, no power, no life."""

import math

AGENT = {
    "name": "solar",
    "description": "Calculate solar energy production for the sol",
    "triggers": ["power", "power_critical", "physics"],
    "phase": "physics",
    "priority": 1,
}

def run(colony: dict, sol: int, **kwargs) -> dict:
    """Generate power from solar panels. Mars gets ~43% of Earth's sunlight."""

    ls = colony.get("solar_longitude", 0)
    lat = colony.get("latitude", -4.5)
    panels_m2 = colony.get("solar_panels_m2", 1000)
    dust_storm = colony.get("dust_storm_active", False)

    # Solar constant at Mars: ~590 W/m² (vs 1361 at Earth)
    solar_constant = 590

    # Seasonal variation (Mars eccentricity)
    eccentricity_factor = 1 + 0.09 * math.cos(math.radians(ls - 250))

    # Latitude factor (simplified)
    declination = 25.19 * math.sin(math.radians(ls))
    cos_zenith = max(0.1, math.cos(math.radians(abs(lat - declination))))

    # Dust storm reduces by 80%
    dust_factor = 0.2 if dust_storm else 1.0

    # Panel efficiency ~20%
    efficiency = 0.20

    # Daily energy (kWh) — Mars sol is ~24.6 hours, ~12h of useful sunlight
    irradiance = solar_constant * eccentricity_factor * cos_zenith * dust_factor
    energy_kwh = irradiance * panels_m2 * efficiency * 12 / 1000  # W→kW, 12h

    # Add to colony power
    colony["power_kwh"] = round(colony.get("power_kwh", 0) + energy_kwh, 1)

    # Advance solar longitude
    colony["solar_longitude"] = (ls + 0.5) % 360

    events = []
    if energy_kwh < colony.get("power_demand_kwh", 200) * 0.5:
        events.append(f"LOW POWER: Solar produced only {energy_kwh:.0f} kWh (demand: {colony.get('power_demand_kwh', 200)} kWh)")

    return {
        "colony": colony,
        "events": events,
        "metrics": {
            "solar": {
                "irradiance_wm2": round(irradiance, 1),
                "energy_kwh": round(energy_kwh, 1),
                "dust_storm": dust_storm,
                "solar_longitude": round(colony["solar_longitude"], 1),
            }
        },
    }
