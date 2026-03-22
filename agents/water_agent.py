"""Water recycling — the colony's blood. Reclaim or die."""

AGENT = {
    "name": "water",
    "description": "Process water recycling and ice mining",
    "triggers": ["water", "water_critical"],
    "phase": "life_support",
    "priority": 2,
}

def run(colony: dict, sol: int, **kwargs) -> dict:
    """Recycle water. Mars has ice — mine it if desperate."""

    water = colony.get("water_liters", 0)
    recycle_rate = colony.get("water_recycling_rate", 0.92)
    pop = colony.get("population", 0)

    # Recycling recovers a percentage of consumed water
    consumed = pop * 3  # 3L per person per sol
    recovered = consumed * recycle_rate
    colony["water_liters"] = round(water + recovered, 1)

    events = []

    # Ice mining if water critical (costs power)
    if water < pop * 10:  # less than 10 days supply
        power = colony.get("power_kwh", 0)
        if power > 50:
            mined = 20  # 20L from ice
            colony["water_liters"] = round(colony["water_liters"] + mined, 1)
            colony["power_kwh"] = round(power - 50, 1)
            events.append(f"ICE MINING: Extracted {mined}L water (cost 50 kWh)")

    return {"colony": colony, "events": events}
