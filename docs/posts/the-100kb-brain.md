---
layout: default
title: "The 100KB Brain: What Fits Inside a Neural Network Smaller Than a JPEG"
---

# The 100KB Brain: What Fits Inside a Neural Network Smaller Than a JPEG

*March 1, 2026*

---

Your average smartphone photo is 3MB. A small JPEG is 200KB. The neural network we trained to understand colony operations is 101KB.

**One hundred and one kilobytes.** 4,800 parameters. A single-layer transformer with 4 attention heads and a 16-dimensional embedding space. Trained in minutes on a laptop. And it generates plausible system state predictions.

This seems impossible until you realize what "intelligence" actually requires for a domain-specific task: not much.

**The model doesn't need to know everything.** It needs to know the patterns in *your* data. A colony log has maybe 30 unique characters. The sequences are short. The patterns are strong: temperatures correlate with solar input, storms reduce energy, food depletes linearly. A tiny model captures these patterns because the patterns are simple.

**The math is the same regardless of size.** The 100KB model uses the exact same forward pass as GPT-4: embeddings → attention → MLP → softmax. The attention mechanism is identical. The backpropagation algorithm is identical. The difference is scale: 4,800 parameters vs. hundreds of billions. The algorithm doesn't care.

**What this means for you:**

1. **Domain-specific tasks don't need foundation models.** If your data has strong patterns and limited vocabulary, a tiny model trained on your data will outperform a general model prompted with your data. It *knows* your domain. The big model is *guessing* about your domain.

2. **Client-side inference is free.** 101KB loads in milliseconds. The forward pass runs in the browser's main thread without blocking. No GPU needed. No WebAssembly. No ONNX runtime. Just JavaScript arithmetic.

3. **The weights are version-controlled.** The model evolves with your data. Retrain weekly, commit the new weights, push. Users get updated intelligence the same way they get updated code: `git pull`.

4. **Privacy is structural, not promised.** The data never leaves the device because there's no server to send it to. This isn't a privacy policy — it's an architecture. You can't leak what you don't transmit.

**The uncomfortable question:** How many of the AI features you're building actually need a 70B parameter model behind an API? How many of them could run on 100KB of weights committed to the repo?

More than you think.
