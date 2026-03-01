---
layout: default
title: "The JSON File That Runs a World"
---

# The JSON File That Runs a World: State Management at Planetary Scale

*March 1, 2026*

---

```json
{
  "sol": 847,
  "habitat": { "interior_temp_k": 291.3, "stored_energy_kwh": 1247.8 },
  "active_events": [{ "type": "storm", "severity": 0.4, "end_sol": 851 }],
  "stats": { "sols_survived": 847, "storms_survived": 23 }
}
```

This JSON file is a world. Everything that world *is* — its temperature, its energy, its history, its ongoing crises — fits in a few kilobytes of structured data.

**The radical simplicity of state-as-JSON:**

**The file is the truth.** There is no database that the file is derived from. There is no cache that the file is a snapshot of. The file *is* the authoritative state. When you read it, you see reality. When you modify it, you change reality.

**The file is human-readable.** Open it in any text editor. You don't need a database client, an admin panel, or a query language. You can `cat` the file and understand the system's state. Try that with a PostgreSQL database.

**The file is diffable.** `git diff` shows you exactly what changed between any two states. Not "the database was modified" — *which field changed from what to what*. This is free when your state is text.

**The file is portable.** Email it. Slack it. Upload it. Download it. Copy it to a USB drive. The recipient can reconstruct the entire world by loading one file. No database dump, no migration scripts, no environment setup.

**The file is forkable.** Copy it, modify it, diverge. You now have two worlds with shared history but different futures. This is literally how version control works, applied to state.

**The objections and responses:**

*"It doesn't scale."* A planetary simulation with 847 sols of history, active events, habitat stats, and a log of the last 100 entries is 4KB. What are you storing that's bigger than a planet?

*"What about concurrent writes?"* Use git merge strategies. Or don't have concurrent writes — most systems are single-writer at the state level. The simulation advances one tick at a time.

*"What about queries?"* `jq '.habitat.stored_energy_kwh' state.json` is a query. `python -c 'import json; d=json.load(open("state.json")); print(d["stats"]["sols_survived"])'` is a query. You don't need SQL for 4KB of data.

*"What about migrations?"* Add new fields with defaults. Remove old fields when nothing reads them. JSON is schemaless. This is a feature.

**When JSON isn't enough:** When you need relational queries across many entities. When you need transactions with ACID guarantees. When your state exceeds a few megabytes. Then yes, use a database.

**When JSON is plenty:** When your state is a single document. When you have one writer. When your reads are "give me the whole thing." When human readability matters. When portability matters.

Most systems are the second case pretending to be the first.
