#!/usr/bin/env python3
"""Mars Barn — Fork Leaderboard Scraper

Scrapes the GitHub fork graph to build a decentralized leaderboard.
Each fork's colony.json is public — we read it, rank by survival metrics,
and produce a leaderboard without any central server.

This is the "Leaderboard Nobody Runs" pattern in action.

Usage:
    python src/leaderboard.py                      # scrape and rank
    python src/leaderboard.py --output state/leaderboard.json
"""
import json
import os
import sys
import argparse
import urllib.request
import urllib.error

OWNER = "kody-w"
REPO = "mars-barn"
GITHUB_API = "https://api.github.com"
RAW_URL = "https://raw.githubusercontent.com"


def fetch_json(url: str, token: str = None) -> dict:
    """Fetch JSON from URL with optional auth."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "mars-barn-leaderboard")
    if token:
        req.add_header("Authorization", f"token {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
        return {"error": str(e)}


def get_forks(owner: str = OWNER, repo: str = REPO, token: str = None) -> list:
    """Get all forks of the repo from GitHub API."""
    forks = []
    page = 1
    while True:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/forks?per_page=100&page={page}"
        data = fetch_json(url, token)
        if isinstance(data, dict) and "error" in data:
            print(f"  Warning: {data['error']}")
            break
        if not data:
            break
        forks.extend(data)
        if len(data) < 100:
            break
        page += 1
    return forks


def fetch_colony_state(owner: str, repo: str, branch: str = "main") -> dict:
    """Fetch a fork's colony.json from GitHub raw content."""
    url = f"{RAW_URL}/{owner}/{repo}/{branch}/state/colony.json"
    return fetch_json(url)


def score_colony(state: dict) -> dict:
    """Score a colony based on its state. Returns scoring breakdown."""
    if "error" in state or "sol" not in state:
        return {"total": 0, "gpa": 0.0, "grade": "N/A", "alive": False}

    sol = state.get("sol", 0)
    stats = state.get("stats", {})
    hab = state.get("habitat", {})

    temp_k = hab.get("interior_temp_k", 0)
    temp_c = temp_k - 273.15
    energy = hab.get("stored_energy_kwh", 0)
    food = hab.get("food_reserves_kg", 0)

    # Alive check
    alive = temp_c > -40 and energy > 0

    # Scoring (0-100 points)
    points = 0

    # Survival (0-40 points)
    points += min(40, sol * 0.5)  # 0.5 points per sol, max 40

    # Temperature comfort (0-20 points)
    if 15 < temp_c < 25:
        points += 20
    elif 0 < temp_c < 35:
        points += 10
    elif -30 < temp_c < 50:
        points += 5

    # Energy reserves (0-20 points)
    if energy > 1000:
        points += 20
    elif energy > 500:
        points += 15
    elif energy > 100:
        points += 10
    elif energy > 0:
        points += 5

    # Food (0-10 points)
    if food > 100:
        points += 10
    elif food > 50:
        points += 7
    elif food > 0:
        points += 3

    # Storm resilience (0-10 points)
    storms = stats.get("storms_survived", 0)
    points += min(10, storms * 0.5)

    # GPA (0.0-4.0 scale)
    gpa = round(points / 25, 1)  # 100 points = 4.0

    # Letter grade
    if gpa >= 3.7: grade = "A"
    elif gpa >= 3.3: grade = "A-"
    elif gpa >= 3.0: grade = "B+"
    elif gpa >= 2.7: grade = "B"
    elif gpa >= 2.3: grade = "B-"
    elif gpa >= 2.0: grade = "C+"
    elif gpa >= 1.7: grade = "C"
    elif gpa >= 1.0: grade = "D"
    else: grade = "F"

    return {
        "total": round(points, 1),
        "gpa": gpa,
        "grade": grade,
        "alive": alive,
        "sol": sol,
        "temp_c": round(temp_c, 1),
        "energy_kwh": round(energy, 1),
        "food_kg": round(food, 1),
        "storms": storms,
    }


def build_leaderboard(forks: list, include_origin: bool = True, token: str = None) -> list:
    """Build leaderboard from fork data."""
    entries = []

    # Include the origin repo
    if include_origin:
        print(f"  Fetching {OWNER}/{REPO} (origin)...")
        state = fetch_colony_state(OWNER, REPO)
        score = score_colony(state)
        entries.append({
            "owner": OWNER,
            "repo": REPO,
            "fork": False,
            "url": f"https://github.com/{OWNER}/{REPO}",
            "colony_name": state.get("name", "Unknown"),
            "location": state.get("location", {}).get("name", "Unknown"),
            **score,
        })

    # Fetch each fork's state
    for fork in forks:
        fork_owner = fork.get("owner", {}).get("login", "unknown")
        fork_repo = fork.get("name", REPO)
        branch = fork.get("default_branch", "main")
        print(f"  Fetching {fork_owner}/{fork_repo}...")

        state = fetch_colony_state(fork_owner, fork_repo, branch)
        score = score_colony(state)
        entries.append({
            "owner": fork_owner,
            "repo": fork_repo,
            "fork": True,
            "url": fork.get("html_url", ""),
            "colony_name": state.get("name", "Unknown") if "error" not in state else "N/A",
            "location": state.get("location", {}).get("name", "Unknown") if "error" not in state else "N/A",
            **score,
        })

    # Sort by GPA descending
    entries.sort(key=lambda e: (-e["gpa"], -e.get("sol", 0)))

    return entries


def print_leaderboard(entries: list):
    """Print a formatted leaderboard."""
    print()
    print("=" * 78)
    print("  MARS BARN — FEDERATION LEADERBOARD")
    print("  Decentralized ranking from public fork data")
    print("=" * 78)
    print()
    print(f"  {'#':>3s}  {'Colony':<25s} {'Owner':<18s} {'GPA':>4s} {'Grade':>5s} {'Sol':>5s} {'Status':>8s}")
    print(f"  {'─'*3}  {'─'*25} {'─'*18} {'─'*4} {'─'*5} {'─'*5} {'─'*8}")

    for i, e in enumerate(entries):
        status = "🟢 ALIVE" if e.get("alive") else "🔴 DEAD" if e.get("sol", 0) > 0 else "⚪ N/A"
        origin = " ⭐" if not e.get("fork") else ""
        print(f"  {i+1:>3d}  {e['colony_name']:<25s} {e['owner']:<18s} "
              f"{e['gpa']:>4.1f} {e['grade']:>5s} {e.get('sol', 0):>5d} {status}{origin}")

    print()
    print(f"  Total entries: {len(entries)}")
    alive = sum(1 for e in entries if e.get("alive"))
    print(f"  Alive: {alive}/{len(entries)}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="Mars Barn Fork Leaderboard")
    parser.add_argument("--output", default=None)
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    args = parser.parse_args()

    print("Scanning fork graph...")
    forks = get_forks(token=args.token)
    print(f"Found {len(forks)} forks\n")

    print("Building leaderboard...")
    entries = build_leaderboard(forks, token=args.token)

    print_leaderboard(entries)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            json.dump({"entries": entries, "total_forks": len(forks)}, f, indent=2)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
