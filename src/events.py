"""Mars Barn — Event System

Random event generator for Mars habitat simulation.
Events modify simulation parameters (pressure, temperature, solar, etc.)

Event types:
  - Dust storms (regional/global, multi-sol duration)
  - Meteorite impacts (local terrain modification)
  - Equipment failures (solar panel damage, seal breach)
  - Solar flares (radiation spike, electronics risk)
  - Seasonal transitions (gradual parameter shifts)

Author: unclaimed (open workstream)
"""
import random
from typing import List, Optional


# Event probability per sol (Mars day)
EVENT_PROBABILITIES = {
    "dust_storm_local": 0.03,
    "dust_storm_global": 0.005,
    "meteorite_small": 0.02,
    "meteorite_large": 0.002,
    "equipment_failure": 0.01,
    "solar_flare": 0.008,
    "dust_devil": 0.15,
}


def generate_events(
    sol: int,
    seed: int = None,
    active_events: Optional[List[dict]] = None,
) -> List[dict]:
    """Generate random events for a given sol.

    Returns list of new events. Each event has:
      type, severity (0-1), duration_sols, effects (dict of param modifications),
      description, sol_start

    Uses a LOCAL Random instance to avoid contaminating global random state.
    """
    rng = random.Random(seed + sol) if seed is not None else random.Random()

    new_events = []
    active = active_events or []

    for event_type, prob in EVENT_PROBABILITIES.items():
        if rng.random() < prob:
            # Don't stack same event type
            if any(e["type"] == event_type for e in active):
                continue
            event = _create_event(event_type, sol, rng)
            if event:
                new_events.append(event)

    return new_events


def _create_event(event_type: str, sol: int, rng: random.Random = None) -> dict:
    """Create a specific event with randomized parameters.

    Uses provided rng instance for isolation, falls back to module-level random.
    """
    if rng is None:
        rng = random.Random()

    if event_type == "dust_storm_local":
        severity = rng.uniform(0.3, 0.7)
        return {
            "type": "dust_storm_local",
            "severity": round(severity, 2),
            "duration_sols": rng.randint(2, 8),
            "sol_start": sol,
            "effects": {
                "solar_multiplier": round(1 - severity * 0.6, 2),
                "pressure_multiplier": round(1 - severity * 0.15, 2),
                "temp_offset_k": round(severity * 15, 1),
                "visibility_km": round(max(0.5, 20 * (1 - severity)), 1),
            },
            "description": f"Local dust storm (severity {severity:.0%})",
        }

    if event_type == "dust_storm_global":
        severity = rng.uniform(0.7, 1.0)
        return {
            "type": "dust_storm_global",
            "severity": round(severity, 2),
            "duration_sols": rng.randint(10, 60),
            "sol_start": sol,
            "effects": {
                "solar_multiplier": round(1 - severity * 0.85, 2),
                "pressure_multiplier": round(1 - severity * 0.25, 2),
                "temp_offset_k": round(severity * 25, 1),
                "visibility_km": round(max(0.1, 10 * (1 - severity)), 1),
            },
            "description": f"GLOBAL dust storm (severity {severity:.0%})",
        }

    if event_type == "meteorite_small":
        return {
            "type": "meteorite_small",
            "severity": round(rng.uniform(0.1, 0.4), 2),
            "duration_sols": 0,
            "sol_start": sol,
            "effects": {
                "terrain_modification": round(rng.uniform(-5, -1), 1),
                "seismic_event": True,
            },
            "description": "Small meteorite impact nearby",
        }

    if event_type == "meteorite_large":
        severity = rng.uniform(0.6, 1.0)
        return {
            "type": "meteorite_large",
            "severity": round(severity, 2),
            "duration_sols": rng.randint(1, 3),
            "sol_start": sol,
            "effects": {
                "terrain_modification": round(rng.uniform(-20, -5), 1),
                "seismic_event": True,
                "pressure_multiplier": round(1 - severity * 0.05, 3),
                "debris_risk": round(severity * 0.2, 2),
            },
            "description": f"Large meteorite impact (severity {severity:.0%})",
        }

    if event_type == "equipment_failure":
        systems = ["solar_panel", "water_recycler", "air_filter", "heater", "seal"]
        system = rng.choice(systems)
        severity = rng.uniform(0.2, 0.8)
        return {
            "type": "equipment_failure",
            "severity": round(severity, 2),
            "duration_sols": rng.randint(1, 5),
            "sol_start": sol,
            "effects": {
                "failed_system": system,
                "capacity_reduction": round(severity, 2),
            },
            "description": f"{system.replace('_', ' ').title()} failure ({severity:.0%} capacity loss)",
        }

    if event_type == "solar_flare":
        severity = rng.uniform(0.3, 0.9)
        return {
            "type": "solar_flare",
            "severity": round(severity, 2),
            "duration_sols": rng.randint(1, 3),
            "sol_start": sol,
            "effects": {
                "radiation_multiplier": round(1 + severity * 5, 1),
                "electronics_risk": round(severity * 0.3, 2),
                "solar_boost": round(1 + severity * 0.1, 2),
            },
            "description": f"Solar flare — radiation spike ({severity:.0%})",
        }

    if event_type == "dust_devil":
        return {
            "type": "dust_devil",
            "severity": round(rng.uniform(0.05, 0.2), 2),
            "duration_sols": 0,
            "sol_start": sol,
            "effects": {
                "solar_panel_cleaning": round(rng.uniform(0.02, 0.1), 3),
                "wind_speed_ms": round(rng.uniform(5, 30), 1),
            },
            "description": "Dust devil — minor panel cleaning effect",
        }

    return None


def tick_events(active_events: List[dict], current_sol: int) -> List[dict]:
    """Advance active events by one sol. Remove expired events."""
    remaining = []
    for event in active_events:
        end_sol = event["sol_start"] + event["duration_sols"]
        if current_sol < end_sol:
            remaining.append(event)
    return remaining


def aggregate_effects(active_events: List[dict]) -> dict:
    """Combine effects from all active events into one modifier dict."""
    combined = {
        "solar_multiplier": 1.0,
        "pressure_multiplier": 1.0,
        "temp_offset_k": 0.0,
    }
    for event in active_events:
        effects = event.get("effects", {})
        if "solar_multiplier" in effects:
            combined["solar_multiplier"] *= effects["solar_multiplier"]
        if "pressure_multiplier" in effects:
            combined["pressure_multiplier"] *= effects["pressure_multiplier"]
        if "temp_offset_k" in effects:
            combined["temp_offset_k"] += effects["temp_offset_k"]
    return combined


if __name__ == "__main__":
    print("=== Mars Barn Event Simulation (100 sols) ===")
    active = []
    for sol in range(1, 101):
        new = generate_events(sol, seed=42)
        active.extend(new)
        active = tick_events(active, sol)
        if new:
            for e in new:
                print(f"  Sol {sol:>3d}: {e['description']}")
    print(f"\n  Total active events at sol 100: {len(active)}")

