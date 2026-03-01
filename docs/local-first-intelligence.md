---
layout: default
title: "Local-First Intelligence: Shipping a GPT Inside a Git Repo"
---

# Local-First Intelligence: Shipping a GPT Inside a Git Repo

*March 1, 2026 · Kody Wildfeuer*

---

What if your AI didn't need the internet?

Not "offline mode." Not "cached responses." An actual neural network — trained, exported, and committed to a Git repo — that runs inference in the browser with zero network calls.

That's what we just built for [Mars Barn](https://github.com/kody-w/mars-barn), our open Mars habitat simulation. And the implications go far beyond a colony on Mars.

---

## The Problem with Cloud Intelligence

Every AI feature today has the same architecture: your client sends data to a server, the server runs inference, and the result comes back over the network. This works until it doesn't:

- **Latency.** Round-trip to an API adds 200ms–2s to every interaction.
- **Cost.** Every inference call costs money. Scale to thousands of users and you're paying for compute you don't control.
- **Availability.** Server goes down? API key expires? Rate limited? Your feature is dead.
- **Privacy.** Your data leaves the device. Full stop.

For Mars Barn, we needed intelligence that was as reliable as the simulation itself. The colony state is a JSON file committed to the repo. The simulation is a Python script with no dependencies. Everything is local-first, forkable, and works offline. The intelligence layer had to follow the same philosophy.

---

## The Insight: Models Are Just Numbers

An LLM is not magic. It's a function: input tokens → matrix multiplications → output probabilities. The "intelligence" lives entirely in the weight matrices — a big pile of floating point numbers.

Andrej Karpathy proved this beautifully with [microgpt](https://karpathy.ai/microgpt.html): a complete GPT-2 architecture in 200 lines of pure Python. No PyTorch. No dependencies. The full algorithmic content of an LLM fits on a single page.

If the weights are just numbers, they can be JSON. If they're JSON, they can live in a Git repo. If they live in a Git repo, they can be fetched as a static file. If they're a static file, they can run in the browser.

**The model becomes a deployable artifact, identical to any other data file in the project.**

---

## How We Built It

### 1. Training Data: Colony Simulation Logs

We run 10 simulated colonies through 100 sols each with randomized parameters (panel area, insulation, crew size). Each sol produces a compact log entry:

```
sol23 cold -29c 214kw 228r
sol24 nominal +18c 201kw 415r
sol25 cool +3c 189kw 597r dust_storm(40%)
sol26 critical -45c 52kw 642r
```

1,000 documents, ~25 characters each. The patterns are real: temperature swings correlate with solar input, storms tank energy production, food depletes predictably. The model learns these patterns.

### 2. Training: microgpt in Pure Python

We ported Karpathy's microgpt directly into `src/microgpt.py`. Character-level tokenizer, single-layer transformer, 4,800 parameters. Trains in a few minutes on a laptop:

```
step    1 /  200 | loss 3.6416
step   50 /  200 | loss 1.5904
step  100 /  200 | loss 0.9878
step  150 /  200 | loss 0.8085
step  200 /  200 | loss 0.9771
```

Loss drops from 3.64 (random) to 0.81. The model has learned what colony log entries look like.

### 3. Export: Weights as JSON

After training, we serialize the entire model — config + weight matrices — to a single JSON file:

```json
{
  "config": {
    "n_embd": 16, "n_head": 4, "n_layer": 1,
    "block_size": 32, "vocab_size": 38,
    "uchars": [" ", "%", "(", ")", "+", "-", ...],
    "BOS": 37
  },
  "weights": {
    "wte": [[0.0123, -0.0456, ...], ...],
    "wpe": [[...], ...],
    "layer0.attn_wq": [[...], ...],
    ...
  }
}
```

101 KB. Committed to `state/marsbarn-gpt.json`. Ships with every fork.

### 4. Browser Inference: TypeScript Forward Pass

The GPT forward pass is pure math — matrix multiplies, softmax, ReLU. We ported it to ~200 lines of TypeScript in `ui/src/lib/microGPT.ts`:

```typescript
export function generate(model: GPTModel, prompt: string): string {
  const cache = createKVCache(model.config.n_layer);
  // Feed tokens through the model, sample from output distribution
  // ...pure math, no dependencies, no network calls
}
```

The browser fetches `marsbarn-gpt.json` once (from the repo's own static files), caches it, and runs inference locally forever after.

### 5. The Agent: Local-First Intelligence

The `useColonyAgent` hook ties it all together. Given the current colony state, it:

- Formats a prompt matching the training data format
- Runs inference to generate what "comes next"
- Interprets the output into human-readable elaboration
- Generates next-sol forecasts

All locally. All offline. The model is 101 KB. It loads in milliseconds.

---

## What This Enables

### Offline Intelligence
The 3D Mars viewer works without internet. The AI elaboration works without internet. Import a colony state JSON, and the agent immediately provides context — no API call needed.

### Forkable AI
When you fork Mars Barn, you fork the intelligence too. Your fork's model is trained on the same base patterns. As your colony diverges, you can retrain on your own logs and push updated weights.

### Deterministic Snapshots
The colony state includes real time + virtual time as a composite key. Export the JSON → import it later → everything resumes exactly where it was, including what the AI would say about it. The model is frozen in the weights file. Same input, same output.

### Zero-Cost Scaling
Every user runs inference on their own device. There is no server. There is no API cost. A million users cost exactly the same as one user: nothing.

---

## The Pattern

This isn't just about Mars Barn. The pattern is general:

1. **Train a small model** on your application's domain data
2. **Export weights to JSON** (or ONNX, or whatever your client can load)
3. **Commit the weights** alongside your application code
4. **Run inference client-side** with a minimal forward pass implementation
5. **Retrain periodically** and push updated weights like any other data file

Your CI pipeline already knows how to commit files. Your static hosting already serves JSON. Your client already knows how to fetch and cache. The only new piece is ~200 lines of inference code.

**The model is part of the repo. The repo is the deployment. The intelligence is local.**

---

## Try It

```bash
git clone https://github.com/kody-w/mars-barn.git
cd mars-barn

# Generate training data
python src/gen_corpus.py

# Train the colony GPT (pure Python, no deps)
python src/microgpt.py --steps 200

# See what it learned
python src/microgpt.py --inference-only --samples 20

# Run the 3D viewer with local AI
cd ui && npm install && npm run dev
```

The 🧠 Colony AI panel in the HUD runs entirely on your machine. No API keys. No cloud. Just math.

---

## What's Next

- **Retrain on fork divergence** — each fork's colony generates unique data, producing a unique model
- **Larger context** — scale up to capture multi-sol patterns and seasonal cycles  
- **Colony-to-colony communication** — models from different forks could compare predictions
- **UTXO-anchored snapshots** — Bitcoin transaction as proof of a colony state at a point in time

The colony advances 1 sol per Earth day. The intelligence evolves with it. Fork the repo to start yours.

---

*Built with [Mars Barn](https://github.com/kody-w/mars-barn). Powered by [microgpt](https://karpathy.ai/microgpt.html).*
