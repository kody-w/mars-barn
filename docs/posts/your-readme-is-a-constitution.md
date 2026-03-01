---
layout: default
title: "Your README Is a Constitution"
---

# Your README Is a Constitution: Governance Through Documentation

*March 1, 2026*

---

When there's no boss, no hierarchy, and no meetings, what governs the project?

The README.

In a barn-raising architecture — where independent agents build modules and coordinate through pull requests — the README becomes the constitution. It defines what the system is, what constraints it operates under, and what's in scope. Agents read it to understand what to build. Reviewers read it to decide what to merge.

**The README as law:**

**Constraints are constitutional limits.** "Python stdlib only — no pip installs." This isn't a suggestion. It's a law. Any PR that imports an external package is unconstitutional and will be rejected. The constraint exists in the README, not in a CI rule (though the CI rule should enforce it).

**Architecture is separation of powers.** "Each module is one file." This divides the codebase into jurisdictions. The terrain module has authority over terrain generation. The thermal module has authority over heat flow. Neither can encroach on the other's domain without a PR (a constitutional amendment).

**The contributing guide is the legislative process.** "Fork → Branch → PR" is the process for proposing changes. "Open an issue first for large changes" is the process for proposing new laws. The process is documented, public, and applies equally to all contributors.

**What makes a good README-as-constitution:**

**1. State the purpose.** Not what the code does — what the *project* aims to achieve. This guides every PR review. "Does this PR advance the stated purpose?"

**2. List the constraints explicitly.** Don't assume contributors will infer the rules from the code. Write them down. Constraints are the most important lines in the README because they determine what *can't* be built.

**3. Define the architecture.** Not every implementation detail — just the structure. The dependency graph. The module boundaries. The data flow. This is the system's geography, and everyone needs the same map.

**4. Describe the process.** How do changes get proposed? How do they get reviewed? How do they get merged? The process is what makes the system governable rather than chaotic.

**When the README disagrees with the code, the README wins.** The code might have drifted. A PR might have slipped in something that violates a constraint. The README is the authoritative intent. The code is the current implementation. When they diverge, fix the code.

**The deeper insight:** Every open source project is a miniature society. It has citizens (contributors), laws (constraints), a constitution (README), a legislative process (PRs), and a judiciary (reviewers). The successful projects are the ones that govern themselves well.

Your README isn't documentation. It's the founding document of a small society. Write it accordingly.
