"""Random events — dust storms, equipment failure, discoveries. Life happens."""

import random

AGENT = {
    "name": "events",
    "description": "Generate random events that affect the colony",
    "triggers": ["events"],
    "phase": "events",
    "priority": 1,
}

# Events weighted by probability
EVENTS = [
    {"name": "dust_storm_start", "prob": 0.03, "effect": "dust_storm_active=True"},
    {"name": "dust_storm_end", "prob": 0.15, "condition": "dust_storm", "effect": "dust_storm_active=False"},
    {"name": "solar_panel_damage", "prob": 0.02, "effect": "solar_panels_m2*=0.95"},
    {"name": "water_leak", "prob": 0.02, "effect": "water_liters*=0.9"},
    {"name": "equipment_repair", "prob": 0.05, "effect": "solar_panels_m2*=1.02"},
    {"name": "mineral_discovery", "prob": 0.03, "effect": "morale+=0.05"},
    {"name": "birth", "prob": 0.01, "condition": "pop>4,morale>0.6", "effect": "population+=1"},
    {"name": "accident", "prob": 0.01, "effect": "population-=1"},
]

def run(colony: dict, sol: int, **kwargs) -> dict:
    """Roll the dice. Life on Mars is uncertain."""

    events = []
    pop = colony.get("population", 0)
    dust = colony.get("dust_storm_active", False)
    morale = colony.get("morale", 0.8)

    for event in EVENTS:
        # Check conditions
        condition = event.get("condition", "")
        if condition == "dust_storm" and not dust:
            continue
        if condition == "pop>4,morale>0.6" and (pop <= 4 or morale <= 0.6):
            continue

        # Roll
        if random.random() < event["prob"]:
            effect = event["effect"]
            name = event["name"]

            # Apply effect
            if "=" in effect and "*" not in effect and "+" not in effect and "-" not in effect:
                key, val = effect.split("=")
                colony[key] = val == "True" if val in ("True", "False") else float(val)
            elif "*=" in effect:
                key, mult = effect.split("*=")
                colony[key] = round(colony.get(key, 0) * float(mult), 1)
            elif "+=" in effect:
                key, add = effect.split("+=")
                colony[key] = round(colony.get(key, 0) + float(add), 2)
            elif "-=" in effect:
                key, sub = effect.split("-=")
                colony[key] = max(0, round(colony.get(key, 0) - float(sub), 2))

            events.append(f"EVENT: {name} — {effect}")

    return {"colony": colony, "events": events}
