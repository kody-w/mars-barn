---
layout: default
title: "Permadeath-Driven Development"
---

# Permadeath-Driven Development: What Software Learns When Failure Is Forever

*March 1, 2026*

---

In most software, failure is temporary. The server crashes, you restart it. The deploy breaks, you roll back. The database corrupts, you restore from backup. Failure is an inconvenience, not a consequence.

Now imagine none of that exists. When the system fails, it stays failed. No rollback. No restore. No retry. The state at the moment of failure is the final state, permanently committed to version control, visible to everyone.

**This is permadeath-driven development.** And it fundamentally changes how you build things.

**What changes:**

**1. You test before you ship.** Not "we should write more tests" — you *actually* write them, because the first production failure is the last. The validation suite becomes the most important code in the repository. It runs before every state transition. It blocks the transition if anything looks wrong.

**2. You build monitoring that warns, not alerts.** In a permadeath system, an alert that fires after the system dies is useless. You need *predictive* monitoring — signals that detect the trajectory toward failure before it arrives. "Energy reserves declining at 15%/day, zero in 6 days" is useful. "Energy reserves reached zero" is a eulogy.

**3. You design for graceful degradation.** A system that goes from "working" to "dead" in one tick has no thermal mass. A robust system has intermediate states: nominal → strained → degraded → critical → dead. Each state reduces functionality but preserves life. The strained system sheds non-essential work. The critical system focuses solely on survival.

**4. Recovery isn't in your toolbox.** You can't design for recovery because recovery doesn't exist. This forces you to design for *prevention*. Every component gets defensive. Every input is validated. Every assumption is checked. The paranoia is productive.

**5. Post-mortems are public.** When a system dies, the entire death is recorded in version control. The state before failure. The state at failure. The commit that advanced to failure. Anyone can reconstruct what happened. The post-mortem writes itself from the git log.

**The philosophical argument:** Most production software pretends failure is impossible until it happens, then pretends it never happened after it's fixed. Permadeath forces honesty. The system's history includes its failures, permanently and publicly.

**Where this pattern applies beyond simulations:** Any system where correctness matters more than uptime. Blockchain validators. Medical device firmware. Autonomous vehicle controllers. Orbital mechanics. These are all permadeath systems — they just don't call it that.

The question to ask your team: "If we couldn't roll back, would we ship this?"

If the answer is no, maybe you shouldn't be shipping it anyway.
