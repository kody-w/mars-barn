"""Initialize a Mars colony — the first breath."""

import json
import random
from pathlib import Path

AGENT = {
    "name": "init",
    "description": "Initialize a new colony with starting conditions",
    "triggers": [],  # manual trigger only
    "phase": "init",
    "priority": 0,
}

def run(colony: dict = None, sol: int = 0, **kwargs) -> dict:
    """Birth a colony. First breath."""
    if colony and colony.get("population", 0) > 0:
        return {"colony": colony, "events": ["Colony already initialized"]}

    colony = {
        "name": "Olympus Base",
        "sol": 0,
        "latitude": -4.5,
        "longitude": 137.4,
        "population": 6,
        "habitat_temp_k": 293,
        "power_kwh": 500,
        "power_demand_kwh": 200,
        "solar_panels_m2": 1000,
        "water_liters": 2000,
        "water_recycling_rate": 0.92,
        "food_kg": 500,
        "food_growth_rate_kg_per_sol": 3.0,
        "oxygen_hours": 720,
        "solar_longitude": 0,
        "dust_storm_active": False,
        "morale": 0.8,
        "alive": True,
        "founded_at": "sol-0",
        "history": [],
        "metrics": {},
    }

    return {
        "colony": colony,
        "events": ["Colony founded: Olympus Base, 6 colonists, Sol 0"],
    }
