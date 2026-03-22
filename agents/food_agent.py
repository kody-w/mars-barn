"""Food production — the colony's stomach. Grow or starve."""

AGENT = {
    "name": "food",
    "description": "Manage food growth in greenhouse modules",
    "triggers": ["food", "food_critical"],
    "phase": "life_support",
    "priority": 3,
}

def run(colony: dict, sol: int, **kwargs) -> dict:
    """Grow food. Greenhouses need power, water, and warmth."""

    food = colony.get("food_kg", 0)
    growth_rate = colony.get("food_growth_rate_kg_per_sol", 3.0)
    temp = colony.get("habitat_temp_k", 293)
    water = colony.get("water_liters", 0)
    power = colony.get("power_kwh", 0)

    events = []

    # Growth modifiers
    temp_factor = 1.0
    if temp < 280:
        temp_factor = 0.3  # too cold for plants
        events.append("GREENHOUSE: Cold temps reducing crop yield")
    elif temp > 305:
        temp_factor = 0.5  # too hot
        events.append("GREENHOUSE: Heat stress on crops")

    water_factor = 1.0
    if water < 100:
        water_factor = 0.2  # no water for irrigation
        events.append("GREENHOUSE: Water shortage — crops wilting")

    power_factor = 1.0
    if power < 30:
        power_factor = 0.5  # grow lights need power
        events.append("GREENHOUSE: Low power — reduced grow light hours")

    # Grow
    grown = growth_rate * temp_factor * water_factor * power_factor
    colony["food_kg"] = round(food + grown, 1)

    # Greenhouse uses some water and power
    colony["water_liters"] = round(colony["water_liters"] - grown * 2, 1)  # 2L per kg of food
    colony["power_kwh"] = round(colony.get("power_kwh", 0) - 10, 1)  # 10 kWh for grow lights

    return {"colony": colony, "events": events}
