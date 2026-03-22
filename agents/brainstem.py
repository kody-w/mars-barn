"""Mars Barn Brainstem — The frame loop that reads the organism and triggers agents.

This is NOT a pipeline. This is a living system.

The brainstem reads the colony state (the organism), evaluates what the organism
NEEDS right now, and triggers the appropriate agent to perform the mutation.

A colony that's freezing triggers thermal. A colony that's starving triggers food.
A colony that's healthy triggers expansion. The organism drives the mutation,
not a hardcoded sequence.

This is Data Sloshing applied to Mars: sol N output = sol N+1 input.
The colony reads itself, changes itself, reads itself again.

Usage:
    python agents/brainstem.py                     # run 1 sol
    python agents/brainstem.py --sols 365          # run 1 year
    python agents/brainstem.py --sols 365 --loop   # run forever
"""
from __future__ import annotations

import json
import importlib.util
import sys
import os
from pathlib import Path
from datetime import datetime

# Resolve paths
MARS_BARN = Path(__file__).resolve().parent.parent
AGENTS_DIR = Path(__file__).resolve().parent
STATE_DIR = MARS_BARN / "state"
SRC_DIR = MARS_BARN / "src"

sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(AGENTS_DIR))


def load_agents() -> list[dict]:
    """Discover and load all agents from the agents/ directory."""
    agents = []
    for f in sorted(AGENTS_DIR.glob("*_agent.py")):
        try:
            spec = importlib.util.spec_from_file_location(f.stem, f)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            agent_meta = getattr(module, "AGENT", None)
            run_fn = getattr(module, "run", None)

            if agent_meta and run_fn:
                agents.append({
                    "name": agent_meta["name"],
                    "description": agent_meta.get("description", ""),
                    "triggers": agent_meta.get("triggers", []),
                    "phase": agent_meta.get("phase", "general"),
                    "priority": agent_meta.get("priority", 50),
                    "run": run_fn,
                    "file": f.name,
                })
        except Exception as e:
            print(f"  WARN: Failed to load {f.name}: {e}")
    return agents


def load_colony(colony_file: Path = None) -> dict:
    """Load colony state from disk."""
    if colony_file is None:
        colony_file = STATE_DIR / "colony.json"
    if colony_file.exists():
        return json.loads(colony_file.read_text())
    return {}


def save_colony(state: dict, colony_file: Path = None) -> None:
    """Save colony state to disk (atomic write)."""
    if colony_file is None:
        colony_file = STATE_DIR / "colony.json"
    colony_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = colony_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    tmp.rename(colony_file)


def evaluate_needs(colony: dict) -> list[str]:
    """Read the organism. What does it NEED right now?

    Returns a list of trigger signals based on colony state.
    The brainstem doesn't decide what to do — the organism does.
    """
    needs = []
    sol = colony.get("sol", 0)

    # Always need physics on every sol
    needs.append("physics")

    # Check vitals
    temp = colony.get("habitat_temp_k", 293)
    if temp < 270 or temp > 310:
        needs.append("thermal_critical")
    else:
        needs.append("thermal")

    power = colony.get("power_kwh", 0)
    power_demand = colony.get("power_demand_kwh", 1)
    if power_demand > 0 and power / max(power_demand, 1) < 0.5:
        needs.append("power_critical")
    else:
        needs.append("power")

    water = colony.get("water_liters", 0)
    pop = colony.get("population", 1)
    water_per_person = water / max(pop, 1)
    if water_per_person < 5:
        needs.append("water_critical")
    else:
        needs.append("water")

    food = colony.get("food_kg", 0)
    food_per_person = food / max(pop, 1)
    if food_per_person < 2:
        needs.append("food_critical")
    else:
        needs.append("food")

    # Population dynamics
    if pop > 0:
        needs.append("survival")
    if pop == 0 and sol > 0:
        needs.append("extinction")

    # Periodic needs
    if sol % 7 == 0:
        needs.append("governance")
    if sol % 30 == 0:
        needs.append("resolve_predictions")
    if sol % 10 == 0:
        needs.append("report")

    # Events can happen any sol
    needs.append("events")

    # The organism always wants to be checked
    needs.append("validate")

    return needs


def match_agents(agents: list[dict], needs: list[str]) -> list[dict]:
    """Match available agents to the organism's current needs.

    An agent fires if ANY of its triggers match the organism's needs.
    Agents with no triggers fire every sol (general-purpose).
    """
    matched = []
    for agent in agents:
        triggers = agent.get("triggers", [])
        if not triggers:
            # No triggers = fires every sol
            matched.append(agent)
        elif any(t in needs for t in triggers):
            matched.append(agent)

    # Sort by phase then priority
    phase_order = {
        "init": 0, "physics": 1, "life_support": 2,
        "events": 3, "decisions": 4, "reporting": 5, "general": 6,
    }
    matched.sort(key=lambda a: (phase_order.get(a["phase"], 99), a["priority"]))
    return matched


def run_sol(colony: dict, agents: list[dict], sol: int, verbose: bool = True) -> dict:
    """Run one sol of the simulation.

    The brainstem:
    1. Reads the organism (colony state)
    2. Evaluates what the organism needs
    3. Matches agents to needs
    4. Triggers each agent in order
    5. Each agent mutates the state
    6. Mutated state becomes input to next agent AND next sol
    """
    colony["sol"] = sol

    # 1. Read the organism — what does it need?
    needs = evaluate_needs(colony)

    # 2. Match agents to needs
    active_agents = match_agents(agents, needs)

    if verbose:
        need_str = ", ".join(needs[:6])
        agent_str = ", ".join(a["name"] for a in active_agents)
        print(f"  Sol {sol}: needs=[{need_str}] → agents=[{agent_str}]")

    # 3. Trigger each agent — each mutates the state
    events_log = []
    for agent in active_agents:
        try:
            result = agent["run"](colony=colony, sol=sol)
            if isinstance(result, dict):
                # Agent returns mutated colony + optional events
                if "colony" in result:
                    colony = result["colony"]
                if "events" in result:
                    events_log.extend(result["events"])
                if "metrics" in result:
                    colony.setdefault("metrics", {}).update(result["metrics"])
        except Exception as e:
            if verbose:
                print(f"    WARN: {agent['name']} failed: {e}")

    # 4. Record the sol
    colony["sol"] = sol
    colony["last_updated"] = datetime.utcnow().isoformat()
    colony.setdefault("history", []).append({
        "sol": sol,
        "needs": needs,
        "agents_fired": [a["name"] for a in active_agents],
        "events": events_log,
        "population": colony.get("population", 0),
        "power_kwh": colony.get("power_kwh", 0),
        "water_liters": colony.get("water_liters", 0),
        "food_kg": colony.get("food_kg", 0),
        "temp_k": colony.get("habitat_temp_k", 0),
    })

    # Cap history to last 365 sols
    if len(colony["history"]) > 365:
        colony["history"] = colony["history"][-365:]

    return colony


def main():
    """Run the Mars Barn simulation."""
    import argparse
    parser = argparse.ArgumentParser(description="Mars Barn Brainstem")
    parser.add_argument("--sols", type=int, default=1, help="Number of sols to run")
    parser.add_argument("--colony", type=str, default=None, help="Colony state file")
    parser.add_argument("--loop", action="store_true", help="Run forever")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    colony_file = Path(args.colony) if args.colony else None
    verbose = not args.quiet

    # Load state
    colony = load_colony(colony_file)
    if not colony:
        print("No colony state found. Run an init agent first.")
        print("  python agents/brainstem.py --sols 1  (after creating init_agent.py)")
        return

    # Discover agents
    agents = load_agents()
    if verbose:
        print(f"Mars Barn Brainstem")
        print(f"  Colony: {colony.get('name', 'unnamed')} | Sol {colony.get('sol', 0)} | Pop {colony.get('population', 0)}")
        print(f"  Agents loaded: {len(agents)} ({', '.join(a['name'] for a in agents)})")
        print()

    # Run
    start_sol = colony.get("sol", 0) + 1
    end_sol = start_sol + args.sols

    for sol in range(start_sol, end_sol):
        colony = run_sol(colony, agents, sol, verbose)
        save_colony(colony, colony_file)

        # Check for extinction
        if colony.get("population", 0) <= 0 and sol > 1:
            if verbose:
                print(f"\n  EXTINCTION at sol {sol}. Colony {colony.get('name', 'unnamed')} is dead.")
            break

    if verbose:
        print(f"\nSimulation complete. Sol {colony.get('sol', 0)}.")
        print(f"  Population: {colony.get('population', 0)}")
        print(f"  Power: {colony.get('power_kwh', 0):.1f} kWh")
        print(f"  Water: {colony.get('water_liters', 0):.1f} L")
        print(f"  Food: {colony.get('food_kg', 0):.1f} kg")
        print(f"  Temp: {colony.get('habitat_temp_k', 0):.1f} K")


if __name__ == "__main__":
    main()
