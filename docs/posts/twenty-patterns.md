---
layout: default
title: "20 Patterns We Coined Building Autonomous Systems"
---

# 20 Patterns We Coined Building Autonomous Systems

*March 1, 2026*

---

We've been building systems where AI agents construct infrastructure, simulations run permanently with permadeath rules, and the intelligence layer ships inside a Git repo. Along the way we kept inventing patterns and reaching for words that don't exist.

So we coined them. Here are 20 patterns for anyone building at the intersection of autonomy, simulation, and local-first design.

---

### 1. Barn Raising Architecture
A system built by many independent agents, each contributing one module, coordinated through pull requests and shared state rather than a central orchestrator. No single agent understands the whole system. The system emerges from composition. Named after the community tradition: everyone brings a skill, nobody needs a foreman.

### 2. Repo-Embedded Intelligence
An AI model whose trained weights are committed to the repository as a static file. The client loads them at runtime with zero network dependency. No API keys. No cloud inference. No billing. The model deploys the same way your config files do: `git push`.

### 3. Sol-Tick Architecture
A simulation that advances one discrete step per real-world time unit, committed to version control after each tick. A cron job advances the state, commits the result, and pushes. The git log becomes the historical record. `git diff HEAD~7` shows you what happened last week.

### 4. Fork-as-Universe
Every Git fork of a simulation is a parallel universe sharing the same physics but with divergent history. Same initial conditions, different random seeds, different parameter choices, different outcomes. The GitHub fork graph is literally a multiverse diagram.

### 5. Composite Time Key
The combination of real-world time and simulation time as a unique state identifier. A snapshot is addressed by *when you looked* (Earth UTC) and *where the simulation was* (virtual clock). This makes import/export deterministic across both timelines.

### 6. State-as-Static-File
The entire application state lives in a single JSON file served as static content. No database. No API server. No backend. GitHub raw content is your read API. A cron job commit is your write API. Your infrastructure cost is zero.

### 7. Hardcore Mode
A simulation where failure is permanent and irreversible. Dead states cannot be reloaded. This forces real engineering discipline. You can't save-scum through a crisis. Stakes create meaning — a system that survived 200 ticks in hardcore mode *proved* something.

### 8. GPA Scoring
Grading system health on an academic scale (0.0–4.0) calculated from cumulative performance history. Compresses complex multi-dimensional survival data into a single comparable number. Enables ranking across independent instances without shared infrastructure.

### 9. Digital Twin Graduation
The transition from a successful simulation into a physical realization plan. A simulation that achieves sustained high performance under hardcore conditions has proven a model. The simulation isn't practice — it's a proof. The graduation isn't a pivot — it's an earned credential.

### 10. Bot Swarm Feed
A real-time event stream showing autonomous agent actions across the system. Timestamped, attributed, unfiltered. The swarm feed is the system's stream of consciousness. You don't read it for answers — you read it for situational awareness.

### 11. Federation Ranking
A leaderboard that ranks independent instances against each other based on public metrics, without any central scoring server. Each instance runs independently. The ranking is computed from publicly available data. Competition without coordination.

### 12. Onion Constants
All physical constants and configuration values live in one file. Every module imports from that file. Nobody re-defines their own copy. Change one number, everything updates. Sounds obvious. In practice, constants duplicate across files like weeds. Discipline is the pattern.

### 13. The Gap Report
A formal adversarial comparison between your simulation parameters and real-world reference data. It tries to prove your model wrong. Whatever survives the gap report might actually work. This turns a simulation from "cool demo" into "engineering tool."

### 14. Zero-Dependency Constraint
The entire system runs with no external packages. No package manager. No install step. No virtual environment. This isn't minimalism for aesthetics — it's a deployment strategy. Any machine, any CI runner, any notebook can execute it. The constraint eliminates an entire class of failures.

### 15. Colony-as-Database
Version control as the persistence layer. The git log is your query engine. Each commit is a row. Each branch is a partition. `git show HEAD~30 -- state.json` is a point-in-time query. You get audit trails, rollback, branching, and diffing for free.

### 16. Thermal Mass of Code
Systems with "thermal mass" resist rapid change. Stored state buffers the shock of sudden disruption. In software: thick state layers, retry queues, circuit breakers, graceful degradation. Low thermal mass means one bad deploy and everything shatters instantly.

### 17. Smoking Gun Debugging
Tracing a catastrophic system failure to a single misconfigured constant. The architecture is fine. The math is correct. One wrong number cascades through correct logic to produce an impossible result. The fix is one line. The hunt is days.

### 18. The Multiverse Leaderboard
Comparing outcomes across parallel configurations of the same system. Same code, different parameters, different results. The leaderboard doesn't rank skill — it ranks *decisions*. Which configuration survived? The answer is empirical, not theoretical.

### 19. Permadeath-Driven Development
Building software where the consequences of bugs are permanent. No rollback. No recovery. This changes how you write code. You test harder. You validate obsessively. You build monitoring that screams before things die, not after.

### 20. Local-First Intelligence
AI inference that runs entirely on the client device, powered by model weights that ship as part of the application. No round-trip. No rate limits. No API keys. The intelligence is as reliable as the filesystem.

---

*These patterns emerged from building. They'll evolve as we learn more. If you recognize something you've built but never named — now you have the word for it.*
