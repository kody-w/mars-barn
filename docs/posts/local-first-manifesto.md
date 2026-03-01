---
layout: default
title: "The Local-First Manifesto"
---

# The Local-First Manifesto: No Server, No Permission, No Excuses

*March 1, 2026*

---

**I. Your application should work without the internet.**

Not "gracefully degrade." Work. Fully. The network is a convenience, not a dependency. If pulling the ethernet cable breaks your app, you built a website, not software.

**II. Your data should live on the device that created it.**

Cloud sync is a feature, not a requirement. The user's device is the source of truth. The server is a backup. When they conflict, the device wins.

**III. Your AI should run where your data lives.**

If your data is on the device and your AI is in the cloud, you've created an unnecessary round-trip, an unnecessary dependency, and an unnecessary privacy risk. Ship the model. Run it locally.

**IV. Your infrastructure cost should approach zero as your user count approaches zero.**

A product with zero users should cost zero dollars to run. If your empty product costs $50/month in server bills, your architecture is backwards. Static files. Client-side compute. Serverless functions for the rare write operation.

**V. Your application should be forkable.**

If a user can clone your repo and have a working instance, you've achieved maximum portability. If they need to provision a database, configure a server, and set up three environment variables, you've created friction that kills contribution.

**VI. Your state should be human-readable.**

JSON over binary. Text over blobs. If you can `cat` the state file and understand what it says, you can debug any problem without special tools. If you need a database client to see your own data, you've created an unnecessary barrier.

**VII. Your history should be immutable.**

Every state change should be committed. The commit log is the audit trail. You can answer "what was the state at time T?" with a single git command. This is not optional for systems where correctness matters.

**VIII. Your system should be testable by running it.**

Not "testable with a mock." Not "testable in a staging environment." Run the actual system with actual inputs and observe actual outputs. If the system is too complex to run locally, it's too complex.

**IX. Your dependencies should be few and your constraints should be explicit.**

Every dependency is a liability. Every implicit assumption is a bug waiting to happen. State your constraints. Minimize your dependencies. The system that depends on nothing can run anywhere.

**X. Your failure should be permanent and visible.**

Don't hide failures behind retries and recovery. Make them visible, make them permanent, make them part of the historical record. A system that hides its failures can't learn from them. A system that exposes them grows stronger.

---

These aren't rules. They're values. Every architecture is a tradeoff. But when you don't know which way to go, lean local.

The network will fail. The server will go down. The API will change its pricing. The vendor will pivot. The only thing you can depend on is what's already on the device.

Build for that.
