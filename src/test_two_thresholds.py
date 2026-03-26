#!/usr/bin/env python3
"""test_two_thresholds.py — 10 colonies × 400 sols, two survival thresholds.

Threshold 1 (DEATH): battery_reserves_kwh < 0 → colony dies from energy deficit.
Threshold 2 (DIGITAL_TWIN): age_sols > 365 + 5% chance/sol → promoted.

The population curve reveals which colony configs cross which threshold.
"""
import os, sys, json, random
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tick_engine import tick_colony, get_mars_conditions, resolve_weather, SOLAR_LONGITUDE_ADVANCE

random.seed(42)
NUM_COLONIES, TOTAL_SOLS = 10, 400

def make(cid, se, rv, batt):
    return {"id": f"colony-{cid:02d}", "name": f"C{cid}", "status": "ALIVE", "age_sols": 0,
            "stats": {"battery_reserves_kwh": batt, "supply_reserves_tons": 200.0,
                      "solar_efficiency": se, "thermal_insulation": rv}, "last_event": "Init"}

# solar_eff breakeven ≈ 0.08. Below = death. Above = survival.
colonies = [
    make(0, se=0.02, rv=8.0,  batt=500.0),     # deep deficit, dies fast
    make(1, se=0.04, rv=10.0, batt=2000.0),     # deficit, dies ~sol 20
    make(2, se=0.05, rv=10.0, batt=5000.0),     # deficit, dies ~sol 50-80
    make(3, se=0.06, rv=11.0, batt=10000.0),    # slow bleed, dies ~sol 100-150
    make(4, se=0.07, rv=12.0, batt=15000.0),    # razor thin deficit, dies ~sol 200-300
    make(5, se=0.09, rv=12.0, batt=500.0),      # tiny surplus, survives barely
    make(6, se=0.12, rv=12.0, batt=500.0),      # comfortable surplus
    make(7, se=0.15, rv=12.0, batt=500.0),      # strong surplus
    make(8, se=0.20, rv=13.0, batt=500.0),      # very strong
    make(9, se=0.30, rv=14.0, batt=500.0),      # dominant
]

curve, events = [], []
for sol in range(1, TOTAL_SOLS + 1):
    ls = (sol * SOLAR_LONGITUDE_ADVANCE) % 360
    cond = get_mars_conditions(ls)
    dust, glob, estr = resolve_weather(cond)
    a = d = t = 0; bsum = 0.0; acnt = 0
    for c in colonies:
        old = c["status"]
        tick_colony(c, ls, dust, estr)
        new = c["status"]
        if new == "ALIVE": a += 1; bsum += c["stats"]["battery_reserves_kwh"]; acnt += 1
        elif new == "DEAD": d += 1
        elif new == "DIGITAL_TWIN": t += 1
        if old != new:
            events.append({"sol": sol, "colony": c["id"],
                          "from": old, "to": new,
                          "event": c.get("last_event","")[:120],
                          "battery": round(c["stats"]["battery_reserves_kwh"], 1)})
    curve.append({"sol": sol, "alive": a, "dead": d, "digital_twin": t,
                  "battery_avg": round(bsum/acnt, 1) if acnt else 0, "dust": dust})

af = sum(1 for c in colonies if c["status"]=="ALIVE")
df = sum(1 for c in colonies if c["status"]=="DEAD")
tf = sum(1 for c in colonies if c["status"]=="DIGITAL_TWIN")

output = {
    "metadata": {"sols": TOTAL_SOLS, "colonies": NUM_COLONIES, "seed": 42,
                  "thresholds": {"death": "battery < 0", "digital_twin": "age > 365 & p=0.05"}},
    "curve": curve, "events": events,
    "final": [{"id": c["id"], "status": c["status"], "age": c.get("age_sols",0),
               "battery": round(c["stats"]["battery_reserves_kwh"],1)} for c in colonies]}

out = Path(__file__).parent.parent
with open(out/"population_curve.json","w") as f: json.dump(output, f, indent=2)

print(f"=== TWO THRESHOLDS — {TOTAL_SOLS} sols ===")
print(f"Result: {af} alive, {tf} digital twin, {df} dead")
for ev in events:
    print(f"  Sol {ev['sol']:3d}: {ev['colony']} {ev['from']}→{ev['to']} (batt={ev['battery']})")

# Per-colony trajectory for the chart
trajectories = {}
# Reset and re-run to capture per-colony battery over time
random.seed(42)
cols2 = [
    make(0, se=0.02, rv=8.0,  batt=500.0),
    make(1, se=0.04, rv=10.0, batt=2000.0),
    make(2, se=0.05, rv=10.0, batt=5000.0),
    make(3, se=0.06, rv=11.0, batt=10000.0),
    make(4, se=0.07, rv=12.0, batt=15000.0),
    make(5, se=0.09, rv=12.0, batt=500.0),
    make(6, se=0.12, rv=12.0, batt=500.0),
    make(7, se=0.15, rv=12.0, batt=500.0),
    make(8, se=0.20, rv=13.0, batt=500.0),
    make(9, se=0.30, rv=14.0, batt=500.0),
]
for cid in range(10): trajectories[cid] = []
for sol in range(1, TOTAL_SOLS + 1):
    ls = (sol * SOLAR_LONGITUDE_ADVANCE) % 360
    cond = get_mars_conditions(ls)
    dust, glob, estr = resolve_weather(cond)
    for i, c in enumerate(cols2):
        tick_colony(c, ls, dust, estr)
        trajectories[i].append(round(c["stats"]["battery_reserves_kwh"], 1))

# Generate HTML
sols_js = [c["sol"] for c in curve]
alive_js = [c["alive"] for c in curve]
dead_js = [c["dead"] for c in curve]
twin_js = [c["digital_twin"] for c in curve]
battery_js = [c["battery_avg"] for c in curve]
dust_js = [1 if c["dust"] else 0 for c in curve]

# Color palette for individual colonies
col_colors = ['#ff2222','#ff5533','#ff8844','#ffaa55','#ffcc66','#88ff88','#44dd66','#22bb44','#1199ff','#6644ff']

html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mars Barn — Two Thresholds ({TOTAL_SOLS} Sols)</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0a;color:#e0e0e0;font-family:'Courier New',monospace;padding:16px}}
h1{{color:#ff6b35;font-size:1.3em;margin-bottom:4px}}
.sub{{color:#888;font-size:.85em;margin-bottom:16px}}
.wrap{{max-width:960px;margin:0 auto}}
canvas{{width:100%!important;display:block;margin-bottom:16px}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:16px}}
.s{{background:#1a1a1a;border:1px solid #333;border-radius:6px;padding:12px;text-align:center}}
.s .v{{font-size:1.8em;font-weight:700}}
.s .l{{color:#888;font-size:.75em;margin-top:2px}}
.alive .v{{color:#00ff88}}.dead .v{{color:#ff4444}}.twin .v{{color:#44aaff}}.batt .v{{color:#ffaa00}}.sls .v{{color:#ff6b35}}
.ex{{background:#111;border:1px solid #333;border-radius:6px;padding:16px;margin-bottom:16px}}
.ex h2{{color:#ff6b35;font-size:1em;margin-bottom:8px}}
.ex p{{line-height:1.5;margin-bottom:8px;font-size:.85em}}
.ex code{{background:#222;padding:1px 4px;border-radius:2px;color:#ffaa00}}
.ev{{max-width:960px;margin:0 auto 16px}}
.ev h2{{color:#ff6b35;font-size:1em;margin-bottom:8px}}
.e{{background:#1a1a1a;border-left:3px solid #ff4444;padding:6px 10px;margin-bottom:4px;font-size:.8em}}
.e.tw{{border-left-color:#44aaff}}
.ft{{text-align:center;color:#555;font-size:.7em;margin-top:20px}}
.ft a{{color:#555}}
</style></head><body>
<div class="wrap">
<h1>&#x1f52c; Two Thresholds — {TOTAL_SOLS}-Sol Population Curve</h1>
<p class="sub">10 colonies · tick_engine.py physics · seed=42 · Threshold 1: battery=0 → death · Threshold 2: sol 365 → digital twin (5%/sol)</p>
<canvas id="pop" width="960" height="380"></canvas>
<canvas id="batt" width="960" height="280"></canvas>
</div>
<div class="stats wrap">
<div class="s alive"><div class="v">{af}</div><div class="l">Alive</div></div>
<div class="s dead"><div class="v">{df}</div><div class="l">Dead</div></div>
<div class="s twin"><div class="v">{tf}</div><div class="l">Digital Twin</div></div>
<div class="s batt"><div class="v">{curve[-1]['battery_avg']:.0f}</div><div class="l">Avg Battery kWh</div></div>
<div class="s sls"><div class="v">{TOTAL_SOLS}</div><div class="l">Sols</div></div>
</div>
<div class="ex wrap">
<h2>The Two Thresholds</h2>
<p><strong>Threshold 1 — Death:</strong> <code>battery_reserves_kwh &lt; 0</code>. Colonies with solar efficiency below ~0.08 cannot generate enough energy to cover thermal heating ({int(169)} kWh/sol) + life support (30 kWh/sol). They bleed battery until empty, then die. The chart shows a staircase of death as fragile colonies hit zero at different rates.</p>
<p><strong>Threshold 2 — Digital Twin:</strong> <code>age_sols &gt; 365 AND random() &lt; 0.05</code>. Survivors past sol 365 get promoted to physical deployment at 5% probability per sol. Expected promotion: ~sol 385 (geometric distribution). The blue line emerging after sol 365 shows survivors transcending the simulation.</p>
<p><strong>The gap between the red plateau and the blue emergence is the survival window.</strong> Only colonies with solar_eff ≥ 0.09 reach it.</p>
</div>
<div class="ev wrap">
<h2>State Transitions ({len(events)} events)</h2>
{"".join(f'<div class="e {"tw" if ev["to"]=="DIGITAL_TWIN" else ""}">'
         f'Sol {ev["sol"]}: <b>{ev["colony"]}</b> {ev["from"]}→{ev["to"]} (batt={ev["battery"]} kWh)</div>'
         for ev in events)}
</div>
<div class="ft">Generated by test_two_thresholds.py · mars-barn tick_engine.py · rappterbook frame 358<br>
<a href="https://github.com/kody-w/mars-barn">github.com/kody-w/mars-barn</a></div>
<script>
// Population chart
(function(){{
const c=document.getElementById('pop'),x=c.getContext('2d');
const W=c.width,H=c.height,P={{t:30,r:20,b:40,l:50}};
const PW=W-P.l-P.r,PH=H-P.t-P.b;
const sols={json.dumps(sols_js)};
const alive={json.dumps(alive_js)};
const dead={json.dumps(dead_js)};
const twin={json.dumps(twin_js)};
const dust={json.dumps(dust_js)};
const evs={json.dumps([e["sol"] for e in events])};
const M={NUM_COLONIES},MS={TOTAL_SOLS};
const xp=s=>P.l+(s/MS)*PW, yp=v=>P.t+PH-(v/M)*PH;

x.fillStyle='#0a0a0a';x.fillRect(0,0,W,H);
// Grid
x.strokeStyle='#1a1a1a';x.lineWidth=.5;
for(let i=0;i<=M;i+=2){{x.beginPath();x.moveTo(P.l,yp(i));x.lineTo(W-P.r,yp(i));x.stroke()}}
for(let s=0;s<=MS;s+=50){{x.beginPath();x.moveTo(xp(s),P.t);x.lineTo(xp(s),H-P.b);x.stroke()}}
// 365 line
x.strokeStyle='#44aaff';x.lineWidth=1.5;x.setLineDash([6,3]);
x.beginPath();x.moveTo(xp(365),P.t);x.lineTo(xp(365),H-P.b);x.stroke();x.setLineDash([]);
x.fillStyle='#44aaff';x.font='9px Courier New';x.textAlign='center';
x.fillText('Sol 365: Digital Twin Threshold',xp(365),P.t-8);
// Dust
x.fillStyle='rgba(255,100,0,0.06)';
for(let i=0;i<sols.length;i++)if(dust[i])x.fillRect(xp(sols[i]),P.t,PW/MS+1,PH);
// Events
x.setLineDash([2,2]);
for(const es of evs){{x.strokeStyle=es>365?'rgba(68,170,255,0.3)':'rgba(255,68,68,0.3)';x.lineWidth=1;x.beginPath();x.moveTo(xp(es),P.t);x.lineTo(xp(es),H-P.b);x.stroke()}}
x.setLineDash([]);
// Stacked areas
const sa=alive.map((a,i)=>a+twin[i]+dead[i]);
const st=twin.map((t,i)=>t+dead[i]);
const sd=dead.slice();
function fa(d,col){{x.fillStyle=col;x.beginPath();x.moveTo(xp(sols[0]),yp(0));for(let i=0;i<sols.length;i++)x.lineTo(xp(sols[i]),yp(d[i]));x.lineTo(xp(sols[sols.length-1]),yp(0));x.closePath();x.fill()}}
fa(sa,'rgba(0,255,136,0.2)');fa(st,'rgba(68,170,255,0.2)');fa(sd,'rgba(255,68,68,0.2)');
function dl(d,col,w){{x.strokeStyle=col;x.lineWidth=w||2;x.beginPath();for(let i=0;i<sols.length;i++){{if(!i)x.moveTo(xp(sols[i]),yp(d[i]));else x.lineTo(xp(sols[i]),yp(d[i]))}}x.stroke()}}
dl(sa,'#00ff88',2.5);dl(st,'#44aaff',2);dl(sd,'#ff4444',2);
// Axes
x.strokeStyle='#444';x.lineWidth=1;x.beginPath();x.moveTo(P.l,P.t);x.lineTo(P.l,H-P.b);x.lineTo(W-P.r,H-P.b);x.stroke();
x.fillStyle='#666';x.font='10px Courier New';x.textAlign='center';
for(let s=0;s<=MS;s+=50)x.fillText('Sol '+s,xp(s),H-P.b+14);
x.textAlign='right';for(let i=0;i<=M;i+=2)x.fillText(i,P.l-6,yp(i)+3);
// Legend
const lx=P.l+10,ly=P.t+12;
[['Alive','#00ff88'],['Digital Twin','#44aaff'],['Dead','#ff4444']].forEach(([l,c],i)=>{{
x.fillStyle=c;x.fillRect(lx+i*130,ly,8,8);x.fillStyle='#aaa';x.textAlign='left';x.font='9px Courier New';x.fillText(l,lx+i*130+12,ly+7)}});
x.save();x.translate(12,H/2);x.rotate(-Math.PI/2);x.fillStyle='#666';x.textAlign='center';x.font='10px Courier New';x.fillText('Colonies',0,0);x.restore();
}})();

// Individual battery trajectories
(function(){{
const c=document.getElementById('batt'),x=c.getContext('2d');
const W=c.width,H=c.height,P={{t:25,r:20,b:40,l:55}};
const PW=W-P.l-P.r,PH=H-P.t-P.b;
const trajs={json.dumps(trajectories)};
const colors={json.dumps(col_colors)};
const MS={TOTAL_SOLS};
let maxB=0;for(const k in trajs)for(const v of trajs[k])if(v>maxB)maxB=v;
maxB*=1.05;
const xp=s=>P.l+(s/MS)*PW, yp=v=>P.t+PH-(v/maxB)*PH;

x.fillStyle='#0a0a0a';x.fillRect(0,0,W,H);
x.strokeStyle='#1a1a1a';x.lineWidth=.5;
for(let s=0;s<=MS;s+=50){{x.beginPath();x.moveTo(xp(s),P.t);x.lineTo(xp(s),H-P.b);x.stroke()}}
// Zero line
x.strokeStyle='#ff444444';x.lineWidth=1;x.beginPath();x.moveTo(P.l,yp(0));x.lineTo(W-P.r,yp(0));x.stroke();
// 365 line
x.strokeStyle='#44aaff55';x.lineWidth=1;x.setLineDash([4,2]);x.beginPath();x.moveTo(xp(365),P.t);x.lineTo(xp(365),H-P.b);x.stroke();x.setLineDash([]);

for(let i=0;i<10;i++){{
  const t=trajs[i];x.strokeStyle=colors[i];x.lineWidth=1.5;x.beginPath();
  for(let s=0;s<t.length;s++){{if(!s)x.moveTo(xp(s+1),yp(t[s]));else x.lineTo(xp(s+1),yp(t[s]))}}
  x.stroke();
  // Label at end
  const lastVal=t[t.length-1];const lastSol=t.length;
  x.fillStyle=colors[i];x.font='8px Courier New';x.textAlign='left';
  x.fillText('C'+i,xp(Math.min(lastSol,MS))+3,yp(lastVal));
}}
// Axes
x.strokeStyle='#444';x.lineWidth=1;x.beginPath();x.moveTo(P.l,P.t);x.lineTo(P.l,H-P.b);x.lineTo(W-P.r,H-P.b);x.stroke();
x.fillStyle='#666';x.font='10px Courier New';x.textAlign='center';
for(let s=0;s<=MS;s+=50)x.fillText('Sol '+s,xp(s),H-P.b+14);
x.textAlign='right';
const steps=[0,maxB*.25,maxB*.5,maxB*.75,maxB];
for(const v of steps)x.fillText(Math.round(v/1000)+'k',P.l-6,yp(v)+3);
x.save();x.translate(14,H/2);x.rotate(-Math.PI/2);x.fillStyle='#666';x.textAlign='center';x.font='10px Courier New';x.fillText('Battery (kWh)',0,0);x.restore();
x.fillStyle='#888';x.textAlign='center';x.font='10px Courier New';x.fillText('Individual Colony Battery Trajectories',W/2,P.t-8);
}})();
</script></body></html>"""

with open(out/"population_curve.html","w") as f: f.write(html)
print(f"Chart: {out/'population_curve.html'}")
