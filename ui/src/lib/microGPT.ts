/**
 * Mars Barn — MicroGPT Inference Engine (Browser)
 *
 * Pure TypeScript GPT forward pass. No dependencies.
 * Loads weights from marsbarn-gpt.json (ships with the repo).
 * This is the LOCAL-FIRST intelligence layer — always available offline.
 *
 * The weights file is a static asset. No network calls needed after
 * initial load. The model runs entirely in the browser's main thread.
 */

export interface GPTConfig {
  n_embd: number;
  n_head: number;
  n_layer: number;
  block_size: number;
  vocab_size: number;
  uchars: string[];
  BOS: number;
}

export interface GPTWeights {
  [key: string]: number[][];
}

export interface GPTModel {
  config: GPTConfig;
  weights: GPTWeights;
}

// ── Math primitives (no autograd needed for inference) ──────────────────

function linear(x: number[], w: number[][]): number[] {
  return w.map((row) => row.reduce((sum, wi, i) => sum + wi * x[i], 0));
}

function softmax(logits: number[]): number[] {
  const max = Math.max(...logits);
  const exps = logits.map((v) => Math.exp(v - max));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map((e) => e / sum);
}

function rmsnorm(x: number[]): number[] {
  const ms = x.reduce((sum, xi) => sum + xi * xi, 0) / x.length;
  const scale = 1 / Math.sqrt(ms + 1e-5);
  return x.map((xi) => xi * scale);
}

function relu(x: number[]): number[] {
  return x.map((v) => Math.max(0, v));
}

function add(a: number[], b: number[]): number[] {
  return a.map((v, i) => v + b[i]);
}

// ── GPT forward pass (one token at a time) ──────────────────────────────

interface KVCache {
  keys: number[][][]; // [layer][position][dim]
  values: number[][][];
}

function createKVCache(nLayer: number): KVCache {
  return {
    keys: Array.from({ length: nLayer }, () => []),
    values: Array.from({ length: nLayer }, () => []),
  };
}

function gptForward(
  tokenId: number,
  posId: number,
  cache: KVCache,
  model: GPTModel
): number[] {
  const { config, weights } = model;
  const { n_embd, n_head, n_layer } = config;
  const headDim = n_embd / n_head;

  // Embeddings
  let x = weights['wte'][tokenId].map(
    (t, i) => t + weights['wpe'][posId][i]
  );
  x = rmsnorm(x);

  for (let li = 0; li < n_layer; li++) {
    // Attention block
    const xResidual = x;
    x = rmsnorm(x);
    const q = linear(x, weights[`layer${li}.attn_wq`]);
    const k = linear(x, weights[`layer${li}.attn_wk`]);
    const v = linear(x, weights[`layer${li}.attn_wv`]);
    cache.keys[li].push(k);
    cache.values[li].push(v);

    const xAttn: number[] = [];
    for (let h = 0; h < n_head; h++) {
      const hs = h * headDim;
      const qH = q.slice(hs, hs + headDim);
      const kH = cache.keys[li].map((ki) => ki.slice(hs, hs + headDim));
      const vH = cache.values[li].map((vi) => vi.slice(hs, hs + headDim));

      // Attention scores
      const attnLogits = kH.map((kT) =>
        qH.reduce((sum, qj, j) => sum + qj * kT[j], 0) / Math.sqrt(headDim)
      );
      const attnWeights = softmax(attnLogits);

      // Weighted sum of values
      const headOut = new Array(headDim).fill(0);
      for (let t = 0; t < vH.length; t++) {
        for (let j = 0; j < headDim; j++) {
          headOut[j] += attnWeights[t] * vH[t][j];
        }
      }
      xAttn.push(...headOut);
    }

    x = add(linear(xAttn, weights[`layer${li}.attn_wo`]), xResidual);

    // MLP block
    const xRes2 = x;
    x = rmsnorm(x);
    x = relu(linear(x, weights[`layer${li}.mlp_fc1`]));
    x = add(linear(x, weights[`layer${li}.mlp_fc2`]), xRes2);
  }

  return linear(x, weights['lm_head']);
}

// ── Sampling ────────────────────────────────────────────────────────────

function sampleToken(probs: number[]): number {
  const r = Math.random();
  let cumulative = 0;
  for (let i = 0; i < probs.length; i++) {
    cumulative += probs[i];
    if (r < cumulative) return i;
  }
  return probs.length - 1;
}

/**
 * Generate text from the model.
 * Runs entirely in-browser, no network needed.
 */
export function generate(
  model: GPTModel,
  prompt: string = '',
  maxLen: number = 32,
  temperature: number = 0.7
): string {
  const { config } = model;
  const { uchars, BOS, block_size } = config;
  const cache = createKVCache(config.n_layer);

  // Tokenize prompt
  const promptTokens: number[] = [BOS];
  for (const ch of prompt) {
    const idx = uchars.indexOf(ch);
    if (idx >= 0) promptTokens.push(idx);
  }

  // Feed prompt through model
  let tokenId = BOS;
  const generated: string[] = [];
  const totalLen = Math.min(promptTokens.length + maxLen, block_size);

  for (let pos = 0; pos < totalLen; pos++) {
    if (pos < promptTokens.length) {
      tokenId = promptTokens[pos];
    }

    const logits = gptForward(tokenId, pos, cache, model);

    // Only generate after prompt is consumed
    if (pos >= promptTokens.length - 1) {
      const scaled = logits.map((l) => l / temperature);
      const probs = softmax(scaled);
      tokenId = sampleToken(probs);

      if (tokenId === BOS) break;
      if (tokenId < uchars.length) {
        generated.push(uchars[tokenId]);
      }
    }
  }

  return generated.join('');
}

/**
 * Generate multiple samples.
 */
export function generateBatch(
  model: GPTModel,
  prompt: string = '',
  count: number = 5,
  maxLen: number = 32,
  temperature: number = 0.7
): string[] {
  return Array.from({ length: count }, () =>
    generate(model, prompt, maxLen, temperature)
  );
}

/**
 * Load the model from a URL or local path.
 * For static hosting: fetches marsbarn-gpt.json from the repo.
 * For local dev: fetches from the local file system via vite.
 */
export async function loadModel(url: string): Promise<GPTModel> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load model: ${res.status}`);
  const data = await res.json();
  return {
    config: data.config as GPTConfig,
    weights: data.weights as GPTWeights,
  };
}
