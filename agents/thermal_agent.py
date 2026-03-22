"""Thermal regulation — the colony's body temperature."""

import math

AGENT = {
    "name": "thermal",
    "description": "Regulate habitat temperature based on Mars conditions and power",
    "triggers": ["thermal", "thermal_critical", "physics"],
    "phase": "physics",
    "priority": 2,
}

def run(colony: dict, sol: int, **kwargs) -> dict:
    """Thermal regulation. The habitat fights Mars to stay warm."""

    # Mars surface temp varies by solar longitude (season) and time of day
    ls = colony.get("solar_longitude", 0)
    lat = colony.get("latitude", -4.5)

    # Seasonal temperature variation (simplified)
    seasonal = 20 * math.sin(math.radians(ls))  # ±20K seasonal swing
    mars_surface_k = 210 + seasonal  # Mars average ~210K

    # Current habitat temp
    habitat_temp = colony.get("habitat_temp_k", 293)
    target_temp = 293  # 20°C

    # Heat loss to Mars (proportional to temp difference)
    insulation = 0.98  # 2% loss per sol
    heat_loss_k = (habitat_temp - mars_surface_k) * (1 - insulation)

    # Thermostat — only heat if below target, only cool if above
    power_available = colony.get("power_kwh", 0)
    delta_from_target = target_temp - (habitat_temp - heat_loss_k)

    if delta_from_target > 0:
        # Need heating
        power_for_heating = min(power_available * 0.2, delta_from_target * 2, 50)
        heating_k = power_for_heating * 0.5
    else:
        # Above target — passive cooling only, no power used
        power_for_heating = 0
        heating_k = delta_from_target * 0.3  # negative = cooling

    # New temp (clamped to prevent runaway)
    new_temp = max(180, min(320, habitat_temp - heat_loss_k + heating_k))

    # Clamp to survival range
    events = []
    if new_temp < 270:
        events.append(f"WARNING: Habitat temp critical ({new_temp:.0f}K). Risk of hypothermia.")
    if new_temp > 310:
        events.append(f"WARNING: Habitat overheating ({new_temp:.0f}K). Cooling needed.")

    colony["habitat_temp_k"] = round(new_temp, 1)
    colony["power_kwh"] = round(power_available - power_for_heating, 1)

    return {
        "colony": colony,
        "events": events,
        "metrics": {
            "thermal": {
                "mars_surface_k": round(mars_surface_k, 1),
                "habitat_temp_k": round(new_temp, 1),
                "heat_loss_k": round(heat_loss_k, 1),
                "heating_applied_k": round(heating_k, 1),
                "power_used_kwh": round(power_for_heating, 1),
            }
        },
    }
