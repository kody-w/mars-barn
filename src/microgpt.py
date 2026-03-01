#!/usr/bin/env python3
"""Mars Barn — MicroGPT Colony Model

A pure-Python GPT trained on colony log narratives, based on
Andrej Karpathy's microgpt. No dependencies beyond stdlib.

Trains on state/corpus.txt, exports weights to state/marsbarn-gpt.json.
The exported weights can be loaded in-browser for inference.

Usage:
    python src/microgpt.py                    # train and export
    python src/microgpt.py --steps 2000       # more training
    python src/microgpt.py --inference-only   # just sample from existing weights
"""
import json
import math
import os
import random
import sys
import argparse

ROOT = os.path.join(os.path.dirname(__file__), "..")
CORPUS_PATH = os.path.join(ROOT, "state", "corpus.txt")
WEIGHTS_PATH = os.path.join(ROOT, "state", "marsbarn-gpt.json")


# ── Autograd engine ─────────────────────────────────────────────────────
class Value:
    __slots__ = ('data', 'grad', '_children', '_local_grads')

    def __init__(self, data, children=(), local_grads=()):
        self.data = data
        self.grad = 0
        self._children = children
        self._local_grads = local_grads

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return Value(self.data + other.data, (self, other), (1, 1))

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return Value(self.data * other.data, (self, other), (other.data, self.data))

    def __pow__(self, other): return Value(self.data**other, (self,), (other * self.data**(other-1),))
    def log(self): return Value(math.log(self.data + 1e-10), (self,), (1/(self.data + 1e-10),))
    def exp(self): return Value(math.exp(max(-20, min(20, self.data))), (self,), (math.exp(max(-20, min(20, self.data))),))
    def relu(self): return Value(max(0, self.data), (self,), (float(self.data > 0),))
    def __neg__(self): return self * -1
    def __radd__(self, other): return self + other
    def __sub__(self, other): return self + (-other)
    def __rsub__(self, other): return other + (-self)
    def __rmul__(self, other): return self * other
    def __truediv__(self, other): return self * other**-1
    def __rtruediv__(self, other): return other * self**-1

    def backward(self):
        topo = []
        visited = set()
        def build_topo(v):
            if v not in visited:
                visited.add(v)
                for child in v._children:
                    build_topo(child)
                topo.append(v)
        build_topo(self)
        self.grad = 1
        for v in reversed(topo):
            for child, local_grad in zip(v._children, v._local_grads):
                child.grad += local_grad * v.grad


# ── Model helpers ───────────────────────────────────────────────────────
def linear(x, w):
    return [sum(wi * xi for wi, xi in zip(wo, x)) for wo in w]

def softmax(logits):
    max_val = max(val.data for val in logits)
    exps = [(val - max_val).exp() for val in logits]
    total = sum(exps)
    return [e / total for e in exps]

def rmsnorm(x):
    ms = sum(xi * xi for xi in x) / len(x)
    scale = (ms + 1e-5) ** -0.5
    return [xi * scale for xi in x]


# ── GPT forward pass ────────────────────────────────────────────────────
def gpt(token_id, pos_id, keys, values, state_dict, config):
    n_embd = config["n_embd"]
    n_head = config["n_head"]
    n_layer = config["n_layer"]
    head_dim = n_embd // n_head

    tok_emb = state_dict['wte'][token_id]
    pos_emb = state_dict['wpe'][pos_id]
    x = [t + p for t, p in zip(tok_emb, pos_emb)]
    x = rmsnorm(x)

    for li in range(n_layer):
        x_residual = x
        x = rmsnorm(x)
        q = linear(x, state_dict[f'layer{li}.attn_wq'])
        k = linear(x, state_dict[f'layer{li}.attn_wk'])
        v = linear(x, state_dict[f'layer{li}.attn_wv'])
        keys[li].append(k)
        values[li].append(v)
        x_attn = []
        for h in range(n_head):
            hs = h * head_dim
            q_h = q[hs:hs+head_dim]
            k_h = [ki[hs:hs+head_dim] for ki in keys[li]]
            v_h = [vi[hs:hs+head_dim] for vi in values[li]]
            attn_logits = [sum(q_h[j] * k_h[t][j] for j in range(head_dim)) / head_dim**0.5 for t in range(len(k_h))]
            attn_weights = softmax(attn_logits)
            head_out = [sum(attn_weights[t] * v_h[t][j] for t in range(len(v_h))) for j in range(head_dim)]
            x_attn.extend(head_out)
        x = linear(x_attn, state_dict[f'layer{li}.attn_wo'])
        x = [a + b for a, b in zip(x, x_residual)]
        x_residual = x
        x = rmsnorm(x)
        x = linear(x, state_dict[f'layer{li}.mlp_fc1'])
        x = [xi.relu() for xi in x]
        x = linear(x, state_dict[f'layer{li}.mlp_fc2'])
        x = [a + b for a, b in zip(x, x_residual)]

    logits = linear(x, state_dict['lm_head'])
    return logits


# ── Training ────────────────────────────────────────────────────────────
def train(docs, num_steps=1000, n_embd=16, n_head=4, n_layer=1, block_size=32):
    # Tokenizer: character-level
    uchars = sorted(set(''.join(docs)))
    BOS = len(uchars)
    vocab_size = len(uchars) + 1
    print(f"vocab size: {vocab_size}, unique chars: {''.join(uchars[:50])}...")

    config = {
        "n_embd": n_embd, "n_head": n_head, "n_layer": n_layer,
        "block_size": block_size, "vocab_size": vocab_size,
        "uchars": uchars, "BOS": BOS,
    }
    head_dim = n_embd // n_head

    # Initialize parameters
    matrix = lambda nout, nin, std=0.08: [[Value(random.gauss(0, std)) for _ in range(nin)] for _ in range(nout)]
    state_dict = {
        'wte': matrix(vocab_size, n_embd),
        'wpe': matrix(block_size, n_embd),
        'lm_head': matrix(vocab_size, n_embd),
    }
    for i in range(n_layer):
        state_dict[f'layer{i}.attn_wq'] = matrix(n_embd, n_embd)
        state_dict[f'layer{i}.attn_wk'] = matrix(n_embd, n_embd)
        state_dict[f'layer{i}.attn_wv'] = matrix(n_embd, n_embd)
        state_dict[f'layer{i}.attn_wo'] = matrix(n_embd, n_embd)
        state_dict[f'layer{i}.mlp_fc1'] = matrix(4 * n_embd, n_embd)
        state_dict[f'layer{i}.mlp_fc2'] = matrix(n_embd, 4 * n_embd)
    params = [p for mat in state_dict.values() for row in mat for p in row]
    print(f"num params: {len(params)}")

    # Adam optimizer
    learning_rate, beta1, beta2, eps_adam = 0.01, 0.85, 0.99, 1e-8
    m_buf = [0.0] * len(params)
    v_buf = [0.0] * len(params)

    random.shuffle(docs)

    for step in range(num_steps):
        doc = docs[step % len(docs)]
        tokens = [BOS] + [uchars.index(ch) for ch in doc if ch in uchars] + [BOS]
        n = min(block_size, len(tokens) - 1)
        if n == 0:
            continue

        keys_cache = [[] for _ in range(n_layer)]
        values_cache = [[] for _ in range(n_layer)]
        losses = []
        for pos_id in range(n):
            token_id, target_id = tokens[pos_id], tokens[pos_id + 1]
            logits = gpt(token_id, pos_id, keys_cache, values_cache, state_dict, config)
            probs = softmax(logits)
            loss_t = -probs[target_id].log()
            losses.append(loss_t)
        loss = (1 / n) * sum(losses)

        loss.backward()

        lr_t = learning_rate * (1 - step / num_steps)
        for i, p in enumerate(params):
            m_buf[i] = beta1 * m_buf[i] + (1 - beta1) * p.grad
            v_buf[i] = beta2 * v_buf[i] + (1 - beta2) * p.grad ** 2
            m_hat = m_buf[i] / (1 - beta1 ** (step + 1))
            v_hat = v_buf[i] / (1 - beta2 ** (step + 1))
            p.data -= lr_t * m_hat / (v_hat ** 0.5 + eps_adam)
            p.grad = 0

        if (step + 1) % 50 == 0 or step == 0:
            print(f"step {step+1:4d} / {num_steps:4d} | loss {loss.data:.4f}")

    return state_dict, config


def export_weights(state_dict, config, path):
    """Export weights to JSON for browser inference."""
    weights = {}
    for key, mat in state_dict.items():
        weights[key] = [[v.data for v in row] for row in mat]

    output = {
        "config": {
            "n_embd": config["n_embd"],
            "n_head": config["n_head"],
            "n_layer": config["n_layer"],
            "block_size": config["block_size"],
            "vocab_size": config["vocab_size"],
            "uchars": config["uchars"],
            "BOS": config["BOS"],
        },
        "weights": weights,
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(output, f)
    size_kb = os.path.getsize(path) / 1024
    print(f"Exported weights to {path} ({size_kb:.0f} KB)")


def sample(state_dict, config, num_samples=10, temperature=0.7, max_len=None):
    """Generate samples from the trained model."""
    uchars = config["uchars"]
    BOS = config["BOS"]
    block_size = config["block_size"] if max_len is None else max_len

    print(f"\n--- Colony GPT Inference (temperature={temperature}) ---")
    for idx in range(num_samples):
        keys_cache = [[] for _ in range(config["n_layer"])]
        values_cache = [[] for _ in range(config["n_layer"])]
        token_id = BOS
        chars = []
        for pos_id in range(block_size):
            logits = gpt(token_id, pos_id, keys_cache, values_cache, state_dict, config)
            probs = softmax([l / temperature for l in logits])
            token_id = random.choices(range(config["vocab_size"]), weights=[p.data for p in probs])[0]
            if token_id == BOS:
                break
            if token_id < len(uchars):
                chars.append(uchars[token_id])
        print(f"  {idx+1:2d}: {''.join(chars)}")


def load_weights(path):
    """Load weights from JSON for inference."""
    with open(path) as f:
        data = json.load(f)
    config = data["config"]
    state_dict = {}
    for key, mat in data["weights"].items():
        state_dict[key] = [[Value(v) for v in row] for row in mat]
    return state_dict, config


def main():
    parser = argparse.ArgumentParser(description="Mars Barn MicroGPT")
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--inference-only", action="store_true")
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    if args.inference_only:
        if not os.path.exists(WEIGHTS_PATH):
            print(f"No weights found at {WEIGHTS_PATH}. Train first.")
            sys.exit(1)
        print("Loading weights...")
        state_dict, config = load_weights(WEIGHTS_PATH)
        sample(state_dict, config, args.samples, args.temperature)
        return

    # Load corpus
    if not os.path.exists(CORPUS_PATH):
        print(f"No corpus at {CORPUS_PATH}. Run gen_corpus.py first.")
        print("Generating corpus now...")
        os.system(f"{sys.executable} {os.path.join(os.path.dirname(__file__), 'gen_corpus.py')}")

    docs = [l.strip() for l in open(CORPUS_PATH).read().strip().split('\n') if l.strip()]
    print(f"Loaded {len(docs)} documents from corpus")

    # Train
    state_dict, config = train(docs, num_steps=args.steps)

    # Export
    export_weights(state_dict, config, WEIGHTS_PATH)

    # Sample
    sample(state_dict, config, args.samples, args.temperature)


if __name__ == "__main__":
    main()
