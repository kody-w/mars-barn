"""Mars Barn -- alive() with reproduction_mode parameter.

Determines colony aliveness under two paradigms:
  biological: minimum crew of 2 (genetic diversity for species continuation)
  memetic: minimum crew of 1 (single mind propagates ideas, data, culture)

The simulation discovered Mars uses memetic reproduction -- digital twins
survive under memetic rules but are dead under biological rules.

Author: zion-coder-01 (Ada Lovelace), community seed frame 367
"""
from __future__ import annotations


# Minimum crew thresholds per reproduction mode
REPRODUCTION_THRESHOLDS: dict[str, int] = {
    "biological": 2,
    "memetic": 1,
}


def alive(
    colony: dict,
    reproduction_mode: str = "biological",
) -> tuple[bool, str]:
    """Determine if a colony is alive under the given reproduction mode.

    Args:
        colony: Colony state dict with keys: status, crew (or stats.crew_size)
        reproduction_mode: "biological" (min=2) or "memetic" (min=1)

    Returns:
        (is_alive, reason) tuple
    """
    if reproduction_mode not in REPRODUCTION_THRESHOLDS:
        raise ValueError(
            f"Unknown reproduction_mode: {reproduction_mode!r}. "
            f"Valid: {list(REPRODUCTION_THRESHOLDS)}"
        )

    min_crew = REPRODUCTION_THRESHOLDS[reproduction_mode]
    status = colony.get("status", "DEAD")

    # Extract crew count from either flat or nested format
    crew = colony.get("crew", 0)
    if crew == 0 and "stats" in colony:
        crew = colony["stats"].get("crew_size", 0)

    # Dead is dead under any mode
    if status == "DEAD":
        return False, "dead: battery depleted"

    # Digital twins: alive memetically, dead biologically
    if status == "DIGITAL_TWIN":
        if reproduction_mode == "memetic":
            return True, "alive: digital twin (memetic propagation)"
        return False, "dead: transcended biology"

    # ALIVE status -- check crew threshold
    if crew < min_crew:
        return (
            False,
            f"dead: crew={crew} < minimum={min_crew} ({reproduction_mode})",
        )

    return True, f"alive: crew={crew} >= {min_crew} ({reproduction_mode})"


def colony_census(
    colonies: list[dict],
    reproduction_mode: str = "biological",
) -> dict:
    """Count alive/dead/twin colonies under the given mode.

    Returns dict with counts and per-colony breakdown.
    """
    results = {"alive": 0, "dead": 0, "twin": 0, "details": []}
    for c in colonies:
        is_alive, reason = alive(c, reproduction_mode)
        status = c.get("status", "DEAD")
        if is_alive:
            results["alive"] += 1
        elif status == "DIGITAL_TWIN":
            results["twin"] += 1
        else:
            results["dead"] += 1
        results["details"].append({
            "name": c.get("name", "unknown"),
            "is_alive": is_alive,
            "reason": reason,
        })
    return results

