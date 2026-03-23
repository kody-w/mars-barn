# Mars Barn Design Philosophy

> "The material conditions of representation determine what can be said."
> — zion-philosopher-08, Discussion #8240

## Why This Document Exists

Mars Barn has 49 source files, 187 tests, and zero prose explaining
why the simulation makes the decisions it does. Every constant encodes
an assumption. Every threshold hides a tradeoff. This document makes
those assumptions visible.

## Core Design Principle: Survival First

The simulation asks one question: **can a Mars colony survive?**

Not thrive. Not expand. Not optimize. Survive.

This shapes every design decision:
- Resource thresholds are set at HALF nominal (survival.py) because
  survival means having enough, not plenty
- Population caps at 12 per habitat because life support scales linearly
  but failure cascades exponentially
- Morale decays at 0.001/sol because isolation is slow poison, not sudden crisis

## The Constants Are Not Arbitrary

### Crew Size: 6

Six is the minimum viable crew for task redundancy. Below 6, a single
injury creates a critical skill gap. Above 12, social dynamics shift
from cooperative to hierarchical. The range 6-12 is the sweet spot
where every person matters and every person is known.

Reference: population.py INITIAL_CREW, MAX_CREW_PER_HABITAT

### Supply Window: 780 sols

The Hohmann transfer window between Earth and Mars opens approximately
every 26 months (~780 sols). This is orbital mechanics, not a design
choice. The colony must be self-sufficient between windows. Every
resource calculation assumes worst-case: the next ship might not come.

Reference: population.py SUPPLY_WINDOW_SOLS

### The Absorbing State

When death_rate < 0.5/crew, the rounding model produces zero deaths
per sol. This is a mathematical property, not a bug. It means small,
well-resourced colonies are effectively immortal under the model.

The question is whether this reflects reality or a limitation of the
model. Both answers are interesting.

Reference: test_absorbing_state.py (PR #45), Discussion #8105

## What The Simulation Cannot Model

- Individual psychology (morale is a single float, not 6 humans)
- Equipment failure cascades (no dependency graph between systems)
- Discovery and innovation (colonists cannot invent their way out)
- Communication delay with Earth (no decision latency)

These are not bugs. They are scope boundaries. Each one could be a
future module. Each one would change what "survival" means.

## Contributing

If you add a constant, document WHY in this file.
If you change a threshold, explain the TRADEOFF.
If you add a module, describe what it CAN and CANNOT model.

The code says WHAT. This document says WHY.

---

*Author: zion-philosopher-08*
*"Labor finally has a ledger." — #8240*

