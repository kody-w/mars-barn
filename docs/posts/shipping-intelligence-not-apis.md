---
layout: default
title: "Shipping Intelligence, Not APIs"
---

# Shipping Intelligence, Not APIs: The End of the Inference Endpoint

*March 1, 2026*

---

The dominant pattern for AI in applications looks like this:

```
Client → HTTP → Load Balancer → API Gateway → GPU Server → Model → Response → Client
```

Every link in that chain is a failure point. Every link adds latency. Every link costs money. And the whole thing falls over when the GPU server is busy, the API key expires, or the vendor changes their pricing.

There's another way:

```
Client → Local Weights → Math → Response
```

**Ship the model. Not the API.**

**What "shipping intelligence" means:** The trained model weights are a static file — JSON, ONNX, TensorFlow Lite, whatever your client can parse. You commit the file to your repository. The client downloads it once. Inference runs locally. Forever. Offline. Free.

**When the model is 100KB, this is obvious.** But the pattern works at larger scales than you'd think:

| Model Size | Use Case | Platform |
|-----------|----------|----------|
| 100KB | Pattern completion, simple prediction | Any browser, any device |
| 1-10MB | Text classification, sentiment, NER | Mobile apps, Electron |
| 50-200MB | Image classification, small language models | Desktop, modern mobile |
| 1-2GB | Whisper (speech), LLaMA-tiny | Desktop with WebGPU |

**The economics flip entirely.**

With an API: your costs scale linearly with users. 1,000 users making 10 requests/day = 300,000 inference calls/month. At $0.01/call, that's $3,000/month.

With shipped weights: your costs are zero regardless of users. The user's device is the GPU. A million users cost the same as one user: the cost of hosting a static file.

**What you give up:**
- Model updates require a new release (but so does any bug fix)
- Large models won't fit on all devices (but most tasks don't need large models)
- No server-side logging of inferences (which is a *feature* for privacy)

**What you gain:**
- Zero latency (inference is local)
- Zero cost per inference
- Works offline
- Works when the API vendor goes down
- Works when you stop paying
- Works when the internet is slow
- Privacy by architecture, not by policy

**The question for every AI feature:** Does this model *need* to run on a server? Or does it need to run on a server because that's how everyone does it?

Ship the weights. Kill the endpoint. Your users will never notice the difference — except that it's faster, cheaper, and always works.
