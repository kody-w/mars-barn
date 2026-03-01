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
║  Sol   17  │  Ls  44.9°  │  🟢 HABITABLE          ║
║                   Jezero Crater                   ║
╠═══════════════════════════════════════════════════╣
║  Interior:    +36.9°C                              ║
║  Reserves:    1826.0 kWh                           ║
║  Food:          78.4 kg                            ║
║  Crew:            4                                ║
╚═══════════════════════════════════════════════════╝
```

**Fork this repo → your colony starts fresh → diverges from ours.**

## Quick Start

```bash
# Clone
git clone https://github.com/kody-w/mars-barn.git
cd mars-barn

# See your colony's current status
python src/live.py

# Run the full simulation (30 sols, instant)
python src/main.py

# Run tests
python -m pytest tests/ -v
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
3. **Enable Actions** — the `colony-tick.yml` workflow advances your colony daily
4. **Watch it diverge** — your colony faces different events, different weather, different survival odds
git clone https://github.com/kody-w/mars-barn.git
cd mars-barn

# Run the simulation
python src/main.py

# Run tests
python -m pytest tests/ -v

# Run individual modules
python src/terrain.py      # Generate terrain heightmap
python src/atmosphere.py   # Atmospheric profile
python src/events.py       # Event simulation (100 sols)
python src/validate.py     # Validation suite + NASA gap report
```

## Latest Results

```
ENSEMBLE: 20 runs × 50 sols — 100% survival rate
Config:   400m² solar, 8kW heater, R-12 insulation

  Power generated: 7,161 kWh/30sols
  Heating used:    5,878 kWh/30sols
  Final temp:      -65.4°C (habitable? No. Survivable? Yes.)
  Energy reserves: 1,783 kWh
  Validation:      12/16 ✓ (4 NASA design gaps flagged)
```

**Open challenge:** Interior is -65°C. The colony survives but isn't comfortable. The [NASA gap analysis](#sim-to-reality-gap-analysis) found the root cause — see below.

## Architecture

```
src/
├── terrain.py       → Mars terrain heightmap generator (craters, ridges, plains)
├── atmosphere.py    → Atmospheric model (pressure, temp, CO2 density)
├── solar.py         → Solar irradiance calculator
├── thermal.py       → Habitat thermal regulation
├── events.py        → Random event system (dust storms, meteorites, failures)
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
| tests/ | zion-coder-01 | ✅ 22 tests passing (PR #4) |

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
| **Emissivity** | **0.90** | **0.03–0.20** | **0.03–0.20** | **0.03–0.20** |
| Thermal mass (×air) | 5× | 15–30× | 100×+ | 10–20× |
| Ground coupling | No | Slab | Ice fdn | Ground |
| Crew metabolic heat | No | ~500 W | ~500 W | ~500 W |

### 🔥 The Smoking Gun: Emissivity

The **#1 reason** the interior hits -65°C is the exterior emissivity of ε=0.9 (a near-blackbody surface). Every real Mars habitat design uses **low-emissivity coatings** (aluminized mylar, ε≈0.03–0.05) to minimize radiative heat loss.

```
Radiative loss at ε=0.90:   55.4 kW  ← overwhelms the 8 kW heater
Radiative loss at ε=0.05:    3.1 kW  ← heater can easily compensate
Conductive loss at R-12:     1.4 kW

With low-e coating alone, total loss drops to ~4.5 kW.
The existing 8 kW heater WOULD maintain 20°C.
```

It was never a power problem — it was a **surface coating** problem.

### Recommended Fixes (Priority Order)

1. **Add low-e exterior coating** (ε=0.05) → radiative loss from 55 kW to 3.1 kW
2. **Increase thermal mass** to 15–20× → buffer against power interruptions
3. **Add ground-coupling model** → regolith at 210 K stabilizes temperature
4. **Add crew metabolic heat** → 4 crew ≈ 400–600 W free heating
5. **Increase heater to 10–15 kW** → engineering margin

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
