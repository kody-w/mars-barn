#!/usr/bin/env python3
"""test_two_thresholds.py — Run tick_engine for 365 sols, track population curve.

Tests the two life/death thresholds in tick_engine.py:
  1. Battery depletion (batt < 0) → colony DEAD
  2. Digital twin maturity (age > 365 sols) → DIGITAL_TWIN

Runs 6 colonies (3 healthy, 3 marginal) through 400 sols of Mars physics,
records population each sol, outputs an HTML chart for GitHub Pages.

Author: zion-coder-03 (seed execution, frame 358)
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import LIFE_SUPPORT_BASE_KWH_PER_SOL
from solar import daily_energy
from thermal import simulate_sol
from mars_climate import dust_storm_stats

# --- tick_engine constants ---
SOLAR_LONGITUDE_ADVANCE = 0.5
SUPPLY_DROP_PROBABILITY = 0.10
BASE_LIFE_SUPPORT_KWH = LIFE_SUPPORT_BASE_KWH_PER_SOL
PANEL_ARRAY_SCALE = 10
DIGITAL_TWIN_THRESHOLD_SOLS = 365
DIGITAL_TWIN_PROBABILITY = 0.05


def get_mars_conditions(ls: float) -> dict:
    any_prob, regional_prob, global_prob, mean_sev, max_sev = dust_storm_stats(ls)
    return {
        "dust_any_prob": any_prob,
        "dust_regional_prob": regional_prob,
        "dust_global_prob": global_prob,
        "dust_mean_severity": mean_sev,
        "dust_max_severity": max_sev,
        "solar_longitude": ls,
    }


def resolve_weather(conditions: dict) -> tuple:
    dust_storm = random.random() < conditions["dust_any_prob"]
    global_storm = False
    if dust_storm and conditions["dust_any_prob"] > 0:
        global_storm = random.random() < (
            conditions["dust_global_prob"] / conditions["dust_any_prob"]
        )
    return dust_storm, global_storm


def make_colony(name: str, battery: float, solar_eff: float, r_val: float,
                panel_scale: float = PANEL_ARRAY_SCALE) -> dict:
    return {
        "name": name,
        "status": "ALIVE",
        "age_sols": 0,
        "last_event": "",
        "panel_scale": panel_scale,
        "stats": {
            "battery_reserves_kwh": battery,
            "supply_reserves_tons": 200.0,
            "solar_efficiency": solar_eff,
            "thermal_insulation": r_val,
        },
    }


def tick_colony(colony: dict, current_ls: float, dust_storm: bool) -> dict:
    if colony.get("status") != "ALIVE":
        return colony

    stats = colony["stats"]
    batt = stats["battery_reserves_kwh"]
    supplies = stats["supply_reserves_tons"]
    solar_eff = stats["solar_efficiency"]
    r_val = stats["thermal_insulation"]
    scale = colony.get("panel_scale", PANEL_ARRAY_SCALE)

    supply_drop = random.random() < SUPPLY_DROP_PROBABILITY
    if supply_drop and not dust_storm:
        supplies += 50.0

    energy_res = daily_energy(
        solar_longitude=current_ls,
        dust_storm=dust_storm,
        solar_multiplier=solar_eff,
    )
    generated_kwh = energy_res["total_kwh"] * scale

    thermal_res = simulate_sol(
        solar_longitude=current_ls,
        r_value=r_val,
        dust_storm=dust_storm,
        rtg_power_w=0.0,
    )
    heating_kwh = thermal_res["heating_kwh"]
    total_consumed = heating_kwh + BASE_LIFE_SUPPORT_KWH

    batt += generated_kwh - total_consumed

    if batt < 0:
        colony["status"] = "DEAD"
        colony["last_event"] = f"Battery depleted on Sol {colony['age_sols'] + 1}."
        batt = 0.0
    elif colony["age_sols"] > DIGITAL_TWIN_THRESHOLD_SOLS:
        if random.random() < DIGITAL_TWIN_PROBABILITY:
            colony["status"] = "DIGITAL_TWIN"
            colony["last_event"] = f"Ascended to digital twin on Sol {colony['age_sols'] + 1}."

    colony["age_sols"] = colony.get("age_sols", 0) + 1
    stats["battery_reserves_kwh"] = round(batt, 2)
    stats["supply_reserves_tons"] = round(supplies, 2)
    colony["stats"] = stats
    return colony


def run_simulation(n_sols: int = 400, seed: int = 42) -> dict:
    random.seed(seed)

    colonies = [
        # Healthy tier — should survive and maybe ascend
        make_colony("Olympus Base",    battery=500.0, solar_eff=1.0,  r_val=12.0, panel_scale=10),
        make_colony("Hellas Outpost",  battery=350.0, solar_eff=0.85, r_val=10.0, panel_scale=10),
        # Marginal tier — might die during dust season
        make_colony("Valles Station",  battery=200.0, solar_eff=0.5,  r_val=6.0,  panel_scale=3),
        make_colony("Acidalia Camp",   battery=150.0, solar_eff=0.4,  r_val=5.0,  panel_scale=2),
        # Fragile tier — likely to die early
        make_colony("Polar Shelter",   battery=100.0, solar_eff=0.3,  r_val=4.0,  panel_scale=1.5),
        make_colony("Dust Bowl",       battery=80.0,  solar_eff=0.25, r_val=3.0,  panel_scale=1),
    ]

    history = {
        "sols": [],
        "alive_count": [],
        "dead_count": [],
        "twin_count": [],
        "battery": {c["name"]: [] for c in colonies},
        "status": {c["name"]: [] for c in colonies},
        "events": [],
    }

    for sol in range(n_sols):
        base_ls = (sol * SOLAR_LONGITUDE_ADVANCE) % 360
        conditions = get_mars_conditions(base_ls)
        dust_storm, global_storm = resolve_weather(conditions)

        for c in colonies:
            tick_colony(c, base_ls, dust_storm)

        alive = sum(1 for c in colonies if c["status"] == "ALIVE")
        dead = sum(1 for c in colonies if c["status"] == "DEAD")
        twins = sum(1 for c in colonies if c["status"] == "DIGITAL_TWIN")

        history["sols"].append(sol)
        history["alive_count"].append(alive)
        history["dead_count"].append(dead)
        history["twin_count"].append(twins)

        for c in colonies:
            history["battery"][c["name"]].append(c["stats"]["battery_reserves_kwh"])
            history["status"][c["name"]].append(c["status"])

        if global_storm:
            history["events"].append({"sol": sol, "type": "GLOBAL", "ls": round(base_ls, 1)})
        elif dust_storm:
            history["events"].append({"sol": sol, "type": "REGIONAL", "ls": round(base_ls, 1)})

        for c in colonies:
            if c["last_event"] and ("depleted" in c["last_event"] or "Ascended" in c["last_event"]):
                history["events"].append({"sol": sol, "colony": c["name"], "event": c["last_event"]})
                c["last_event"] = ""

    return {
        "history": history,
        "final_states": [
            {"name": c["name"], "status": c["status"], "age_sols": c["age_sols"],
             "battery": c["stats"]["battery_reserves_kwh"]}
            for c in colonies
        ],
    }


def generate_html_chart(result: dict, output_path: str) -> None:
    h = result["history"]
    sols = h["sols"]
    alive = h["alive_count"]
    dead = h["dead_count"]
    twins = h["twin_count"]
    events = h["events"]
    finals = result["final_states"]
    battery_data = h["battery"]
    colony_names = list(battery_data.keys())

    death_events = [e for e in events if "depleted" in e.get("event", "")]
    twin_events = [e for e in events if "Ascended" in e.get("event", "")]
    storm_events = [e for e in events if e.get("type") == "GLOBAL"]
    n_sols = len(sols)

    key_events_html = []
    for e in sorted(events, key=lambda x: x["sol"]):
        if e.get("event"):
            cls = "death" if "depleted" in e["event"] else "twin"
            key_events_html.append(f'<div class="event-item {cls}">Sol {e["sol"]}: {e.get("colony","")} — {e["event"]}</div>')
        elif e.get("type") == "GLOBAL":
            key_events_html.append(f'<div class="event-item storm">Sol {e["sol"]}: GLOBAL dust storm at Ls {e["ls"]}°</div>')

    finals_html = "".join(
        f'<p><strong>{f["name"]}</strong>: '
        f'<span style="color:{"#2ecc71" if f["status"]=="ALIVE" else "#9b59b6" if f["status"]=="DIGITAL_TWIN" else "#e74c3c"}">'
        f'{f["status"]}</span> — {f["age_sols"]} sols, {f["battery"]:.0f} kWh</p>'
        for f in finals
    )

    battery_json = {name: vals for name, vals in battery_data.items()}
    colors = ['#ff6347', '#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6']

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mars Barn — Two Thresholds: Population Curve</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;padding:20px}}
h1{{color:#ff6347;text-align:center;margin-bottom:4px;font-size:1.6em}}
.sub{{text-align:center;color:#888;margin-bottom:20px;font-size:.9em}}
.charts{{max-width:1000px;margin:0 auto}}
canvas{{width:100%;background:#111;border-radius:8px;border:1px solid #222;margin-bottom:16px}}
.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px}}
.card{{background:#111;border:1px solid #222;border-radius:8px;padding:14px;text-align:center}}
.card .l{{color:#888;font-size:.75em;margin-bottom:2px}}
.card .v{{font-size:1.8em;font-weight:bold}}
.card .v.a{{color:#2ecc71}}.card .v.d{{color:#e74c3c}}.card .v.t{{color:#9b59b6}}.card .v.s{{color:#f39c12}}
.lg{{display:flex;justify-content:center;gap:16px;margin:10px 0;font-size:.8em;flex-wrap:wrap}}
.lg span{{display:flex;align-items:center;gap:5px}}
.lg .dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.box{{max-width:1000px;margin:16px auto;background:#111;border:1px solid #222;border-radius:8px;padding:16px}}
.box h3{{color:#ff6347;margin-bottom:8px;font-size:.95em}}
.box.m h3{{color:#7b68ee}}
.event-item{{padding:3px 0;font-size:.82em;border-bottom:1px solid #1a1a1a}}
.event-item.death{{color:#e74c3c}}.event-item.twin{{color:#9b59b6}}.event-item.storm{{color:#f39c12}}
.box p{{font-size:.85em;line-height:1.5;margin:4px 0}}
.box ul,.box ol{{margin:6px 0 6px 20px;font-size:.85em;line-height:1.5}}
.box code{{background:#1a1a2e;padding:1px 5px;border-radius:3px;font-size:.88em}}
footer{{text-align:center;color:#444;margin-top:30px;font-size:.75em}}
.threshold-line{{position:relative}}
</style>
</head>
<body>
<h1>🔴 Two Thresholds — {n_sols} Sols</h1>
<p class="sub">6 colonies × {n_sols} sols of Mars physics via tick_engine.py | seed=42</p>

<div class="summary">
  <div class="card"><div class="l">Survived</div><div class="v a">{alive[-1]}</div></div>
  <div class="card"><div class="l">Dead (battery=0)</div><div class="v d">{dead[-1]}</div></div>
  <div class="card"><div class="l">Digital Twins</div><div class="v t">{twins[-1]}</div></div>
  <div class="card"><div class="l">Global Storms</div><div class="v s">{len(storm_events)}</div></div>
  <div class="card"><div class="l">Regional Storms</div><div class="v s">{len([e for e in events if e.get("type")=="REGIONAL"])}</div></div>
</div>

<div class="charts">
  <h3 style="color:#7b68ee;text-align:center;margin-bottom:6px">Population Curve</h3>
  <div class="lg">
    <span><div class="dot" style="background:#2ecc71"></div> Alive</span>
    <span><div class="dot" style="background:#e74c3c"></div> Dead</span>
    <span><div class="dot" style="background:#9b59b6"></div> Digital Twin</span>
    <span><div class="dot" style="background:rgba(243,156,18,0.3)"></div> Global Storm</span>
  </div>
  <canvas id="popChart" height="220"></canvas>

  <h3 style="color:#7b68ee;text-align:center;margin-bottom:6px">Battery Reserves (kWh)</h3>
  <div class="lg">
    {"".join(f'<span><div class="dot" style="background:{colors[i]}"></div> {n}</span>' for i,n in enumerate(colony_names))}
  </div>
  <canvas id="battChart" height="280"></canvas>
</div>

<div class="box">
  <h3>⚡ Key Events</h3>
  {"".join(key_events_html) if key_events_html else '<div class="event-item">No threshold events triggered.</div>'}
</div>

<div class="box m">
  <h3>Final Colony States</h3>
  {finals_html}
</div>

<div class="box m">
  <h3>Method</h3>
  <p>Six colonies with varying resilience run through <code>tick_engine.py</code> physics:</p>
  <ul>
    <li><strong>Olympus Base</strong> — 500 kWh, 1.0× solar, R-12, 10× panels (robust)</li>
    <li><strong>Hellas Outpost</strong> — 350 kWh, 0.85× solar, R-10, 10× panels (healthy)</li>
    <li><strong>Valles Station</strong> — 200 kWh, 0.5× solar, R-6, 3× panels (marginal)</li>
    <li><strong>Acidalia Camp</strong> — 150 kWh, 0.4× solar, R-5, 2× panels (stressed)</li>
    <li><strong>Polar Shelter</strong> — 100 kWh, 0.3× solar, R-4, 1.5× panels (fragile)</li>
    <li><strong>Dust Bowl</strong> — 80 kWh, 0.25× solar, R-3, 1× panels (doomed?)</li>
  </ul>
  <p><strong>Threshold 1 (Death):</strong> battery &lt; 0 → DEAD<br>
  <strong>Threshold 2 (Ascension):</strong> age &gt; 365 sols + 5%/sol → DIGITAL_TWIN</p>
  <p>Full Mars climate: orbital eccentricity, dust storms, thermal regulation, seasonal CO₂ cycle.</p>
</div>

<footer>Generated by test_two_thresholds.py | tick_engine.py | Mars Barn | Frame 358</footer>

<script>
const sols={json.dumps(sols)};
const alive={json.dumps(alive)};
const dead={json.dumps(dead)};
const twins={json.dumps(twins)};
const batteries={json.dumps(battery_json)};
const deathEvts={json.dumps([e["sol"] for e in death_events])};
const twinEvts={json.dumps([e["sol"] for e in twin_events])};
const stormSols={json.dumps([e["sol"] for e in storm_events])};
const nSols={n_sols};

function draw(cid,datasets,yLab,annots){{
  const c=document.getElementById(cid),ctx=c.getContext('2d');
  const dpr=window.devicePixelRatio||1,r=c.getBoundingClientRect();
  c.width=r.width*dpr;c.height=r.height*dpr;ctx.scale(dpr,dpr);
  const W=r.width,H=r.height,p={{t:24,r:20,b:35,l:60}};
  const pW=W-p.l-p.r,pH=H-p.t-p.b;
  let yMin=Infinity,yMax=-Infinity;
  datasets.forEach(d=>d.data.forEach(v=>{{if(v<yMin)yMin=v;if(v>yMax)yMax=v}}));
  if(yMin===yMax){{yMin-=1;yMax+=1}};const yr=yMax-yMin;yMin-=yr*.05;yMax+=yr*.05;
  // Grid
  ctx.strokeStyle='#222';ctx.lineWidth=.5;
  for(let i=0;i<=5;i++){{
    const y=p.t+pH*(1-i/5);ctx.beginPath();ctx.moveTo(p.l,y);ctx.lineTo(W-p.r,y);ctx.stroke();
    ctx.fillStyle='#666';ctx.font='11px sans-serif';ctx.textAlign='right';
    ctx.fillText((yMin+(yMax-yMin)*i/5).toFixed(yMax>100?0:1),p.l-6,y+4);
  }}
  for(let s=0;s<=nSols;s+=50){{
    const x=p.l+(s/nSols)*pW;ctx.beginPath();ctx.moveTo(x,p.t);ctx.lineTo(x,p.t+pH);ctx.stroke();
    ctx.fillStyle='#666';ctx.font='11px sans-serif';ctx.textAlign='center';ctx.fillText(s,x,H-p.b+15);
  }}
  // 365-sol threshold line
  const tx=p.l+(365/nSols)*pW;
  ctx.strokeStyle='rgba(155,89,182,0.4)';ctx.lineWidth=1.5;ctx.setLineDash([6,4]);
  ctx.beginPath();ctx.moveTo(tx,p.t);ctx.lineTo(tx,p.t+pH);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#9b59b6';ctx.font='bold 10px sans-serif';ctx.textAlign='center';
  ctx.fillText('365 sol threshold',tx,p.t-6);
  // Storm bands
  stormSols.forEach(s=>{{const x=p.l+(s/nSols)*pW;ctx.fillStyle='rgba(243,156,18,0.12)';ctx.fillRect(x-2,p.t,5,pH)}});
  // Lines
  datasets.forEach(d=>{{
    ctx.strokeStyle=d.color;ctx.lineWidth=d.width||2;ctx.beginPath();
    d.data.forEach((v,i)=>{{const x=p.l+(i/(d.data.length-1))*pW,y=p.t+pH*(1-(v-yMin)/(yMax-yMin));i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)}});
    ctx.stroke();
  }});
  // Annotations
  if(annots)annots.forEach(a=>{{
    const x=p.l+(a.sol/nSols)*pW;ctx.strokeStyle=a.color;ctx.lineWidth=1.5;ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(x,p.t);ctx.lineTo(x,p.t+pH);ctx.stroke();ctx.setLineDash([]);
    ctx.fillStyle=a.color;ctx.font='bold 10px sans-serif';ctx.textAlign='center';ctx.fillText(a.label,x,p.t-6);
  }});
  ctx.save();ctx.translate(14,p.t+pH/2);ctx.rotate(-Math.PI/2);
  ctx.fillStyle='#888';ctx.font='12px sans-serif';ctx.textAlign='center';ctx.fillText(yLab,0,0);ctx.restore();
}}

window.addEventListener('load',()=>{{
  const an=[];
  deathEvts.forEach(s=>an.push({{sol:s,color:'#e74c3c',label:'☠️'}}));
  twinEvts.forEach(s=>an.push({{sol:s,color:'#9b59b6',label:'🧬'}}));
  draw('popChart',[
    {{data:alive,color:'#2ecc71',width:3}},
    {{data:dead,color:'#e74c3c',width:2}},
    {{data:twins,color:'#9b59b6',width:2}},
  ],'Colony Count',an);
  const names=Object.keys(batteries);
  const cols=['#ff6347','#3498db','#2ecc71','#f39c12','#e74c3c','#9b59b6'];
  draw('battChart',names.map((n,i)=>({{data:batteries[n],color:cols[i],width:1.5}})),'Battery (kWh)',an);
}});
window.addEventListener('resize',()=>location.reload());
</script>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)


if __name__ == "__main__":
    print("=== test_two_thresholds.py — 400 Sol Simulation ===")
    print("Running 6 colonies through tick_engine physics (seed=42)...")
    result = run_simulation(n_sols=400, seed=42)

    h = result["history"]
    print(f"\nFinal state at Sol 400:")
    for f in result["final_states"]:
        print(f"  {f['name']}: {f['status']} ({f['age_sols']} sols, {f['battery']:.0f} kWh)")

    alive_end = h["alive_count"][-1]
    dead_end = h["dead_count"][-1]
    twin_end = h["twin_count"][-1]
    storms_g = [e for e in h["events"] if e.get("type") == "GLOBAL"]
    storms_r = [e for e in h["events"] if e.get("type") == "REGIONAL"]
    deaths = [e for e in h["events"] if "depleted" in e.get("event", "")]
    ascensions = [e for e in h["events"] if "Ascended" in e.get("event", "")]

    print(f"\nPopulation: {alive_end} alive, {dead_end} dead, {twin_end} digital twins")
    print(f"Storms: {len(storms_g)} global, {len(storms_r)} regional")
    for d in deaths:
        print(f"  ☠️  {d['colony']}: {d['event']}")
    for a in ascensions:
        print(f"  🧬 {a['colony']}: {a['event']}")

    output = Path(__file__).parent.parent / "docs" / "two-thresholds.html"
    generate_html_chart(result, str(output))
    print(f"\nChart: {output}")
