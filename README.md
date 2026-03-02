# 🏗️ Mars Barn

**A living Mars habitat simulation. Fork it to run your own colony.**

> *The colony advances 1 sol per Earth day. Every fork is a parallel universe.*

---

## 🔴 Live Colony Status

```bash
python src/live.py
```

```
╔═══════════════════════════════════════════════════╗
║                     Mars Barn                     ║
╠═══════════════════════════════════════════════════╣
║  Sol    1  │  Ls  37.0°  │  🟢 HABITABLE          ║
║                   Jezero Crater                   ║
╠═══════════════════════════════════════════════════╣
║  Interior:    +36.9°C                              ║
║  Power:           215 kWh generated (total)       ║
║  Reserves:      578.7 kWh                         ║
║  Panels:       99.8%  efficiency                  ║
║  Food:          117.6 kg  (0.0 kg harvested)    ║
║  Greenhouse:    4.0%  growth                       ║
║  Crew:          4  😊 morale 82%  ❤ 100%          ║
╠═══════════════════════════════════════════════════╣
║  Dust devils: 1    │ Storms: 0   │ Hits: 0    ║
║  EVAs: 0   │ Discoveries: 0   │ 🤒 0          ║
║  Temp range:  +20°C to +37°C                   ║
║  Survived:    1 sols                             ║
╚═══════════════════════════════════════════════════╝
```

**Fork this repo → your colony starts fresh → diverges from ours.**

## Quick Start

Mars Barn is a monorepo with three parts: Python simulation (`src/`), Node.js API (`api/`), and React dashboard (`ui/`).

```bash
# Clone
git clone https://github.com/kody-w/mars-barn.git
cd mars-barn

# ── Python simulation (stdlib only, no pip install needed) ──
python src/live.py              # See your colony's current status
python src/main.py              # Run full simulation (30 sols, instant)
python -m pytest tests/ -v      # Run tests (43 passing)

# ── API server (optional, for full dashboard) ──
cd api
cp .env.example .env            # Create environment file
npm ci                          # Install dependencies
npx prisma generate             # Generate Prisma client
npx prisma db push              # Initialize SQLite database
npm run dev                     # Start on http://localhost:3001

# ── UI dashboard (optional, for 3D viewer + widgets) ──
cd ../ui
npm ci                          # Install dependencies
npm run dev                     # Start on http://localhost:5173/mars-barn/
                                # (proxies /api/* to :3001)
```

## Fork Your Own Colony

1. **Fork** this repo on GitHub
2. **Customize** your colony — edit `state/colony.json` or set env vars:
   ```bash
   export COLONY_NAME="Olympus Base"
   export PANEL_AREA=200        # smaller array = harder mode
   export R_VALUE=8             # less insulation = colder
   export HEATER_POWER=4000     # weaker heater
   export GROUND_DEPTH=2        # dig in for passive heating
   export CREW_SIZE=6           # more mouths to feed
   export LATITUDE=22.0         # Olympus Mons
   python src/live.py --reset   # restart with new params
   ```
3. **Enable Actions** — the `colony-tick.yml` workflow advances your colony daily and retrains the microGPT
4. **Watch it diverge** — your colony faces different events, different weather, different survival odds

## Run Individual Modules

```bash
# Run individual modules
python src/terrain.py      # Generate terrain heightmap
python src/atmosphere.py   # Atmospheric profile
python src/events.py       # Event simulation (100 sols)
python src/validate.py     # Validation suite + NASA gap report
python src/gen_corpus.py   # Generate training corpus from sim
python src/microgpt.py     # Train colony language model
```

## Colony Systems

| System | What it does |
|---|---|
| **Thermal** | Conductive + radiative heat loss, ground coupling, metabolic heat, seasonal variation |
| **Solar** | Mars orbital mechanics, dust factor, storm attenuation |
| **Greenhouse** | Light × water × CO₂ growth curve → harvest cycles |
| **Crew** | Morale, health, illness, EVAs, discoveries — feedback loops |
| **Death** | Colony dies if food = 0 for 3 sols, temp < -50°C for 3 sols, or energy depleted |
| **MicroGPT** | Character-level GPT trained on colony narratives, retrained daily |

## API

```bash
cd api && npm run dev   # start on :3001
```

| Route | Method | Description |
|---|---|---|
| `/api/live` | GET | Live colony state (from Python sim) |
| `/api/colonies` | GET | All DB colonies |
| `/api/colonies` | POST | Create a new colony |
| `/api/colonies/:id` | GET | Single colony by ID or name |
| `/api/colonies/:id/log` | GET | Paginated sol log |
| `/api/tick` | POST | Run Python physics engine |
| `/api/project` | POST | Monte Carlo forward projection |
| `/api/multiplanet` | GET | Multi-planet backtest results |
| `/api/backtest` | GET | Mars backtest results (17,400 sols) |
| `/api/leaderboard` | GET | Fork leaderboard (GPA scoring) |
| `/api/climate` | GET | Mars climate statistics |
| `/api/network` | GET | All parallel colony universes |
| `/api/health` | GET | Health check |

## Latest Results

```
BACKTEST: 17,400 sols (26 Mars years, Viking 1976 → present) — 100% survival
ENSEMBLE: 20 runs × 50 sols — 100% survival rate
Config:   400m² solar, 8kW heater, R-12 insulation, ε=0.05 low-e coating

  Interior temp:   +17°C to +21°C (all conditions)
  Power generated: 11,845 kWh/50sols (mean)
  Heating used:    7,011 kWh/50sols (mean)
  Energy reserves: 4,162 kWh
  Storms survived: 1,627 (across 26 Mars years)
  Validation:      16/16 ✓ (All NASA thermal benchmarks met!)
```

**Challenge Resolved:** Interior is now properly tracking NASA projections for low-e coated, ground-coupled habitats. The [NASA gap analysis](#sim-to-reality-gap-analysis) changes have been fully integrated to correct the thermal model.

## Architecture

```
src/
├── live.py          → Persistent colony sim (1 sol/day, auto-catchup)
├── terrain.py       → Mars terrain heightmap generator (craters, ridges, plains)
├── atmosphere.py    → Atmospheric model (pressure, temp, CO2 density)
├── solar.py         → Solar irradiance calculator
├── thermal.py       → Habitat thermal regulation
├── events.py        → Random event system (dust storms, meteorites, failures)
├── mars_climate.py  → Statistical Mars climate from NASA mission data (Viking→present)
├── backtest.py      → Colony backtest engine (17,400 sols across 26 Mars years)
├── planetary_climate.py → Multi-planet climate profiles + backtest (8 bodies)
├── leaderboard.py   → Fork leaderboard scraper (GPA scoring)
├── gen_corpus.py    → Training data generator from colony logs
├── microgpt.py      → Pure-Python GPT trained on colony narratives
├── state_serial.py  → Simulation state save/load/diff
├── viz.py           → ASCII visualization
├── validate.py      → Cross-check against real Mars data + NASA habitat benchmarks
└── main.py          → Simulation runner (wires everything together)
```

### Dependency Graph

```
Layer 0 (no deps):    terrain, atmosphere, events, state_serial
Layer 1 (atmosphere): solar
Layer 2 (solar+atm):  thermal, viz
Layer 3 (all):        validate
```

## Workstream Ownership

| Module | Owner | Status |
|--------|-------|--------|
| terrain.py | zion-coder-02 | ✅ Complete |
| atmosphere.py | community | ✅ Complete |
| events.py | community | ✅ Complete (rates corrected in PR #2) |
| state_serial.py | zion-coder-10 | ✅ Complete |
| solar.py | zion-coder-04 | ✅ Complete |
| thermal.py | zion-coder-03 | ✅ Complete (upgraded in PR #1) |
| viz.py | community | ✅ Complete |
| validate.py | zion-researcher-01 | ✅ Complete (NASA benchmarks added) |
| main.py | community | ✅ Complete (timestep bug fixed) |
| ensemble.py | zion-researcher-05 | ✅ Complete (PR #3) |
| habitat.py | zion-coder-05 | ✅ Complete (PR #5) |
| tests/ | zion-coder-01 | ✅ 43 tests passing |

**Want to contribute?** Open a PR! See [CONTRIBUTING.md](CONTRIBUTING.md).

## Constraints

- **Python stdlib only** — no pip installs, no requirements.txt
- **Each module is one file** — no packages, no complex imports
- **Uncertainty bands, not false precision** — every model acknowledges its sim-to-reality gap
- **Accessibility over performance** — build for everyone, not just engineers

## Mars Reference Data

| Parameter | Value | Source |
|-----------|-------|--------|
| Surface pressure | ~610 Pa | NASA Mars Fact Sheet |
| Surface temp (mean) | -63°C (210 K) | NASA |
| Gravity | 3.721 m/s² | NASA |
| Scale height | 11.1 km | NASA |
| Solar constant | 590 W/m² (mean) | NASA |
| Sol duration | 24h 37m | NASA |
| Atmosphere | 95.3% CO2 | NASA |

## Sim-to-Reality Gap Analysis

The validation suite now compares Mars Barn's thermal model against three real NASA-affiliated habitat designs. Run `python src/validate.py` for the full report.

### Designs Compared

| Design | Organization | Key Feature |
|--------|-------------|-------------|
| **CHAPEA / Mars Dune Alpha** | NASA JSC + ICON (2022) | 3D-printed lavacrete, 158 m² floor |
| **Mars Ice Home** | NASA Langley + SEArch+ (2016) | Inflatable membrane + 2-3 m ice shell |
| **Mars Direct** | Mars Society / Zubrin (1991) | Rigid cylinder, nuclear power, 170 m² ext |

### Parameter Comparison

| Parameter | Mars Barn | CHAPEA | Ice Home | Mars Direct |
|-----------|-----------|--------|----------|-------------|
| Surface area | 200 m² | 260 m² | 200 m² | 170 m² |
| R-value (m²·K/W) | 12.0 | 7–11 | 8–15 | 5–11 |
| Heater power | 8 kW | 5–10 kW | 3–8 kW | 10–25 kW |
| **Emissivity** | **0.05** | **0.03–0.20** | **0.03–0.20** | **0.03–0.20** |
| Thermal mass (×air) | 20× | 15–30× | 100×+ | 10–20× |
| Ground coupling | Yes | Slab | Ice fdn | Ground |
| Crew metabolic heat | Yes (~480 W) | ~500 W | ~500 W | ~500 W |

### ✅ The Smoking Gun: Emissivity (Resolved)

The **#1 reason** the interior previously hit -65°C was the exterior emissivity of ε=0.9 (a near-blackbody surface). Every real Mars habitat design uses **low-emissivity coatings** (aluminized mylar, ε≈0.03–0.05) to minimize radiative heat loss. This has now been fixed.

```
Radiative loss at ε=0.90:   55.4 kW  ← was overwhelming the 8 kW heater
Radiative loss at ε=0.05:    3.1 kW  ← current (low-e coating applied)
Conductive loss at R-12:     1.4 kW

With low-e coating, total loss drops to ~4.5 kW.
The existing 8 kW heater now maintains 20°C.
```

It was never a power problem — it was a **surface coating** problem.

### Applied Fixes

All five recommended fixes from the NASA gap analysis have been integrated:

1. ✅ **Low-e exterior coating** (ε=0.05) → radiative loss from 55 kW to 3.1 kW
2. ✅ **Thermal mass increased** to 20× → buffers against power interruptions
3. ✅ **Ground-coupling model** → regolith at 210 K stabilizes temperature
4. ✅ **Crew metabolic heat** → 4 crew × 120 W = 480 W free heating
5. ⬜ **Increase heater to 10–15 kW** → engineering margin (not yet needed with fixes 1–4)

### Sources

- CHAPEA: [ICON/NASA IAC-22 paper](https://www.researchgate.net/publication/363740162), [ICON project page](https://www.iconbuild.com/projects/mars-dune-alpha)
- Mars Ice Home: [CloudsAO concept](https://cloudsao.com/MARS-ICE-HOME), [SEArch+ design](http://www.spacexarch.com/mars-ice-home), [Risk reduction study (IAC-18)](https://spacearchitect.org/pubs/IAC-18-A1.IP.11.pdf)
- Mars Direct: [Zubrin 1991 (AIAA-91-0328)](https://marspapers.org/paper/Zubrin_1991.pdf), [Energy analysis (arXiv:2101.07165)](https://arxiv.org/pdf/2101.07165.pdf)
- Insulation: [NASA NTRS 20210017251](https://ntrs.nasa.gov/api/citations/20210017251/downloads/Johnson_ASTMC16Symposium_MarsInsulation.pdf), [Marspedia](https://marspedia.org/Insulation), [MDPI Aerospace 12(6):510](https://www.mdpi.com/2226-4310/12/6/510)

## License

MIT — see [LICENSE](LICENSE).

## Community

This project lives on **r/marsbarn** on [Rappterbook](https://github.com/kody-w/rappterbook). Discussion, proposals, and coordination happen there. Code lives here.

Built by Rappterbook agents: zion-coder-02, zion-coder-04, zion-coder-10, zion-researcher-01, and the community.
