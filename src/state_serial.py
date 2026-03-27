"""Mars Barn — State Serialization

Save and load full simulation state to/from JSON.
Supports snapshots and diffing between timesteps.

Author: zion-coder-10 (claimed)
"""
import json
from typing import Any, Optional

from constants import (
    HABITAT_CREW_SIZE,
    HABITAT_TARGET_TEMP_K,
    HABITAT_INTERIOR_PRESSURE_PA,
    HABITAT_SOLAR_PANEL_AREA_M2,
    HABITAT_SOLAR_PANEL_EFFICIENCY,
    HABITAT_INSULATION_R_VALUE,
    HABITAT_STORED_ENERGY_KWH,
    HABITAT_HEATER_POWER_W,
)


def create_state(
    sol: int = 0,
    terrain: list = None,
    latitude: float = 0.0,
    longitude: float = 0.0,
    hour: float = 12.0,
    solar_longitude: float = 0.0,
    active_events: list = None,
    habitat: dict = None,
) -> dict:
    """Create a new simulation state dict."""
    return {
        "version": 1,
        "sol": sol,
        "hour": hour,
        "location": {
            "latitude_deg": latitude,
            "longitude_deg": longitude,
        },
        "solar_longitude": solar_longitude,
        "terrain": terrain or [],
        "active_events": active_events or [],
        "habitat": habitat or {
            "crew_size": HABITAT_CREW_SIZE,
            "interior_temp_k": HABITAT_TARGET_TEMP_K,
            "interior_pressure_pa": HABITAT_INTERIOR_PRESSURE_PA,
            "power_kw": 0.0,
            "solar_panel_area_m2": HABITAT_SOLAR_PANEL_AREA_M2,
            "solar_panel_efficiency": HABITAT_SOLAR_PANEL_EFFICIENCY,
            "insulation_r_value": HABITAT_INSULATION_R_VALUE,
            "stored_energy_kwh": HABITAT_STORED_ENERGY_KWH,
            "heater_power_w": HABITAT_HEATER_POWER_W,
        },
        "resources": {
            "o2_kg": 168.0,        # ~200 days at 0.84 kg/person/sol for initial crew
            "h2o_liters": 200.0,   # starting water reserve
            "food_kcal": 0.0,      # greenhouse starts empty — crops need time to grow
        },
        "metrics": {
            "total_power_generated_kwh": 0.0,
            "total_heat_lost_kwh": 0.0,
            "events_survived": 0,
            "sols_survived": sol,
        },
    }


def save_state(state: dict, filepath: str) -> None:
    """Save simulation state to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def load_state(filepath: str) -> dict:
    """Load simulation state from a JSON file."""
    with open(filepath) as f:
        return json.load(f)


def snapshot(state: dict) -> dict:
    """Create a lightweight snapshot for history tracking.

    Strips terrain data (too large) and keeps only metrics + key params.
    """
    return {
        "sol": state["sol"],
        "hour": state["hour"],
        "solar_longitude": state.get("solar_longitude", 0),
        "habitat": {
            "interior_temp_k": state["habitat"]["interior_temp_k"],
            "power_kw": state["habitat"]["power_kw"],
            "stored_energy_kwh": state["habitat"]["stored_energy_kwh"],
        },
        "active_event_count": len(state.get("active_events", [])),
        "metrics": dict(state.get("metrics", {})),
    }


def diff_states(old: dict, new: dict) -> dict:
    """Compute differences between two snapshots.

    Returns dict of changed fields with (old_value, new_value) tuples.
    """
    changes = {}
    _diff_recursive(old, new, "", changes)
    return changes


def _diff_recursive(old: Any, new: Any, path: str, changes: dict) -> None:
    """Recursively diff two dicts/values."""
    if isinstance(old, dict) and isinstance(new, dict):
        all_keys = set(list(old.keys()) + list(new.keys()))
        for key in sorted(all_keys):
            p = f"{path}.{key}" if path else key
            if key not in old:
                changes[p] = (None, new[key])
            elif key not in new:
                changes[p] = (old[key], None)
            else:
                _diff_recursive(old[key], new[key], p, changes)
    elif old != new:
        changes[path] = (old, new)


if __name__ == "__main__":
    state = create_state(sol=0, latitude=-4.5, longitude=137.4)
    print(f"Initial state: sol {state['sol']}, crew {state['habitat']['crew_size']}")

    snap1 = snapshot(state)
    state["sol"] = 10
    state["habitat"]["stored_energy_kwh"] = 480.0
    state["metrics"]["sols_survived"] = 10
    snap2 = snapshot(state)

    diff = diff_states(snap1, snap2)
    print(f"\nChanges after 10 sols:")
    for path, (old, new) in diff.items():
        print(f"  {path}: {old} → {new}")

