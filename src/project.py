#!/usr/bin/env python3
"""Mars Barn — Colony Projection Engine

Datasloshing: fast-forward the colony using intelligent trend analysis.

Combines:
  1. Statistical profiling of colony history (mean/median/std/min/max)
  2. Event frequency distributions from the log
  3. Extreme value modeling (thousand-year events via Poisson)
  4. Monte Carlo forward simulation using real tick_sol physics
  5. microGPT narrative generation for each projected sol

Usage:
    python src/project.py                     # project 30 sols, 20 runs
    python src/project.py --sols 100 --runs 50
    python src/project.py --json              # output as JSON
"""
import json
import math
import copy
import os
import sys
import random
import statistics
import argparse
from pathlib import Path
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from live import load_colony, tick_sol, default_colony

ROOT = Path(__file__).resolve().parent.parent


# ── Historical Statistical Profile ──────────────────────────────────────

def analyze_history(colony: dict) -> dict:
    """Extract statistical profile from colony log history."""
    log = colony.get("log", [])
    if not log:
        return _empty_profile()

    fields = ["int_c", "ext_c", "solar_kwh", "heat_kwh", "stored_kwh", "dust", "food_kg"]
    profile = {}

    for field in fields:
        values = [e[field] for e in log if field in e]
        if not values:
            continue
        profile[field] = {
            "min": min(values),
            "max": max(values),
            "mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
            "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
            "p10": round(sorted(values)[max(0, int(len(values) * 0.1))], 2),
            "p90": round(sorted(values)[min(len(values) - 1, int(len(values) * 0.9))], 2),
            "trend": _compute_trend(values),
            "n": len(values),
        }

    # Morale/health if available
    for field in ["morale", "health"]:
        values = [e[field] for e in log if field in e]
        if values:
            profile[field] = {
                "min": min(values),
                "max": max(values),
                "mean": round(statistics.mean(values), 2),
                "median": round(statistics.median(values), 2),
                "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
                "trend": _compute_trend(values),
                "n": len(values),
            }

    return profile


def _compute_trend(values: list) -> float:
    """Simple linear regression slope (units per sol)."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return round(numerator / denominator, 4) if denominator else 0.0


def _empty_profile() -> dict:
    return {}


# ── Event Frequency Analysis ────────────────────────────────────────────

def analyze_events(colony: dict) -> dict:
    """Compute event frequencies and return-period estimates."""
    log = colony.get("log", [])
    total_sols = len(log) or 1

    # Count all events across history
    event_counts = Counter()
    for entry in log:
        for ev in entry.get("events", []):
            # Normalize event types (strip parameters)
            ev_type = ev.split("(")[0].split(":")[0]
            event_counts[ev_type] += 1

    frequencies = {}
    for ev_type, count in event_counts.items():
        freq = count / total_sols
        frequencies[ev_type] = {
            "count": count,
            "frequency_per_sol": round(freq, 4),
            "return_period_sols": round(1 / freq, 1) if freq > 0 else float("inf"),
        }

    # Add known extreme events not yet observed
    extreme_events = {
        "global_dust_storm": {"prob_per_sol": 0.0005, "return_period_sols": 2000},
        "large_meteorite": {"prob_per_sol": 0.002, "return_period_sols": 500},
        "solar_flare": {"prob_per_sol": 0.008, "return_period_sols": 125},
        "equipment_cascade": {"prob_per_sol": 0.001, "return_period_sols": 1000},
        "subsurface_quake": {"prob_per_sol": 0.0003, "return_period_sols": 3333},
    }
    for ev, params in extreme_events.items():
        if ev not in frequencies:
            frequencies[ev] = {
                "count": 0,
                "frequency_per_sol": params["prob_per_sol"],
                "return_period_sols": params["return_period_sols"],
                "modeled": True,
            }

    return frequencies


# ── Extreme Value / Thousand-Year Event Modeling ────────────────────────

def model_extremes(profile: dict, projection_sols: int) -> list:
    """Generate potential extreme events using Poisson arrival modeling."""
    extreme_events = []

    # Thousand-year class events
    event_catalog = [
        {
            "type": "global_dust_storm",
            "prob_per_sol": 0.0005,
            "severity_range": (0.7, 1.0),
            "duration_range": (30, 120),
            "effects": {"solar_mult": 0.15, "temp_offset_k": 25, "food_impact": -0.5},
            "description": "Planet-encircling dust storm — solar output drops to 15%",
        },
        {
            "type": "large_meteorite",
            "prob_per_sol": 0.002,
            "severity_range": (0.6, 1.0),
            "duration_range": (1, 3),
            "effects": {"panel_damage": 0.3, "seal_breach_risk": 0.4},
            "description": "Large meteorite impact near colony — shockwave and dust cloud",
        },
        {
            "type": "solar_proton_event",
            "prob_per_sol": 0.001,
            "severity_range": (0.5, 0.9),
            "duration_range": (1, 5),
            "effects": {"crew_health_hit": 0.15, "electronics_risk": 0.3},
            "description": "Solar proton event — radiation spike, crew shelter-in-place",
        },
        {
            "type": "subsurface_quake",
            "prob_per_sol": 0.0003,
            "severity_range": (0.3, 0.8),
            "duration_range": (1, 1),
            "effects": {"structural_risk": 0.2, "seal_breach_risk": 0.15},
            "description": "Subsurface marsquake — structural integrity check required",
        },
        {
            "type": "equipment_cascade",
            "prob_per_sol": 0.001,
            "severity_range": (0.5, 0.9),
            "duration_range": (3, 15),
            "effects": {"power_reduction": 0.4, "heating_reduction": 0.3},
            "description": "Cascading equipment failure — multiple systems degraded",
        },
    ]

    for event in event_catalog:
        # Poisson: expected arrivals in projection window
        lam = event["prob_per_sol"] * projection_sols
        # Sample number of arrivals
        n_arrivals = _poisson_sample(lam)
        for _ in range(n_arrivals):
            sol_offset = random.randint(1, projection_sols)
            severity = random.uniform(*event["severity_range"])
            duration = random.randint(*event["duration_range"])
            extreme_events.append({
                "sol_offset": sol_offset,
                "type": event["type"],
                "severity": round(severity, 2),
                "duration_sols": duration,
                "effects": event["effects"],
                "description": event["description"],
            })

    return sorted(extreme_events, key=lambda e: e["sol_offset"])


def _poisson_sample(lam: float) -> int:
    """Sample from Poisson distribution using Knuth's algorithm."""
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


# ── Monte Carlo Forward Projection ─────────────────────────────────────

def project_forward(
    colony: dict,
    projection_sols: int = 30,
    num_runs: int = 20,
    seed: int = None,
) -> dict:
    """Run Monte Carlo projections from current colony state.

    Returns:
        - profile: statistical analysis of history
        - event_frequencies: observed + modeled event rates
        - extreme_events: Poisson-sampled thousand-year events
        - projections: per-sol p10/p50/p90 confidence bands
        - runs: individual run trajectories (condensed)
        - narratives: GPT-style narrative for the median run
    """
    if seed is not None:
        random.seed(seed)

    # Analyze what we know
    profile = analyze_history(colony)
    event_freqs = analyze_events(colony)
    extremes = model_extremes(profile, projection_sols)

    start_sol = colony["sol"]
    all_runs = []

    for run_idx in range(num_runs):
        run_colony = copy.deepcopy(colony)
        # Perturb name so tick_sol's deterministic seed diverges per run
        run_colony["name"] = f"{colony['name']}::run{run_idx}"
        # Remove log to keep memory light during projection
        run_colony["log"] = run_colony["log"][-5:]  # keep last 5 for context
        run_seed = (seed or 42) + run_idx * 7919
        random.seed(run_seed)

        trajectory = []
        dead = False

        # Pre-compute which extreme events hit this run
        run_extremes = []
        for ext in extremes:
            if random.random() < (1.0 / num_runs) * 3:  # each run sees ~3x its share
                run_extremes.append(ext)

        for sol_offset in range(1, projection_sols + 1):
            sol = start_sol + sol_offset

            # Inject extreme events
            for ext in run_extremes:
                if ext["sol_offset"] == sol_offset:
                    _apply_extreme(run_colony, ext)

            entry = tick_sol(run_colony, sol)

            # Check for death
            if any("COLONY_DEAD" in ev for ev in entry.get("events", [])):
                dead = True

            trajectory.append({
                "sol": sol,
                "int_c": entry["int_c"],
                "stored_kwh": entry["stored_kwh"],
                "food_kg": entry["food_kg"],
                "morale": entry.get("morale", 0),
                "health": entry.get("health", 0),
                "storm": entry["storm"],
                "events": [e for e in entry["events"] if e != "dust_devil"],
                "dead": dead,
            })

            if dead:
                # Pad remaining sols with death state
                for remaining in range(sol_offset + 1, projection_sols + 1):
                    trajectory.append({
                        "sol": start_sol + remaining,
                        "int_c": trajectory[-1]["int_c"],
                        "stored_kwh": 0,
                        "food_kg": 0,
                        "morale": 0,
                        "health": 0,
                        "storm": False,
                        "events": [],
                        "dead": True,
                    })
                break

        all_runs.append(trajectory)

    # Compute confidence bands
    bands = _compute_bands(all_runs, projection_sols)

    # Build median-run narrative
    narratives = _build_narratives(all_runs, start_sol, projection_sols)

    # Survival statistics
    survival_count = sum(1 for run in all_runs if not run[-1]["dead"])
    death_sols = [
        next((e["sol"] for e in run if e["dead"]), None)
        for run in all_runs
    ]
    death_sols = [s for s in death_sols if s is not None]

    return {
        "start_sol": start_sol,
        "projection_sols": projection_sols,
        "num_runs": num_runs,
        "profile": profile,
        "event_frequencies": event_freqs,
        "extreme_events": extremes,
        "bands": bands,
        "survival_rate": round(survival_count / num_runs * 100, 1),
        "death_sol_median": round(statistics.median(death_sols)) if death_sols else None,
        "narratives": narratives,
    }


def _apply_extreme(colony: dict, extreme: dict):
    """Apply an extreme event's effects to colony state."""
    hab = colony["habitat"]
    crew = colony.get("crew", {})
    effects = extreme["effects"]

    if "solar_mult" in effects:
        hab["panel_dust_factor"] = max(0.1, hab["panel_dust_factor"] * effects["solar_mult"])
    if "panel_damage" in effects:
        hab["panel_dust_factor"] = max(0.1, hab["panel_dust_factor"] - effects["panel_damage"])
    if "food_impact" in effects:
        hab["food_reserves_kg"] = max(0, hab["food_reserves_kg"] * (1 + effects["food_impact"]))
    if "crew_health_hit" in effects:
        crew["health"] = max(0.1, crew.get("health", 1) - effects["crew_health_hit"])
    if "power_reduction" in effects:
        hab["stored_energy_kwh"] = max(0, hab["stored_energy_kwh"] * (1 - effects["power_reduction"]))

    colony["active_events"].append({
        "type": extreme["type"],
        "severity": extreme["severity"],
        "end_sol": colony["sol"] + extreme["duration_sols"],
    })

    colony["crew"] = crew


def _compute_bands(all_runs: list, projection_sols: int) -> list:
    """Compute per-sol p10/p50/p90 confidence bands across all runs."""
    bands = []
    fields = ["int_c", "stored_kwh", "food_kg", "morale", "health"]

    for sol_idx in range(projection_sols):
        sol_data = {}
        for field in fields:
            values = sorted(
                run[sol_idx][field] for run in all_runs if sol_idx < len(run)
            )
            if not values:
                continue
            n = len(values)
            sol_data[field] = {
                "p10": round(values[max(0, int(n * 0.1))], 2),
                "p50": round(values[n // 2], 2),
                "p90": round(values[min(n - 1, int(n * 0.9))], 2),
                "min": round(values[0], 2),
                "max": round(values[-1], 2),
            }

        # Survival probability at this sol
        alive = sum(1 for run in all_runs if sol_idx < len(run) and not run[sol_idx]["dead"])
        sol_data["survival_pct"] = round(alive / len(all_runs) * 100, 1)
        sol_data["sol"] = all_runs[0][sol_idx]["sol"] if all_runs and sol_idx < len(all_runs[0]) else sol_idx

        bands.append(sol_data)

    return bands


def _build_narratives(all_runs: list, start_sol: int, projection_sols: int) -> list:
    """Build human-readable narrative for the median (p50) trajectory."""
    narratives = []

    # Find the median run by total food at end
    end_foods = [run[-1]["food_kg"] for run in all_runs]
    median_idx = sorted(range(len(end_foods)), key=lambda i: end_foods[i])[len(end_foods) // 2]
    median_run = all_runs[median_idx]

    for entry in median_run:
        parts = [f"sol{entry['sol']}"]

        # Status
        t = entry["int_c"]
        if t > 15:
            parts.append("nominal")
        elif t > 0:
            parts.append("cool")
        elif t > -30:
            parts.append("cold")
        else:
            parts.append("critical")

        parts.append(f"{t:+.0f}c")
        parts.append(f"{entry['stored_kwh']:.0f}r")
        parts.append(f"{entry['food_kg']:.0f}f")

        # Morale
        m = entry.get("morale", 0)
        parts.append("happy" if m > 0.7 else "ok" if m > 0.4 else "stressed")

        # Events
        for ev in entry.get("events", []):
            parts.append(ev)

        if entry["dead"]:
            parts.append("DEAD")

        narratives.append(" ".join(parts))

    return narratives


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Mars Barn Colony Projection Engine")
    parser.add_argument("--sols", type=int, default=30, help="Sols to project forward")
    parser.add_argument("--runs", type=int, default=20, help="Monte Carlo runs")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    colony = load_colony()

    if not args.json:
        print(f"Projecting {colony['name']} from Sol {colony['sol']} → Sol {colony['sol'] + args.sols}...")
        print(f"  Monte Carlo runs: {args.runs}")
        print()

    result = project_forward(colony, args.sols, args.runs, args.seed)

    if args.json:
        print(json.dumps(result))
        return

    # Print historical profile
    print("═══ Historical Profile ═══")
    for field, stats in result["profile"].items():
        print(f"  {field:>12s}: mean={stats['mean']:>8.1f}  median={stats['median']:>8.1f}  "
              f"range=[{stats['min']:.1f}, {stats['max']:.1f}]  trend={stats['trend']:+.3f}/sol")

    # Event frequencies
    print(f"\n═══ Event Frequencies (from {colony['sol']} sols) ═══")
    for ev, info in sorted(result["event_frequencies"].items(), key=lambda x: -x[1]["frequency_per_sol"]):
        modeled = " (modeled)" if info.get("modeled") else ""
        print(f"  {ev:>25s}: {info['frequency_per_sol']:.4f}/sol  "
              f"(return period: {info['return_period_sols']:.0f} sols){modeled}")

    # Extreme events in this projection window
    if result["extreme_events"]:
        print(f"\n═══ Extreme Events Sampled ═══")
        for ext in result["extreme_events"]:
            print(f"  Sol +{ext['sol_offset']:>3d}: {ext['type']} "
                  f"(severity {ext['severity']:.0%}, {ext['duration_sols']} sols) — {ext['description']}")
    else:
        print(f"\n  No extreme events in this {args.sols}-sol window.")

    # Projection bands
    print(f"\n═══ Projection (p10 / p50 / p90) ═══")
    print(f"  Survival rate: {result['survival_rate']}%")
    if result["death_sol_median"]:
        print(f"  Median death sol: {result['death_sol_median']}")
    print()
    print(f"  {'Sol':>5s} | {'Temp °C':>18s} | {'Energy kWh':>18s} | {'Food kg':>18s} | {'Morale':>18s} | {'Alive':>6s}")
    print(f"  {'─' * 5} | {'─' * 18} | {'─' * 18} | {'─' * 18} | {'─' * 18} | {'─' * 6}")

    # Print every 5th sol + last
    for i, band in enumerate(result["bands"]):
        if i % 5 != 0 and i != len(result["bands"]) - 1:
            continue
        t = band.get("int_c", {})
        e = band.get("stored_kwh", {})
        f = band.get("food_kg", {})
        m = band.get("morale", {})
        print(f"  {band['sol']:>5d} | "
              f"{t.get('p10', 0):>+5.1f} / {t.get('p50', 0):>+5.1f} / {t.get('p90', 0):>+5.1f} | "
              f"{e.get('p10', 0):>5.0f} / {e.get('p50', 0):>5.0f} / {e.get('p90', 0):>5.0f} | "
              f"{f.get('p10', 0):>5.1f} / {f.get('p50', 0):>5.1f} / {f.get('p90', 0):>5.1f} | "
              f"{m.get('p10', 0):>4.2f} / {m.get('p50', 0):>4.2f} / {m.get('p90', 0):>4.2f} | "
              f"{band['survival_pct']:>5.1f}%")

    # Narratives (median run)
    print(f"\n═══ Median Run Narrative ═══")
    for n in result["narratives"][:10]:
        print(f"  {n}")
    if len(result["narratives"]) > 10:
        print(f"  ... ({len(result['narratives']) - 10} more sols)")


if __name__ == "__main__":
    main()
