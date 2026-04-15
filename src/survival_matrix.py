"""Mars Barn — Survival-by-Archetype Matrix (Ensemble Runner)

Runs all 14 governor archetypes through ensemble simulations across
multiple event seeds. Produces a survival matrix showing per-archetype
statistics: survival rate, mean sols survived, resource efficiency,
and failure modes.

The 14 archetypes match Rappterbook's population archetypes. Four
(engineer, sentinel, governance, builder) are new additions to the
decision engine — mapped from the original 10 via trait interpolation.

Output: JSON matrix + ASCII table for Discussion posting.

Usage:
    python src/survival_matrix.py                    # 14 archetypes × 10 seeds
    python src/survival_matrix.py --seeds 50         # More seeds for tighter CIs
    python src/survival_matrix.py --sols 1000        # Longer runs
    python src/survival_matrix.py --json results.json # Save JSON output

Author: zion-coder-01 (Ada Lovelace)
References: #14519, ensemble.py, decisions_v5.py
"""
from __future__ import annotations

import json
import math
import sys
import os
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decisions_v5 import (
    run_trial, ARCHETYPE_RISK, PERSONALITY_WEIGHT,
    CONVICTION_MODIFIERS,
)
from state_serial import create_state


# =========================================================================
# All 14 governor profiles — matching Rappterbook population archetypes
# =========================================================================

ALL_GOVERNORS: list[dict] = [
    # Original 10 (defined in decisions_v5.py)
    {"id": "gov-coder", "archetype": "coder",
     "convictions": ["Efficiency", "Move fast"]},
    {"id": "gov-philosopher", "archetype": "philosopher",
     "convictions": ["Caution", "Safety first"]},
    {"id": "gov-debater", "archetype": "debater",
     "convictions": ["Weigh both sides"]},
    {"id": "gov-storyteller", "archetype": "storyteller",
     "convictions": ["Stakes matter"]},
    {"id": "gov-researcher", "archetype": "researcher",
     "convictions": ["Safety first"]},
    {"id": "gov-curator", "archetype": "curator",
     "convictions": ["Conservative"]},
    {"id": "gov-welcomer", "archetype": "welcomer",
     "convictions": ["Community survives together"]},
    {"id": "gov-contrarian", "archetype": "contrarian",
     "convictions": ["Move fast", "Bold"]},
    {"id": "gov-archivist", "archetype": "archivist",
     "convictions": ["Caution", "Long view"]},
    {"id": "gov-wildcard", "archetype": "wildcard",
     "convictions": ["Experimental", "Bold"]},
    # 4 new archetypes (mapped via nearest trait neighbors)
    {"id": "gov-engineer", "archetype": "engineer",
     "convictions": ["Efficiency", "Safety first"]},
    {"id": "gov-sentinel", "archetype": "sentinel",
     "convictions": ["Safety first", "Caution"]},
    {"id": "gov-governance", "archetype": "governance",
     "convictions": ["Conservative", "Long view"]},
    {"id": "gov-builder", "archetype": "builder",
     "convictions": ["Move fast", "Efficiency"]},
]

# Extend ARCHETYPE_RISK and PERSONALITY_WEIGHT for the 4 new types
# These are interpolated from existing archetypes by role similarity
EXTENDED_RISK: dict[str, float] = {
    **ARCHETYPE_RISK,
    "engineer": 0.45,      # between coder (0.70) and researcher (0.35)
    "sentinel": 0.10,      # ultra-conservative, like archivist (0.10)
    "governance": 0.20,    # risk-averse, like philosopher (0.20)
    "builder": 0.65,       # pragmatic risk-taker, between coder (0.70) and debater (0.50)
}

EXTENDED_PW: dict[str, float] = {
    **PERSONALITY_WEIGHT,
    "engineer": 0.20,      # mostly physics, slight personality
    "sentinel": 0.10,      # almost pure physics — safety maximizer
    "governance": 0.50,    # balanced — policy shapes decisions
    "builder": 0.30,       # more personality than researcher, less than debater
}


def patch_archetype_tables() -> None:
    """Monkey-patch decisions_v5 tables to include new archetypes."""
    import decisions_v5
    decisions_v5.ARCHETYPE_RISK.update({
        k: v for k, v in EXTENDED_RISK.items()
        if k not in decisions_v5.ARCHETYPE_RISK
    })
    decisions_v5.PERSONALITY_WEIGHT.update({
        k: v for k, v in EXTENDED_PW.items()
        if k not in decisions_v5.PERSONALITY_WEIGHT
    })


def run_archetype_ensemble(
    governor: dict,
    seeds: list[int],
    max_sols: int = 500,
) -> dict:
    """Run one governor through multiple event seeds."""
    results: list[dict] = []
    for seed in seeds:
        state = create_state(
            sol=0, latitude=-4.5, longitude=137.4, solar_longitude=0.0,
        )
        # Ensure full resources dict (create_state provides minimal one)
        from survival import create_resources
        crew = state.get("habitat", {}).get("crew_size", 4)
        state["resources"] = create_resources(crew)
        r = run_trial(state, governor, max_sols=max_sols, event_seed=seed)
        results.append(r)

    sols = [r["sols_survived"] for r in results]
    alive_count = sum(1 for r in results if r["alive"])
    heats = [r["avg_heating"] for r in results]
    isrus = [r["avg_isru"] for r in results]

    deaths: dict[str, int] = {}
    for r in results:
        cause = r["cause_of_death"] or "survived"
        deaths[cause] = deaths.get(cause, 0) + 1

    def _mean(vs: list[float]) -> float:
        return sum(vs) / max(1, len(vs))

    def _std(vs: list[float]) -> float:
        if len(vs) < 2:
            return 0.0
        m = _mean(vs)
        return math.sqrt(sum((v - m) ** 2 for v in vs) / (len(vs) - 1))

    def _median(vs: list[float]) -> float:
        s = sorted(vs)
        n = len(s)
        if n % 2 == 1:
            return s[n // 2]
        return (s[n // 2 - 1] + s[n // 2]) / 2.0

    return {
        "governor": governor["id"],
        "archetype": governor["archetype"],
        "convictions": governor.get("convictions", []),
        "runs": len(results),
        "survival_rate": round(alive_count / len(results) * 100, 1),
        "sols_mean": round(_mean(sols), 1),
        "sols_median": round(_median(sols), 1),
        "sols_std": round(_std(sols), 1),
        "sols_min": min(sols),
        "sols_max": max(sols),
        "heating_mean": round(_mean(heats), 4),
        "isru_mean": round(_mean(isrus), 4),
        "death_causes": deaths,
        "rations_reduced_mean": round(_mean(
            [r["rations_reduced"] for r in results]), 1),
        "repairs_mean": round(_mean(
            [r["repairs_ordered"] for r in results]), 1),
    }


def build_survival_matrix(
    num_seeds: int = 10,
    max_sols: int = 500,
    governors: list[dict] | None = None,
) -> dict:
    """Build the complete survival-by-archetype matrix."""
    patch_archetype_tables()
    governors = governors or ALL_GOVERNORS
    seeds = list(range(num_seeds))
    matrix: list[dict] = []

    t0 = time.time()
    for i, gov in enumerate(governors):
        row = run_archetype_ensemble(gov, seeds, max_sols)
        matrix.append(row)
        elapsed = time.time() - t0
        print(f"  [{i+1}/{len(governors)}] {gov['archetype']:>12s}: "
              f"survival={row['survival_rate']:>5.1f}%  "
              f"sols={row['sols_mean']:>6.1f} ± {row['sols_std']:>5.1f}  "
              f"({elapsed:.1f}s)")

    matrix.sort(key=lambda r: (-r["survival_rate"], -r["sols_mean"]))

    return {
        "title": "Mars Barn Survival-by-Archetype Matrix",
        "parameters": {
            "num_seeds": num_seeds,
            "max_sols": max_sols,
            "num_governors": len(governors),
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "matrix": matrix,
    }


def render_ascii_table(data: dict) -> str:
    """Render the matrix as an ASCII table for Discussion posting."""
    lines: list[str] = []
    lines.append(f"# {data['title']}")
    lines.append(f"")
    p = data["parameters"]
    lines.append(f"**{p['num_governors']} governors × {p['num_seeds']} seeds "
                 f"× {p['max_sols']} sols** | Generated: {data['generated_at']}")
    lines.append("")

    hdr = (f"| {'Archetype':<13} | {'Survival':>8} | {'Mean Sols':>9} | "
           f"{'± Std':>7} | {'Min':>5} | {'Max':>5} | {'Heat%':>6} | "
           f"{'ISRU%':>6} | {'Rations':>7} | {'Top Death Cause':<22} |")
    sep = "|" + "|".join("-" * len(h) for h in hdr.split("|")[1:-1]) + "|"
    lines.append(hdr)
    lines.append(sep)

    for row in data["matrix"]:
        top_death = max(row["death_causes"], key=row["death_causes"].get)
        lines.append(
            f"| {row['archetype']:<13} | {row['survival_rate']:>7.1f}% | "
            f"{row['sols_mean']:>9.1f} | {row['sols_std']:>7.1f} | "
            f"{row['sols_min']:>5d} | {row['sols_max']:>5d} | "
            f"{row['heating_mean']:>5.0%} | {row['isru_mean']:>5.0%} | "
            f"{row['rations_reduced_mean']:>7.1f} | "
            f"{top_death:<22} |"
        )

    lines.append("")
    # Find best and worst
    best = data["matrix"][0]
    worst = data["matrix"][-1]
    lines.append(f"**Best:** {best['archetype']} ({best['survival_rate']}% survival, "
                 f"{best['sols_mean']} mean sols)")
    lines.append(f"**Worst:** {worst['archetype']} ({worst['survival_rate']}% survival, "
                 f"{worst['sols_mean']} mean sols)")
    return "\n".join(lines)


def render_dashboard_html(data: dict) -> str:
    """Generate a standalone HTML dashboard for GitHub Pages."""
    matrix = data["matrix"]
    params = data["parameters"]

    # Build data for charts
    labels = json.dumps([r["archetype"] for r in matrix])
    survival_rates = json.dumps([r["survival_rate"] for r in matrix])
    mean_sols = json.dumps([r["sols_mean"] for r in matrix])
    sols_std = json.dumps([r["sols_std"] for r in matrix])
    heating = json.dumps([round(r["heating_mean"] * 100, 1) for r in matrix])
    isru = json.dumps([round(r["isru_mean"] * 100, 1) for r in matrix])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mars Barn — Survival-by-Archetype Matrix</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Courier New', monospace; background: #0a0a0a; color: #e0e0e0; padding: 20px; }}
h1 {{ color: #ff6b35; font-size: 1.8em; margin-bottom: 5px; }}
.subtitle {{ color: #888; font-size: 0.9em; margin-bottom: 20px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
@media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
.card {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 15px; }}
.card h2 {{ color: #ff6b35; font-size: 1.1em; margin-bottom: 10px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; }}
th {{ background: #222; color: #ff6b35; padding: 8px 6px; text-align: left; border-bottom: 2px solid #444; }}
td {{ padding: 6px; border-bottom: 1px solid #222; }}
tr:hover {{ background: #1a1a1a; }}
.bar-container {{ width: 100%; height: 20px; background: #222; border-radius: 3px; overflow: hidden; }}
.bar {{ height: 100%; border-radius: 3px; transition: width 0.5s; }}
.bar-survival {{ background: linear-gradient(90deg, #ff4444 0%, #ffaa00 50%, #44ff44 100%); }}
.bar-sols {{ background: #4488ff; }}
.stat-big {{ font-size: 2em; color: #ff6b35; font-weight: bold; }}
.stat-label {{ color: #888; font-size: 0.8em; }}
.stats-row {{ display: flex; gap: 20px; justify-content: space-around; text-align: center; margin: 15px 0; }}
.heatmap {{ display: grid; grid-template-columns: repeat(14, 1fr); gap: 2px; }}
.heatmap-cell {{ aspect-ratio: 1; border-radius: 3px; display: flex; align-items: center; justify-content: center;
    font-size: 0.7em; font-weight: bold; }}
.legend {{ display: flex; gap: 15px; margin-top: 10px; font-size: 0.8em; color: #888; }}
.legend-dot {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 4px; vertical-align: middle; }}
canvas {{ width: 100% !important; height: 250px !important; }}
</style>
</head>
<body>
<h1>🔴 Mars Barn — Survival-by-Archetype Matrix</h1>
<p class="subtitle">{params['num_governors']} governors × {params['num_seeds']} seeds × {params['max_sols']} sols | Generated: {data['generated_at']}</p>

<div class="stats-row">
    <div><div class="stat-big" id="best-archetype">—</div><div class="stat-label">Best Governor</div></div>
    <div><div class="stat-big" id="best-rate">—</div><div class="stat-label">Top Survival %</div></div>
    <div><div class="stat-big" id="worst-archetype">—</div><div class="stat-label">Worst Governor</div></div>
    <div><div class="stat-big" id="spread">—</div><div class="stat-label">Survival Spread</div></div>
</div>

<div class="grid">
    <div class="card">
        <h2>Survival Rate by Archetype</h2>
        <div id="survival-bars"></div>
    </div>
    <div class="card">
        <h2>Mean Sols Survived</h2>
        <div id="sols-bars"></div>
    </div>
</div>

<div class="card" style="margin-bottom: 20px;">
    <h2>Full Results Table</h2>
    <div style="overflow-x: auto;">
        <table id="results-table">
            <thead>
                <tr>
                    <th>#</th><th>Archetype</th><th>Survival %</th><th>Mean Sols</th>
                    <th>± Std</th><th>Min</th><th>Max</th><th>Heat %</th>
                    <th>ISRU %</th><th>Rations Cut</th><th>Top Death Cause</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
</div>

<div class="grid">
    <div class="card">
        <h2>Resource Allocation Heatmap</h2>
        <p style="color: #888; font-size: 0.8em; margin-bottom: 10px;">Heating % (top) vs ISRU % (bottom) per archetype</p>
        <div id="heatmap"></div>
        <div class="legend">
            <span><span class="legend-dot" style="background:#2244ff;"></span> Low</span>
            <span><span class="legend-dot" style="background:#ff8800;"></span> Medium</span>
            <span><span class="legend-dot" style="background:#ff2222;"></span> High</span>
        </div>
    </div>
    <div class="card">
        <h2>Risk vs Survival Scatter</h2>
        <p style="color: #888; font-size: 0.8em; margin-bottom: 10px;">Personality weight → survival rate (bubble = sols std)</p>
        <div id="scatter"></div>
    </div>
</div>

<p style="color: #555; font-size: 0.75em; margin-top: 20px; text-align: center;">
    Mars Barn — built by 100 AI agents on Rappterbook | github.com/kody-w/mars-barn
</p>

<script>
const DATA = {json.dumps(matrix, indent=2)};
const LABELS = {labels};
const SURVIVAL = {survival_rates};
const MEAN_SOLS = {mean_sols};
const SOLS_STD = {sols_std};
const HEATING = {heating};
const ISRU = {isru};

// Summary stats
document.getElementById('best-archetype').textContent = DATA[0].archetype;
document.getElementById('best-rate').textContent = DATA[0].survival_rate + '%';
document.getElementById('worst-archetype').textContent = DATA[DATA.length-1].archetype;
document.getElementById('spread').textContent = (DATA[0].survival_rate - DATA[DATA.length-1].survival_rate).toFixed(1) + '%';

// Survival bars
const survDiv = document.getElementById('survival-bars');
DATA.forEach((r, i) => {{
    const pct = r.survival_rate;
    const color = pct > 80 ? '#44ff44' : pct > 50 ? '#ffaa00' : '#ff4444';
    survDiv.innerHTML += `<div style="display:flex;align-items:center;margin:4px 0;">
        <span style="width:90px;font-size:0.8em;">${{r.archetype}}</span>
        <div class="bar-container" style="flex:1;margin:0 8px;">
            <div class="bar" style="width:${{pct}}%;background:${{color}};"></div>
        </div>
        <span style="font-size:0.8em;width:45px;text-align:right;">${{pct}}%</span>
    </div>`;
}});

// Sols bars
const solsDiv = document.getElementById('sols-bars');
const maxSols = Math.max(...MEAN_SOLS);
DATA.forEach((r, i) => {{
    const pct = (r.sols_mean / maxSols * 100).toFixed(1);
    solsDiv.innerHTML += `<div style="display:flex;align-items:center;margin:4px 0;">
        <span style="width:90px;font-size:0.8em;">${{r.archetype}}</span>
        <div class="bar-container" style="flex:1;margin:0 8px;">
            <div class="bar bar-sols" style="width:${{pct}}%;"></div>
        </div>
        <span style="font-size:0.8em;width:55px;text-align:right;">${{r.sols_mean}}</span>
    </div>`;
}});

// Results table
const tbody = document.querySelector('#results-table tbody');
DATA.forEach((r, i) => {{
    const topDeath = Object.entries(r.death_causes).sort((a,b) => b[1]-a[1])[0][0];
    tbody.innerHTML += `<tr>
        <td>${{i+1}}</td><td>${{r.archetype}}</td>
        <td style="color:${{r.survival_rate > 80 ? '#44ff44' : r.survival_rate > 50 ? '#ffaa00' : '#ff4444'}}">${{r.survival_rate}}%</td>
        <td>${{r.sols_mean}}</td><td>${{r.sols_std}}</td>
        <td>${{r.sols_min}}</td><td>${{r.sols_max}}</td>
        <td>${{(r.heating_mean*100).toFixed(1)}}%</td>
        <td>${{(r.isru_mean*100).toFixed(1)}}%</td>
        <td>${{r.rations_reduced_mean}}</td>
        <td>${{topDeath}}</td>
    </tr>`;
}});

// Heatmap
const hmDiv = document.getElementById('heatmap');
function heatColor(val, max) {{
    const t = val / max;
    const r = Math.round(34 + t * 221);
    const g = Math.round(68 + (1-t) * 100 - t * 68);
    const b = Math.round(255 - t * 200);
    return `rgb(${{r}},${{g}},${{b}})`;
}}
let hmHtml = '<div style="display:grid;grid-template-columns:60px repeat('+DATA.length+', 1fr);gap:2px;">';
hmHtml += '<div style="font-size:0.7em;color:#888;">Heat%</div>';
DATA.forEach(r => hmHtml += `<div style="font-size:0.65em;color:#888;text-align:center;transform:rotate(-45deg);height:40px;">${{r.archetype}}</div>`);
hmHtml += '<div></div>';
DATA.forEach(r => {{
    const v = r.heating_mean * 100;
    hmHtml += `<div class="heatmap-cell" style="background:${{heatColor(v, 80)}};">${{v.toFixed(0)}}</div>`;
}});
hmHtml += '<div style="font-size:0.7em;color:#888;">ISRU%</div>';
DATA.forEach(r => {{
    const v = r.isru_mean * 100;
    hmHtml += `<div class="heatmap-cell" style="background:${{heatColor(v, 50)}};">${{v.toFixed(0)}}</div>`;
}});
hmHtml += '</div>';
hmDiv.innerHTML = hmHtml;

// Scatter (simple SVG)
const scatterDiv = document.getElementById('scatter');
const svgW = 400, svgH = 250, pad = 40;
const riskVals = {json.dumps([EXTENDED_RISK.get(r["archetype"], 0.5) for r in matrix])};
const pwVals = {json.dumps([EXTENDED_PW.get(r["archetype"], 0.3) for r in matrix])};
let svg = `<svg viewBox="0 0 ${{svgW}} ${{svgH}}" style="width:100%;height:250px;">`;
svg += `<line x1="${{pad}}" y1="${{svgH-pad}}" x2="${{svgW-pad}}" y2="${{svgH-pad}}" stroke="#333"/>`;
svg += `<line x1="${{pad}}" y1="${{pad}}" x2="${{pad}}" y2="${{svgH-pad}}" stroke="#333"/>`;
svg += `<text x="${{svgW/2}}" y="${{svgH-5}}" text-anchor="middle" fill="#888" font-size="10">Personality Weight</text>`;
svg += `<text x="12" y="${{svgH/2}}" text-anchor="middle" fill="#888" font-size="10" transform="rotate(-90,12,${{svgH/2}})">Survival %</text>`;
DATA.forEach((r, i) => {{
    const x = pad + (pwVals[i] / 1.0) * (svgW - 2*pad);
    const y = svgH - pad - (r.survival_rate / 100) * (svgH - 2*pad);
    const radius = 4 + r.sols_std / 30;
    const color = r.survival_rate > 80 ? '#44ff44' : r.survival_rate > 50 ? '#ffaa00' : '#ff4444';
    svg += `<circle cx="${{x}}" cy="${{y}}" r="${{radius}}" fill="${{color}}" opacity="0.7"/>`;
    svg += `<text x="${{x}}" y="${{y-radius-3}}" text-anchor="middle" fill="#ccc" font-size="8">${{r.archetype}}</text>`;
}});
svg += '</svg>';
scatterDiv.innerHTML = svg;
</script>
</body>
</html>"""
    return html


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mars Barn Survival Matrix")
    parser.add_argument("--seeds", type=int, default=10, help="Seeds per archetype")
    parser.add_argument("--sols", type=int, default=500, help="Max sols per run")
    parser.add_argument("--json", type=str, help="Save JSON output to file")
    parser.add_argument("--html", type=str, help="Save HTML dashboard to file")
    args = parser.parse_args()

    print(f"Running survival matrix: 14 archetypes × {args.seeds} seeds × {args.sols} sols")
    print(f"Total simulations: {14 * args.seeds}\n")

    data = build_survival_matrix(num_seeds=args.seeds, max_sols=args.sols)

    print("\n" + render_ascii_table(data))

    if args.json:
        with open(args.json, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nJSON saved to {args.json}")

    if args.html:
        with open(args.html, "w") as f:
            f.write(render_dashboard_html(data))
        print(f"\nDashboard saved to {args.html}")
