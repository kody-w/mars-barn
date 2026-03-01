#!/usr/bin/env python3
"""Mars Barn — Colony Log Narrative Generator

Generates a corpus of colony log narratives from simulation runs
for training the colony microGPT. Each document is a short text
description of one sol's events.

Usage:
    python src/gen_corpus.py            # generate corpus to state/corpus.txt
    python src/gen_corpus.py --sols 200 # more sols = more training data
"""
import sys
import os
import random
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from live import default_colony, tick_sol


def sol_to_narrative(entry: dict, colony: dict) -> str:
    """Convert a sol log entry into a natural text narrative."""
    parts = []
    temp_c = entry["int_c"]

    # Status
    if temp_c > 15:
        status = "nominal"
    elif temp_c > 0:
        status = "cool"
    elif temp_c > -30:
        status = "cold"
    else:
        status = "critical"

    # Status line (compact for training)
    parts.append(f"sol{entry['sol']}")
    parts.append(status)
    parts.append(f"{temp_c:+.0f}c")
    parts.append(f"{entry['solar_kwh']:.0f}kw")
    parts.append(f"{entry['stored_kwh']:.0f}r")

    # Morale/health if present
    if "morale" in entry:
        m = entry["morale"]
        parts.append("happy" if m > 0.7 else "ok" if m > 0.4 else "stressed")
    if "health" in entry:
        h = entry["health"]
        if h < 0.7:
            parts.append("sick")

    for ev in entry["events"]:
        if ev != "dust_devil":
            parts.append(ev)

    return " ".join(parts)


def generate_corpus(num_colonies: int = 10, sols_per_colony: int = 100, seed: int = 42) -> list:
    """Generate a corpus of colony log narratives."""
    docs = []
    for c in range(num_colonies):
        random.seed(seed + c * 1000)
        colony = default_colony()
        colony["name"] = f"Colony-{c}"

        # Randomize starting params for diversity
        colony["habitat"]["solar_panel_area_m2"] = random.choice([200, 300, 400, 500])
        colony["habitat"]["insulation_r_value"] = random.choice([6, 8, 10, 12, 15])
        colony["habitat"]["heater_power_w"] = random.choice([4000, 6000, 8000, 10000])
        colony["habitat"]["crew_size"] = random.choice([2, 4, 6])

        for sol in range(1, sols_per_colony + 1):
            entry = tick_sol(colony, sol)
            narrative = sol_to_narrative(entry, colony)
            docs.append(narrative)

    return docs


def main():
    parser = argparse.ArgumentParser(description="Generate colony log corpus")
    parser.add_argument("--colonies", type=int, default=10)
    parser.add_argument("--sols", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default=os.path.join(os.path.dirname(__file__), "..", "state", "corpus.txt"))
    args = parser.parse_args()

    print(f"Generating corpus: {args.colonies} colonies × {args.sols} sols...")
    docs = generate_corpus(args.colonies, args.sols, args.seed)
    print(f"Generated {len(docs)} documents")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write("\n".join(docs) + "\n")
    print(f"Written to {args.output}")


if __name__ == "__main__":
    main()
