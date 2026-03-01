---
layout: default
title: "Zero-Dollar Infrastructure: Running a Planetary Simulation With No Server"
---

# Zero-Dollar Infrastructure: Running a Planetary Simulation With No Server

*March 1, 2026*

---

Here is the complete infrastructure bill for running a planetary simulation with a 3D viewer, AI intelligence layer, daily automated advancement, and static hosting:

**$0.00/month.**

No cloud provider. No Kubernetes. No database server. No Redis. No message queue. No CDN subscription. No monitoring service. No PagerDuty.

Here's the stack:

| Component | Service | Cost |
|-----------|---------|------|
| Compute (simulation) | GitHub Actions (cron) | Free |
| Database | `state.json` in git | Free |
| API | GitHub raw content | Free |
| Static hosting | GitHub Pages | Free |
| AI inference | Client-side (101KB weights) | Free |
| CI/CD | GitHub Actions | Free |
| Monitoring | Git log + commit messages | Free |

**How this works:**

**Compute:** A GitHub Action runs once per day. It executes a Python script, advances the simulation one step, and commits the result. Total runtime: ~5 seconds. Monthly usage: ~2.5 minutes of the 2,000 free minutes.

**Database:** The state file is committed to the repo. Reading is a raw GitHub fetch. Writing is a git commit. History is `git log`. Point-in-time queries are `git show <commit> -- state.json`. There is no schema migration because JSON is schemaless. There is no connection pooling because there are no connections.

**API:** Clients fetch `https://raw.githubusercontent.com/<user>/<repo>/main/state/state.json`. This is a CDN-backed, globally distributed read API with caching headers. You didn't build it. You didn't deploy it. It's just there.

**AI:** The model weights are a 101KB JSON file served as a static asset. Inference runs in the browser. The user's CPU is the compute. You don't pay for it. It doesn't scale down. It doesn't have cold starts.

**The catch:** This architecture has real limitations. Write throughput is limited to git commit speed (~1/minute). There's no real-time push (clients poll). Multi-writer conflicts require merge strategies. You can't run SQL queries against a JSON file.

**When it's appropriate:** Systems with low write frequency and high read frequency. Time-stepped simulations. Personal dashboards. Status pages. Portfolio sites with dynamic data. Any system where "updated once a day" is fast enough.

**When it's not:** Chat applications. Multiplayer games. Financial trading. Anything requiring sub-second writes or real-time sync.

**The point isn't that this replaces cloud infrastructure.** The point is that *most projects don't need cloud infrastructure* and assume they do because nobody showed them the alternative.

Your side project doesn't need a database server. Your simulation doesn't need AWS. Your portfolio site doesn't need a backend.

It needs a JSON file and a cron job.
