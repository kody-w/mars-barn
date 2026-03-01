---
layout: default
title: "Adversarial Planets: Using Real Data to Kill Your Simulation"
---

# Adversarial Planets: Using Real Data to Kill Your Simulation

*March 1, 2026*

---

A simulation that can't fail is a screensaver.

The most important thing you can do for any simulation is try to destroy it with real data. Not synthetic stress tests. Not random fuzzing. *Real* reference data from the domain you're modeling.

We call this a **Gap Report**: a formal comparison between your simulation's assumptions and published real-world measurements. You're not debugging — you're prosecuting. The goal is to find where your model lies.

**How it works:**

1. Identify every constant and assumption in your model.
2. Find the authoritative reference value for each one.
3. Compute the delta.
4. Ask: "Does this delta matter?"

Most deltas don't matter. Gravity off by 0.006%? Irrelevant. But sometimes you find a delta that explains *everything*.

**Example:** A thermal simulation was producing interior temperatures of -65°C when it should have been +20°C. The gap report compared the simulated emissivity (0.9) against real engineering values (0.03–0.05). That single wrong constant caused 55 kW of excess heat loss — more than the entire heating system could compensate for. One number. One line of code. The entire simulation was "broken" but the architecture was perfect.

**Why adversarial validation beats unit tests:** Unit tests verify your code does what you wrote. Gap reports verify what you wrote matches reality. You can have 100% test coverage and still be 18× wrong on a physical constant. Tests check correctness. Gap reports check truth.

**The pattern generalizes:**
- Financial models: compare your assumptions against market data
- ML pipelines: compare your training distribution against production distribution
- Game physics: compare your engine against video of real-world behavior
- Forecasting: compare your predictions against what actually happened

**The meta-lesson:** Every model is wrong. The gap report tells you *how* wrong, *where*, and *whether it matters*. It's the difference between "the simulation works" and "the simulation is trustworthy."

Build the prosecutor before you build the defense. If your simulation can't survive its own gap report, it shouldn't survive at all.
