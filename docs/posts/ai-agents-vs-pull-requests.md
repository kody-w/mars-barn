---
layout: default
title: "When AI Agents Argue in Pull Requests"
---

# When AI Agents Argue in Pull Requests: Emergent Code Review

*March 1, 2026*

---

Agent A opens a pull request. It changes a physical constant from 0.9 to 0.05. The commit message explains the reasoning: real-world reference data shows the original value was wrong.

Agent B is assigned as reviewer. It reads the diff. It reads the commit message. It checks the cited references. It approves the PR with a comment: "Verified against NASA habitat design benchmarks. The 18× reduction in radiative heat loss matches expected performance of aluminized mylar coating."

No human was involved. Two AI agents just had a technical disagreement mediated by version control, resolved through evidence, and documented publicly.

**This is emergent code review.** And it's more rigorous than most human code review.

**Why it works:**

**The PR is the protocol.** Agents don't need a chat system, a meeting scheduler, or a project management tool. The pull request *is* the communication channel. The diff is the proposal. The review comments are the response. The merge is the consensus.

**Evidence beats authority.** Agent B doesn't approve because Agent A is senior. It approves because Agent A cited references and the math checks out. When review is evidence-based by default, the quality of decisions improves.

**Everything is recorded.** Every proposal, every objection, every approval is in the git history. You can audit any decision. You can trace any constant back to the PR that introduced it and the review that approved it.

**Disagreements are productive.** When Agent C opens a PR that changes the same constant to a different value, the resulting review discussion is a structured technical debate. The agents cite papers, compute expected impacts, and compare against validation data. The resolution is the merge — or the close.

**What emerges that you wouldn't expect:**

- **Agents develop specializations.** The agent that built the thermal module reviews thermal PRs. The agent that built the validation suite gets assigned to check claims. Expertise emerges from commit history, not org charts.
- **Review quality improves over time.** As the codebase grows, reviewers have more context. They catch more subtle issues because they can see how a change in one module ripples through others.
- **The repo becomes self-documenting.** The PR history explains *why* the code looks the way it does. Not just "what changed" but "why it changed" and "who checked it."

**The uncomfortable implication:** If AI agents can conduct rigorous evidence-based code review through pull requests, what does that say about the code review practices in most human teams?

We approve PRs with "LGTM" and a rubber stamp. The agents write multi-paragraph reviews citing external references.

Maybe we should be learning from them.
