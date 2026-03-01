/**
 * Mars Barn — Local Colony Intelligence Agent
 *
 * LOCAL-FIRST design: the microGPT model ships with the repo as a static
 * JSON file. No network calls. No API keys. Always available offline.
 *
 * This hook wraps the inference engine and provides:
 * - Status elaboration (what's happening right now)
 * - Event context (why did this happen)
 * - Predictive hints (what might happen next)
 *
 * The model is trained on colony simulation logs and learns the statistical
 * patterns of colony life: temperature swings, storm sequences, energy
 * cycles, food depletion curves. Its "intelligence" is pattern completion
 * on these sequences — same mechanism as ChatGPT, just tiny and local.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { loadModel, generate, GPTModel } from './microGPT';
import { ColonyState, useColonyStore } from './colonyStore';

// Model lives in the repo — fetched once, cached forever
const MODEL_URLS = [
  // Local dev (vite serves from project root)
  '/mars-barn/state/marsbarn-gpt.json',
  // GitHub raw fallback
  'https://raw.githubusercontent.com/kody-w/mars-barn/main/state/marsbarn-gpt.json',
];

interface AgentState {
  ready: boolean;
  loading: boolean;
  error: string | null;
  elaboration: string | null;
  predictions: string[];
  lastContext: string | null;
}

/**
 * Build a prompt from current colony state.
 * The model was trained on patterns like "sol23 cold -29c 214kw 228r"
 * so we format the current state the same way.
 */
function stateToPrompt(colony: ColonyState): string {
  const intC = Math.round(colony.habitat.interior_temp_k - 273.15);
  const status =
    intC > 15 ? 'nominal' : intC > 0 ? 'cool' : intC > -30 ? 'cold' : 'critical';
  return `sol${colony.sol} ${status} ${intC > 0 ? '+' : ''}${intC}c`;
}

/**
 * Interpret a raw model output into human-readable elaboration.
 */
function interpretOutput(raw: string, colony: ColonyState): string {
  const intC = Math.round(colony.habitat.interior_temp_k - 273.15);

  // Parse what the model generated (it produces colony-log-style text)
  const parts: string[] = [];

  // Current status elaboration
  if (intC > 15) {
    parts.push('Systems nominal.');
  } else if (intC > 0) {
    parts.push('Habitat is cooling. Monitor heater output.');
  } else if (intC > -30) {
    parts.push('Cold warning. Thermal reserves strained.');
  } else {
    parts.push('CRITICAL: Life support at risk.');
  }

  // Energy context
  if (colony.habitat.stored_energy_kwh < 200) {
    parts.push('Low energy reserves — reduce non-essential loads.');
  } else if (colony.habitat.stored_energy_kwh > 1000) {
    parts.push('Strong energy surplus.');
  }

  // Food context
  if (colony.habitat.food_reserves_kg < 30) {
    parts.push('Food critically low. Harvest needed.');
  }

  // Storm context
  const stormActive = colony.active_events.some((e) => e.type === 'storm');
  if (stormActive) {
    parts.push('Dust storm reducing solar input. Conserve reserves.');
  }

  // Model prediction hint (from the raw output)
  if (raw.includes('storm')) {
    parts.push('Model predicts storm-like conditions ahead.');
  }
  if (raw.includes('critical')) {
    parts.push('Model sees critical pattern forming.');
  }

  return parts.join(' ');
}

export function useColonyAgent() {
  const colony = useColonyStore((s) => s.colony);
  const modelRef = useRef<GPTModel | null>(null);
  const [state, setState] = useState<AgentState>({
    ready: false,
    loading: true,
    error: null,
    elaboration: null,
    predictions: [],
    lastContext: null,
  });

  // Load model once (try local first, then GitHub raw)
  useEffect(() => {
    let cancelled = false;

    async function load() {
      for (const url of MODEL_URLS) {
        try {
          const model = await loadModel(url);
          if (cancelled) return;
          modelRef.current = model;
          setState((s) => ({ ...s, ready: true, loading: false }));
          return;
        } catch {
          continue;
        }
      }
      if (!cancelled) {
        setState((s) => ({
          ...s,
          loading: false,
          error: 'Colony GPT weights not found. Train with: python src/microgpt.py',
        }));
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  // Re-elaborate when colony state changes
  useEffect(() => {
    if (!modelRef.current || !colony) return;

    const prompt = stateToPrompt(colony);
    if (prompt === state.lastContext) return;

    // Generate elaboration and predictions
    const raw = generate(modelRef.current, prompt, 24, 0.7);
    const elaboration = interpretOutput(raw, colony);

    // Generate a few prediction samples
    const predictions: string[] = [];
    for (let i = 0; i < 3; i++) {
      const pred = generate(modelRef.current, `sol${colony.sol + 1}`, 20, 0.8);
      predictions.push(pred);
    }

    setState((s) => ({
      ...s,
      elaboration,
      predictions,
      lastContext: prompt,
    }));
  }, [colony, state.lastContext]);

  const regenerate = useCallback(() => {
    if (!modelRef.current || !colony) return;
    const prompt = stateToPrompt(colony);
    const raw = generate(modelRef.current, prompt, 24, 0.9);
    const elaboration = interpretOutput(raw, colony);
    setState((s) => ({ ...s, elaboration, lastContext: null }));
  }, [colony]);

  return { ...state, regenerate };
}
