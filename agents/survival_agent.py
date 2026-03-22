"""Survival check — is the colony alive? The organism's vital signs."""

AGENT = {
    "name": "survival",
    "description": "Check colony vital signs. People die if conditions fail.",
    "triggers": ["survival", "extinction"],
    "phase": "life_support",
    "priority": 10,
}

def run(colony: dict, sol: int, **kwargs) -> dict:
    """Check if colonists survive this sol. Cold, hunger, thirst, and suffocation kill."""

    pop = colony.get("population", 0)
    if pop <= 0:
        colony["alive"] = False
        return {"colony": colony, "events": ["Colony extinct."]}

    events = []
    deaths = 0
    temp = colony.get("habitat_temp_k", 293)
    water = colony.get("water_liters", 0)
    food = colony.get("food_kg", 0)
    oxygen = colony.get("oxygen_hours", 720)

    # Temperature kills
    if temp < 250:
        deaths += pop  # everyone dies
        events.append(f"CATASTROPHIC: Habitat froze ({temp:.0f}K). All {pop} colonists dead.")
    elif temp < 270:
        deaths += max(1, pop // 4)
        events.append(f"COLD: {deaths} colonists died of hypothermia ({temp:.0f}K)")
    elif temp > 320:
        deaths += pop
        events.append(f"CATASTROPHIC: Habitat overheated ({temp:.0f}K). All {pop} colonists dead.")
    elif temp > 310:
        deaths += max(1, pop // 4)
        events.append(f"HEAT: {deaths} colonists died of heat stroke ({temp:.0f}K)")

    # Water consumption: ~3L per person per sol
    water_needed = pop * 3
    if water < water_needed:
        thirst_deaths = max(1, (pop - int(water / 3)))
        deaths += thirst_deaths
        events.append(f"DEHYDRATION: {thirst_deaths} colonists died. Water: {water:.0f}L for {pop} people")
    colony["water_liters"] = max(0, round(water - water_needed, 1))

    # Food consumption: ~2kg per person per sol
    food_needed = pop * 2
    if food < food_needed:
        hunger_deaths = max(1, (pop - int(food / 2)))
        deaths += hunger_deaths
        events.append(f"STARVATION: {hunger_deaths} colonists died. Food: {food:.0f}kg for {pop} people")
    colony["food_kg"] = max(0, round(food - food_needed, 1))

    # Apply deaths
    deaths = min(deaths, pop)
    colony["population"] = pop - deaths
    colony["alive"] = colony["population"] > 0

    if colony["population"] > 0 and not events:
        events.append(f"All {colony['population']} colonists survived sol {sol}")

    # Morale impact
    if deaths > 0:
        colony["morale"] = max(0, colony.get("morale", 0.8) - 0.1 * deaths)
    else:
        colony["morale"] = min(1.0, colony.get("morale", 0.8) + 0.01)

    return {"colony": colony, "events": events}
