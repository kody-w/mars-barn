import { useState, useCallback, useEffect } from 'react';
import { Brain, FastForward, BarChart3 } from 'lucide-react';

// ── GPT inference types & functions (unchanged) ────────────────────────

interface GPTConfig {
    n_embd: number; n_head: number; n_layer: number;
    block_size: number; vocab_size: number; uchars: string[]; BOS: number;
}
interface GPTWeights { config: GPTConfig; weights: Record<string, number[][]>; }

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
        const xRes = [...x]; x = rmsnorm(x);
        const q = linear(x, w[`layer${li}.attn_wq`]);
        const k = linear(x, w[`layer${li}.attn_wk`]);
        const v = linear(x, w[`layer${li}.attn_wv`]);
        keys[li].push(k); values[li].push(v);
        const xAttn: number[] = [];
        for (let h = 0; h < c.n_head; h++) {
            const hs = h * headDim;
            const qH = q.slice(hs, hs + headDim);
            const kH = keys[li].map(ki => ki.slice(hs, hs + headDim));
            const vH = values[li].map(vi => vi.slice(hs, hs + headDim));
            const attnLogits = kH.map(kt => qH.reduce((s, qi, j) => s + qi * kt[j], 0) / Math.sqrt(headDim));
            const attnW = softmax(attnLogits);
            for (let j = 0; j < headDim; j++) xAttn.push(vH.reduce((s, vt, t) => s + attnW[t] * vt[j], 0));
        }
        x = linear(xAttn, w[`layer${li}.attn_wo`]); x = x.map((v, i) => v + xRes[i]);
        const xRes2 = [...x]; x = rmsnorm(x);
        x = linear(x, w[`layer${li}.mlp_fc1`]).map(v => Math.max(0, v));
        x = linear(x, w[`layer${li}.mlp_fc2`]); x = x.map((v, i) => v + xRes2[i]);
    }
    return linear(x, w['lm_head']);
}
function sampleGPT(weights: GPTWeights, temperature = 0.7, maxLen = 64): string {
    const { config, weights: w } = weights;
    const keys: number[][][] = Array.from({ length: config.n_layer }, () => []);
    const values: number[][][] = Array.from({ length: config.n_layer }, () => []);
    let tokenId = config.BOS; const chars: string[] = [];
    for (let pos = 0; pos < Math.min(maxLen, config.block_size); pos++) {
        const logits = gptForward(tokenId, pos, keys, values, w, config);
        const probs = softmax(logits.map(l => l / temperature));
        const r = Math.random(); let cumulative = 0; tokenId = config.vocab_size - 1;
        for (let i = 0; i < probs.length; i++) { cumulative += probs[i]; if (r < cumulative) { tokenId = i; break; } }
        if (tokenId === config.BOS) break;
        if (tokenId < config.uchars.length) chars.push(config.uchars[tokenId]);
    }
    return chars.join('');
}

// ── Projection types ───────────────────────────────────────────────────

interface BandEntry {
    sol: number;
    survival_pct: number;
    int_c?: { p10: number; p50: number; p90: number };
    stored_kwh?: { p10: number; p50: number; p90: number };
    food_kg?: { p10: number; p50: number; p90: number };
    morale?: { p10: number; p50: number; p90: number };
}
interface ExtremeEvent {
    sol_offset: number; type: string; severity: number;
    duration_sols: number; description: string;
}
interface ProjectionResult {
    start_sol: number; projection_sols: number; num_runs: number;
    survival_rate: number; death_sol_median: number | null;
    bands: BandEntry[]; extreme_events: ExtremeEvent[];
    narratives: string[];
    profile: Record<string, { mean: number; median: number; min: number; max: number; trend: number }>;
}

// ── Confidence band ASCII sparkline ────────────────────────────────────

function BandChart({ bands, field, label, unit, color }: {
    bands: BandEntry[]; field: string; label: string; unit: string; color: string;
}) {
    const sampled = bands.filter((_, i) => i % Math.max(1, Math.floor(bands.length / 12)) === 0 || i === bands.length - 1);
    const allVals = sampled.flatMap(b => {
        const f = (b as any)[field];
        return f ? [f.p10, f.p50, f.p90] : [];
    });
    const min = Math.min(...allVals);
    const max = Math.max(...allVals);
    const range = max - min || 1;

    return (
        <div className="space-y-1">
            <div className="flex justify-between text-[10px] text-slate-500">
                <span>{label}</span>
                <span>{unit}</span>
            </div>
            <div className="flex items-end gap-[2px] h-10">
                {sampled.map((b, i) => {
                    const f = (b as any)[field];
                    if (!f) return <div key={i} className="flex-1 bg-slate-800 rounded-sm h-1" />;
                    const bottom = ((f.p10 - min) / range) * 100;
                    const mid = ((f.p50 - min) / range) * 100;
                    const top = ((f.p90 - min) / range) * 100;
                    return (
                        <div key={i} className="flex-1 relative h-full flex flex-col justify-end" title={`Sol ${b.sol}: ${f.p10}/${f.p50}/${f.p90}`}>
                            <div className="w-full rounded-sm opacity-20" style={{ background: color, height: `${top - bottom}%`, marginBottom: `${bottom}%` }} />
                            <div className="absolute w-full rounded-sm" style={{ background: color, height: '2px', bottom: `${mid}%` }} />
                        </div>
                    );
                })}
            </div>
            <div className="flex justify-between text-[9px] text-slate-600">
                <span>Sol {sampled[0]?.sol}</span>
                <span>Sol {sampled[sampled.length - 1]?.sol}</span>
            </div>
        </div>
    );
}

// ── Main widget ────────────────────────────────────────────────────────

type Mode = 'gpt' | 'project';

export default function ColonyGPTWidget() {
    const [weights, setWeights] = useState<GPTWeights | null>(null);
    const [samples, setSamples] = useState<string[]>([]);
    const [projection, setProjection] = useState<ProjectionResult | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [projecting, setProjecting] = useState(false);
    const [projError, setProjError] = useState<string | null>(null);
    const [mode, setMode] = useState<Mode>('gpt');

    useEffect(() => {
        const controller = new AbortController();
        fetch(import.meta.env.BASE_URL + 'state/marsbarn-gpt.json', { signal: controller.signal })
            .then(r => r.ok ? r : fetch('https://raw.githubusercontent.com/kody-w/mars-barn/main/state/marsbarn-gpt.json', { signal: controller.signal }))
            .then(r => { if (!r.ok) throw new Error('No weights'); return r.json(); })
            .then((data: GPTWeights) => { setWeights(data); setLoading(false); })
            .catch((err) => { if (err.name !== 'AbortError') setLoading(false); });
        return () => controller.abort();
    }, []);

    const generate = useCallback(() => {
        if (!weights) return;
        setGenerating(true);
        setTimeout(() => {
            setSamples(Array.from({ length: 5 }, () => sampleGPT(weights, 0.7)));
            setGenerating(false);
        }, 10);
    }, [weights]);

    const runProjection = useCallback(async () => {
        setProjecting(true);
        setProjError(null);
        try {
            const res = await fetch('/api/project', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sols: 50, runs: 20 }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data: ProjectionResult = await res.json();
            setProjection(data);
        } catch (err: unknown) {
            setProjError(err instanceof Error ? err.message : 'Projection failed');
        }
        setProjecting(false);
    }, []);

    if (loading) return <div className="h-full flex items-center justify-center text-slate-500">Loading colony model...</div>;

    return (
        <div className="flex flex-col h-full gap-2">
            {/* Mode tabs */}
            <div className="flex gap-1">
                <button onClick={() => setMode('gpt')}
                    className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-mono transition-colors ${mode === 'gpt' ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400' : 'bg-white/5 border border-white/5 text-slate-500 hover:text-slate-300'}`}>
                    <Brain size={12} /> GPT
                </button>
                <button onClick={() => setMode('project')}
                    className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-mono transition-colors ${mode === 'project' ? 'bg-amber-500/20 border border-amber-500/30 text-amber-400' : 'bg-white/5 border border-white/5 text-slate-500 hover:text-slate-300'}`}>
                    <FastForward size={12} /> Project
                </button>
            </div>

            {/* GPT mode */}
            {mode === 'gpt' && (
                <>
                    <button onClick={generate} disabled={generating || !weights}
                        className="flex items-center gap-2 px-3 py-2 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/30 transition-colors text-sm font-mono disabled:opacity-50">
                        <Brain size={14} />{generating ? 'Generating...' : 'Generate Colony Logs'}
                    </button>
                    <div className="flex-1 overflow-y-auto pr-2 space-y-2">
                        {samples.length === 0 && weights && (
                            <p className="text-xs text-slate-500 italic">Sample from the colony's microGPT — a {weights.config.vocab_size}-token model trained on colony history.</p>
                        )}
                        {!weights && <p className="text-xs text-slate-500 italic">No microGPT weights found.</p>}
                        {samples.map((s, i) => (
                            <div key={i} className="p-2 rounded bg-white/5 border border-white/5 text-xs font-mono text-emerald-300/80">
                                {s || <span className="text-slate-600">&lt;empty&gt;</span>}
                            </div>
                        ))}
                    </div>
                </>
            )}

            {/* Projection mode */}
            {mode === 'project' && (
                <>
                    <button onClick={runProjection} disabled={projecting}
                        className="flex items-center gap-2 px-3 py-2 rounded bg-amber-500/20 border border-amber-500/30 text-amber-400 hover:bg-amber-500/30 transition-colors text-sm font-mono disabled:opacity-50">
                        <BarChart3 size={14} />{projecting ? 'Datasloshing...' : 'Project Forward 50 Sols'}
                    </button>

                    <div className="flex-1 overflow-y-auto pr-2 space-y-3">
                        {!projection && !projecting && !projError && (
                            <p className="text-xs text-slate-500 italic">
                                Monte Carlo projection: 20 parallel universes simulated forward using real physics,
                                statistical trend analysis, and extreme-event modeling (Poisson-sampled thousand-year events).
                            </p>
                        )}

                        {projError && (
                            <div className="text-xs text-rose-400 font-mono p-3 rounded bg-rose-500/10 border border-rose-500/20">
                                ⚠ Projection failed: {projError}
                            </div>
                        )}

                        {projecting && (
                            <div className="text-xs text-amber-400 animate-pulse font-mono p-3 rounded bg-amber-500/10 border border-amber-500/20">
                                Running 20 Monte Carlo trajectories through {50} sols of Mars physics...
                            </div>
                        )}

                        {projection && (
                            <>
                                {/* Summary header */}
                                <div className="grid grid-cols-3 gap-2">
                                    <div className="p-2 rounded bg-white/5 border border-white/5 text-center">
                                        <div className="text-lg font-bold text-emerald-400">{projection.survival_rate}%</div>
                                        <div className="text-[9px] text-slate-500">Survival</div>
                                    </div>
                                    <div className="p-2 rounded bg-white/5 border border-white/5 text-center">
                                        <div className="text-lg font-bold text-amber-400">{projection.num_runs}</div>
                                        <div className="text-[9px] text-slate-500">Runs</div>
                                    </div>
                                    <div className="p-2 rounded bg-white/5 border border-white/5 text-center">
                                        <div className="text-lg font-bold text-sky-400">{projection.projection_sols}</div>
                                        <div className="text-[9px] text-slate-500">Sols</div>
                                    </div>
                                </div>

                                {/* Confidence band charts */}
                                <div className="space-y-3 p-2 rounded bg-white/[0.02] border border-white/5">
                                    <div className="text-[10px] text-slate-400 font-mono">p10 / p50 / p90 confidence bands</div>
                                    <BandChart bands={projection.bands} field="food_kg" label="Food" unit="kg" color="#f59e0b" />
                                    <BandChart bands={projection.bands} field="stored_kwh" label="Energy" unit="kWh" color="#22d3ee" />
                                    <BandChart bands={projection.bands} field="morale" label="Morale" unit="" color="#a78bfa" />
                                    <BandChart bands={projection.bands} field="int_c" label="Temp" unit="°C" color="#fb923c" />
                                </div>

                                {/* Extreme events */}
                                {projection.extreme_events.length > 0 && (
                                    <div className="space-y-1">
                                        <div className="text-[10px] text-red-400 font-mono">⚠ Extreme Events Sampled</div>
                                        {projection.extreme_events.map((ext, i) => (
                                            <div key={i} className="p-2 rounded bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-300/80">
                                                Sol +{ext.sol_offset}: {ext.type} ({(ext.severity * 100).toFixed(0)}%) — {ext.description}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Narratives from median run */}
                                <div className="space-y-1">
                                    <div className="text-[10px] text-slate-400 font-mono">Median trajectory narrative</div>
                                    {projection.narratives.slice(0, 15).map((n, i) => (
                                        <div key={i} className="px-2 py-1 rounded bg-white/[0.03] text-[10px] font-mono text-slate-400">
                                            {n}
                                        </div>
                                    ))}
                                    {projection.narratives.length > 15 && (
                                        <div className="text-[9px] text-slate-600 italic">
                                            ...{projection.narratives.length - 15} more sols
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                </>
            )}

            {/* Footer */}
            <div className="text-[10px] text-slate-600 font-mono">
                {weights ? `${weights.config.n_layer}L/${weights.config.n_head}H/${weights.config.n_embd}D — ${weights.config.vocab_size}tok` : 'no model'}
                {projection ? ` │ ${projection.survival_rate}% survival @ Sol ${projection.start_sol + projection.projection_sols}` : ''}
            </div>
        </div>
    );
}
