---
layout: default
title: "The Leaderboard Nobody Runs"
---

# The Leaderboard Nobody Runs: Decentralized Competition From Public Repos

*March 1, 2026*

---

Traditional leaderboards require infrastructure: a server to collect scores, a database to store them, an API to submit results, and an admin to prevent cheating.

What if the leaderboard was emergent?

**Decentralized leaderboards** require zero shared infrastructure. Each participant publishes their results in their own public repository. The leaderboard is computed by anyone who wants to compute it — scrape the fork graph, read each fork's state file, rank by whatever metric you want.

**No submission API.** You don't submit your score. You commit your state. Your repo *is* your submission.

**No central authority.** There's no leaderboard server to go down, no admin to gatekeep, no API key to manage. The data is public. Anyone can build a ranking.

**No cheating prevention needed (mostly).** The simulation code is open source. If you modify the physics to make your system immortal, the diff is visible. Fork graph analysis shows exactly what you changed. The deterrent isn't cryptography — it's transparency.

**Multiple rankings coexist.** Since there's no official leaderboard, anyone can rank by different criteria. Survival duration. Energy efficiency. Minimum viable parameters. Longest storm survived. Each ranking tells a different story about what "good" means.

**The pattern generalizes to:**
- **Open source benchmarks.** Each participant runs the benchmark in their own CI and publishes results in their repo.
- **Distributed science.** Research groups publish results in their own repos; meta-analyses aggregate them.
- **Competitive configurations.** Teams tune the same system with different parameters; the fork graph is the experiment log.

**The philosophical insight:** A leaderboard is just a view over distributed data. You don't need to centralize the data to centralize the view. If every participant already has a public data source, the leaderboard is a query — not a service.

Stop building leaderboard servers. Start reading public repos.
