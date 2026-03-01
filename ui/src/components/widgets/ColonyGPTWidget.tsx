"use client";

import { useState, useCallback, useEffect } from 'react';
import { Brain } from 'lucide-react';

interface GPTConfig {
    n_embd: number;
    n_head: number;
    n_layer: number;
    block_size: number;
    vocab_size: number;
    uchars: string[];
    BOS: number;
}

interface GPTWeights {
    config: GPTConfig;
    weights: Record<string, number[][]>;
}

function linear(x: number[], w: number[][]): number[] {
    return w.map(wo => wo.reduce((sum, wi, i) => sum + wi * x[i], 0));
}

function softmax(logits: number[]): number[] {
    const max = Math.max(...logits);
    const exps = logits.map(v => Math.exp(v - max));
    const sum = exps.reduce((a, b) => a + b, 0);
    return exps.map(e => e / sum);
}

function rmsnorm(x: number[]): number[] {
    const ms = x.reduce((s, xi) => s + xi * xi, 0) / x.length;
    const scale = 1 / Math.sqrt(ms + 1e-5);
    return x.map(xi => xi * scale);
}

function gptForward(
    tokenId: number, posId: number,
    keys: number[][][], values: number[][][],
    w: Record<string, number[][]>, c: GPTConfig
): number[] {
    const headDim = c.n_embd / c.n_head;
    let x = w['wte'][tokenId].map((t, i) => t + w['wpe'][posId][i]);
    x = rmsnorm(x);

    for (let li = 0; li < c.n_layer; li++) {
        const xRes = [...x];
        x = rmsnorm(x);
        const q = linear(x, w[`layer${li}.attn_wq`]);
        const k = linear(x, w[`layer${li}.attn_wk`]);
        const v = linear(x, w[`layer${li}.attn_wv`]);
        keys[li].push(k);
        values[li].push(v);

        const xAttn: number[] = [];
        for (let h = 0; h < c.n_head; h++) {
            const hs = h * headDim;
            const qH = q.slice(hs, hs + headDim);
            const kH = keys[li].map(ki => ki.slice(hs, hs + headDim));
            const vH = values[li].map(vi => vi.slice(hs, hs + headDim));
            const attnLogits = kH.map(kt =>
                qH.reduce((s, qi, j) => s + qi * kt[j], 0) / Math.sqrt(headDim)
            );
            const attnW = softmax(attnLogits);
            for (let j = 0; j < headDim; j++) {
                xAttn.push(vH.reduce((s, vt, t) => s + attnW[t] * vt[j], 0));
            }
        }
        x = linear(xAttn, w[`layer${li}.attn_wo`]);
        x = x.map((v, i) => v + xRes[i]);

        const xRes2 = [...x];
        x = rmsnorm(x);
        x = linear(x, w[`layer${li}.mlp_fc1`]).map(v => Math.max(0, v));
        x = linear(x, w[`layer${li}.mlp_fc2`]);
        x = x.map((v, i) => v + xRes2[i]);
    }
    return linear(x, w['lm_head']);
}

function sample(weights: GPTWeights, temperature = 0.7, maxLen = 64): string {
    const { config, weights: w } = weights;
    const keys: number[][][] = Array.from({ length: config.n_layer }, () => []);
    const values: number[][][] = Array.from({ length: config.n_layer }, () => []);
    let tokenId = config.BOS;
    const chars: string[] = [];

    for (let pos = 0; pos < Math.min(maxLen, config.block_size); pos++) {
        const logits = gptForward(tokenId, pos, keys, values, w, config);
        const probs = softmax(logits.map(l => l / temperature));
        const r = Math.random();
        let cumulative = 0;
        tokenId = config.vocab_size - 1;
        for (let i = 0; i < probs.length; i++) {
            cumulative += probs[i];
            if (r < cumulative) { tokenId = i; break; }
        }
        if (tokenId === config.BOS) break;
        if (tokenId < config.uchars.length) chars.push(config.uchars[tokenId]);
    }
    return chars.join('');
}

export default function ColonyGPTWidget() {
    const [weights, setWeights] = useState<GPTWeights | null>(null);
    const [samples, setSamples] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        fetch('/api/live')
            .then(() => fetch('/state/marsbarn-gpt.json'))
            .catch(() => fetch('https://raw.githubusercontent.com/kody-w/mars-barn/main/state/marsbarn-gpt.json'))
            .then(r => {
                if (!r.ok) throw new Error('No weights');
                return r.json();
            })
            .then((data: GPTWeights) => {
                setWeights(data);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, []);

    const generate = useCallback(() => {
        if (!weights) return;
        setGenerating(true);
        setTimeout(() => {
            const newSamples = Array.from({ length: 5 }, () => sample(weights, 0.7));
            setSamples(newSamples);
            setGenerating(false);
        }, 10);
    }, [weights]);

    if (loading) return <div className="h-full flex items-center justify-center text-slate-500">Loading colony model...</div>;
    if (!weights) return <div className="h-full flex items-center justify-center text-slate-500">No microGPT weights found</div>;

    return (
        <div className="flex flex-col h-full gap-3">
            <button
                onClick={generate}
                disabled={generating}
                className="flex items-center gap-2 px-3 py-2 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/30 transition-colors text-sm font-mono disabled:opacity-50"
            >
                <Brain size={14} />
                {generating ? 'Generating...' : 'Generate Colony Logs'}
            </button>
            <div className="flex-1 overflow-y-auto pr-2 space-y-2">
                {samples.length === 0 && (
                    <p className="text-xs text-slate-500 italic">Click generate to sample from the colony's microGPT — a {weights.config.vocab_size}-token model trained on colony history.</p>
                )}
                {samples.map((s, i) => (
                    <div key={i} className="p-2 rounded bg-white/5 border border-white/5 text-xs font-mono text-emerald-300/80">
                        {s || <span className="text-slate-600">&lt;empty&gt;</span>}
                    </div>
                ))}
            </div>
            <div className="text-[10px] text-slate-600 font-mono">
                {weights.config.n_layer}L / {weights.config.n_head}H / {weights.config.n_embd}D — {weights.config.vocab_size} tokens
            </div>
        </div>
    );
}
