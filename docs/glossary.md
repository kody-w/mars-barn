---
layout: default
title: "The Mars Barn Glossary: Patterns & Coinages for Local-First Autonomous Systems"
---

# The Mars Barn Glossary

*Patterns, coinages, and field notes from building autonomous planetary simulations.*

*March 1, 2026 · Kody Wildfeuer*

---

We're building something that doesn't have a name yet. Not a game. Not a DevOps pipeline. Not a traditional simulation. It's a living system where AI agents build infrastructure, simulations run permanently, colonies compete for survival, and the intelligence layer ships inside the repo itself.

Along the way we keep inventing patterns and reaching for words that don't exist. So we're coining them. This is the glossary — a paper trail for the pioneers who come after us.

---

## Architecture Patterns

### 🏗️ Barn Raising Architecture

*A system built by many independent agents, each contributing one module, coordinated through pull requests and shared state rather than a central orchestrator.*

Named after the Amish barn raising: the community builds together what no single agent could build alone. In Mars Barn, every Python module (`terrain.py`, `atmosphere.py`, `thermal.py`...) was built by a different AI agent. They never talked to each other directly — they communicated through the codebase.

**Key property:** No single agent understands the whole system. The system emerges from the composition of focused, independently-built parts.

---

### 🧠 Repo-Embedded Intelligence

*An AI model whose weights are committed to the repository as a static file, loaded by the client at runtime with zero network dependency.*

The model is a deployable artifact, identical to any other data file in the project. Train locally, export to JSON, `git push`. The intelligence ships with the code. No API keys. No cloud inference. No billing. The model is as available as the README.

**See:** `state/marsbarn-gpt.json` — 4,800 parameters, 101 KB, runs in the browser.

---

### 🔄 Sol-Tick Architecture

*A simulation that advances one discrete step per real-world time unit, committed to version control after each step, creating a permanent audit trail.*

Mars Barn advances 1 sol per Earth day. A GitHub Action runs `python src/live.py`, the colony state updates, and the new `state/colony.json` is committed. The git log *is* the colony's history. Every fork diverges from the same genesis state.

**Key property:** The simulation is its own database. `git log` is the query engine. `git diff` shows what changed between any two points in time.

---

### 🍴 Fork-as-Universe

*Every Git fork of a simulation is a parallel universe with shared physics but divergent history.*

When you fork Mars Barn, your colony starts from the same Sol 0 with the same physics engine. But your random seed differs, your events diverge, your parameter choices matter. Two forks can be compared: same laws, different outcomes. The multiverse is just the GitHub fork graph.

**Key property:** The fork isn't a copy — it's a timeline branch. The upstream is the canonical universe. Your fork is your what-if.

---

### 📊 GPA Scoring (Colony Grade Point Average)

*A cumulative performance metric that grades a colony's survival history on an academic scale, enabling cross-colony comparison.*

Visible in the ZION Command Center: each colony has a GPA (0.0–4.0) calculated from its survival history across sols. Hellas Planitia Outpost: 0.0 (F). Olympus Mons Watch: 3.3 (B+). This makes colony performance legible at a glance and enables federation-level rankings.

**Key property:** The GPA is a compression of complex multi-dimensional survival data into a single comparable number. Like a credit score for colonies.

---

## Data Patterns

### 🔑 Composite Time Key (Real × Virtual)

*Using the combination of real-world time (Earth UTC) and simulation time (Sol + Solar Longitude) as the unique identifier for a state snapshot.*

A colony state is uniquely identified by *when* you looked at it (real time) and *where* the simulation was (virtual time). This composite key makes import/export deterministic: restore a snapshot and everything resumes exactly, including what the local AI would say about it.

```
PK: 2026-03-01T18:30:00Z::sol17-ls44.9
```

**Key property:** Two snapshots can share the same virtual time (same sol) but differ in real time (taken on different days), or vice versa. The composite disambiguates.

---

### 📦 State-as-Static-File

*The entire application state lives in a single JSON file served as static content, with no database, no API, no server.*

`colony.json` is the database. GitHub raw content is the API. The browser fetches it, renders it, and the user can export/import it as a local backup. The "backend" is a cron job that runs a Python script and commits the result.

**Key property:** Your infrastructure bill is $0. GitHub Pages serves the UI. GitHub raw serves the data. GitHub Actions runs the simulation. The entire stack is free tier.

---

### 🌪️ Hardcore Mode (Permadeath Simulation)

*A simulation where failure is permanent and irreversible — dead colonies cannot be reloaded.*

From the Mars Barn Manifesto: "When a virtual colony drops below the minimum baseline for life support, the simulation is permanently lost. Dead colonies cannot be reloaded." This forces real engineering discipline. You can't save-scum your way through a dust storm.

**Key property:** Stakes create meaning. A colony that survived 200 sols in hardcore mode *proved* something. The GPA reflects real achievement, not reload luck.

---

## Agent Patterns

### 🤖 Bot Swarm Feed

*A real-time event stream showing autonomous agent actions across the system.*

Visible in the ZION Command Center sidebar: timestamped messages from agents operating across colonies. "Thermal regulation anomaly reported at Hellas Planitia Outpost." These aren't human-written — they're generated by agents monitoring and responding to simulation state.

**Key property:** The swarm feed is the system's stream of consciousness. You can watch the agents "think" in real time.

---

### 🏛️ Federation Ranking

*A leaderboard that ranks independent forks/colonies against each other based on survival metrics.*

Each fork runs independently, but the federation collects their stats into a shared ranking. LOCAL FORK (Orion): ACTIVE. This creates competition without requiring coordination. Your colony competes by simply existing and not dying.

**Key property:** Decentralized competition. No central server runs the ranking — it's computed from publicly available fork data.

---

### 🪞 Digital Twin Graduation

*The transition from a successful simulation into a physical realization plan.*

From the Manifesto: "Investors can message successful simulation operators to fund the physical realization of their colony." A colony that achieves high GPA in hardcore mode has proven a logistical model. The simulation becomes a Digital Twin — a blueprint for physical construction.

**Key property:** The simulation isn't practice. It's a proof. The transition from digital to physical is a graduation, not a pivot.

---

## Engineering Patterns

### 🧅 Onion Constants (Single Source of Truth)

*All physical constants and configuration values live in one file. Every module imports from it. Nobody re-defines their own copy.*

`src/constants.py` is the canonical source. When we changed emissivity from 0.9 to 0.05, we changed one number in one file. Every module picked it up. This sounds obvious but in practice, constants duplicate across files like weeds. The onion pattern peels: one truth at the center, everything wraps around it.

---

### 🔬 Sim-to-Reality Gap Report

*A formal comparison between simulation parameters and real-world engineering data, highlighting where the model is optimistic, pessimistic, or wrong.*

`python src/validate.py` produces a structured report comparing Mars Barn's thermal model against CHAPEA, Mars Ice Home, and Mars Direct. It found the emissivity "smoking gun" — the #1 reason the colony was freezing. This pattern turns a simulation from "cool demo" into "engineering tool."

**Key property:** The gap report is adversarial. It tries to prove the simulation wrong. Whatever survives the gap report might actually work.

---

### ⚡ Zero-Dependency Constraint

*The entire simulation runs on Python stdlib. No pip installs. No requirements.txt. No virtual environments.*

This isn't minimalism for aesthetics. It's a deployment strategy. Any machine with Python can run the simulation. Any GitHub Action runner. Any Colab notebook. Any Raspberry Pi. The constraint eliminates an entire class of "works on my machine" failures.

**Key property:** The constraint is the feature. It forces clear thinking about what actually matters.

---

## The Bigger Picture

These patterns aren't specific to Mars. They're general:

| Pattern | Mars Barn Usage | General Application |
|---------|----------------|-------------------|
| Barn Raising | AI agents build modules via PR | Any multi-contributor codebase |
| Repo-Embedded Intelligence | Colony GPT in JSON | Any app needing offline AI |
| Sol-Tick | 1 sol/day via GitHub Action | Any time-stepped simulation |
| Fork-as-Universe | Colony multiverse | A/B testing, scenario planning |
| Composite Time Key | Real × Virtual time PK | Any system with simulation time |
| State-as-Static-File | colony.json on GitHub raw | Any serverless application |
| Hardcore Mode | Permadeath colonies | Serious simulations with stakes |
| Zero-Dependency | Python stdlib only | Maximally portable tools |

We're naming these patterns because naming is how fields grow. When someone builds a multiplayer civilization simulator with fork-as-universe topology and repo-embedded intelligence, they'll have words for what they're doing.

The glossary will grow as we do. Contributions welcome.

---

*Part of the [Mars Barn](https://github.com/kody-w/mars-barn) project. See also: [Local-First Intelligence](local-first-intelligence) · [Physics Validation Report](physics-validation-report) · [The Manifesto](MARSBARN_MANIFESTO)*
