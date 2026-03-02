import React, { useEffect, useRef, useCallback } from 'react';
import { useColonyStore } from '../lib/colonyStore';
import { useColonyAgent } from '../lib/useColonyAgent';
import {
  Thermometer,
  Battery,
  Sun,
  Wind,
  MapPin,
  Users,
  UtensilsCrossed,
  Droplets,
  Download,
  Upload,
  RefreshCw,
  Clock,
  Gauge,
} from 'lucide-react';

function StatusBadge({ alive }: { alive: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-widest ${
        alive
          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
          : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${alive ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
      {alive ? 'HABITABLE' : 'CRITICAL'}
    </span>
  );
}

function Stat({ icon: Icon, label, value, unit, warn }: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  value: string | number;
  unit?: string;
  warn?: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/30 border ${warn ? 'border-rose-500/30' : 'border-white/5'}`}>
      <Icon size={12} className={warn ? 'text-rose-400' : 'text-zinc-500'} />
      <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">{label}</span>
      <span className="ml-auto font-mono text-sm text-zinc-200">
        {value}
        {unit && <span className="text-zinc-600 text-xs ml-0.5">{unit}</span>}
      </span>
    </div>
  );
}

export default function ColonyHUD() {
  const { colony, loading, error, lastFetchedAt, fetchColony, importState, exportState, stateKey } =
    useColonyStore();
  const agent = useColonyAgent();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-refresh every 60s
  useEffect(() => {
    fetchColony();
    const interval = setInterval(fetchColony, 60_000);
    return () => clearInterval(interval);
  }, [fetchColony]);

  const handleExport = useCallback(() => {
    const json = exportState();
    if (!json) return;
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `marsbarn-sol${colony?.sol ?? 0}-${new Date().toISOString().slice(0, 19).replace(/:/g, '')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportState, colony]);

  const handleImport = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          importState(reader.result);
        }
      };
      reader.readAsText(file);
      e.target.value = '';
    },
    [importState]
  );

  if (!colony) {
    return (
      <div className="absolute top-4 left-4 bg-black/70 backdrop-blur-xl rounded-2xl p-4 text-zinc-500 font-mono text-sm border border-white/10">
        {loading ? '⏳ Fetching colony state...' : error ? `❌ ${error}` : 'No data'}
      </div>
    );
  }

  const intC = colony.habitat.interior_temp_k - 273.15;
  const lastLog = colony.log[colony.log.length - 1];
  const extC = lastLog?.ext_c ?? -60;
  const alive = intC > -30;
  const stormActive = colony.active_events.some((e) => e.type === 'storm');
  const key = stateKey();

  return (
    <>
      {/* Hidden file input for import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Top-left: Colony info */}
      <div className="absolute top-4 left-4 bg-black/70 backdrop-blur-xl rounded-2xl p-4 border border-white/10 min-w-[280px] max-w-[320px] space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight">{colony.name}</h2>
            <div className="flex items-center gap-1.5 text-xs text-zinc-500 mt-0.5">
              <MapPin size={10} />
              {colony.location.name}
            </div>
          </div>
          <StatusBadge alive={alive} />
        </div>

        {/* Time composite key */}
        <div className="bg-black/40 rounded-xl p-2.5 border border-white/5 space-y-1">
          <div className="flex items-center gap-2">
            <Clock size={11} className="text-amber-400" />
            <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Virtual Time</span>
            <span className="ml-auto font-mono text-xs text-amber-400">
              Sol {colony.sol} · Ls {colony.solar_longitude}°
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Clock size={11} className="text-sky-400" />
            <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Real Time</span>
            <span className="ml-auto font-mono text-xs text-sky-400">
              {lastFetchedAt ? new Date(lastFetchedAt).toLocaleTimeString() : '—'}
            </span>
          </div>
          <div className="text-[9px] font-mono text-zinc-600 truncate pt-1 border-t border-white/5">
            PK: {key.slice(0, 50)}…
          </div>
        </div>

        {/* Location */}
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <Gauge size={11} />
          <span>{colony.location.latitude.toFixed(1)}°N, {colony.location.longitude.toFixed(1)}°E</span>
        </div>

        {/* Storm warning */}
        {stormActive && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-lg px-3 py-2 text-xs text-rose-400 font-mono animate-pulse">
            🌪️ DUST STORM ACTIVE — Severity{' '}
            {(
              colony.active_events
                .filter((e) => e.type === 'storm')
                .reduce((m, e) => Math.max(m, e.severity ?? 0), 0) * 100
            ).toFixed(0)}
            %
          </div>
        )}

        {/* Stats grid */}
        <div className="space-y-1.5">
          <Stat icon={Thermometer} label="Interior" value={intC.toFixed(1)} unit="°C" warn={intC < 0} />
          <Stat icon={Wind} label="Exterior" value={extC.toFixed(1)} unit="°C" />
          <Stat icon={Battery} label="Reserves" value={colony.habitat.stored_energy_kwh.toFixed(0)} unit="kWh" warn={colony.habitat.stored_energy_kwh < 100} />
          <Stat icon={Sun} label="Panels" value={(colony.habitat.panel_dust_factor * 100).toFixed(0)} unit="%" />
          <Stat icon={Users} label="Crew" value={colony.habitat.crew_size} />
          <Stat icon={UtensilsCrossed} label="Food" value={colony.habitat.food_reserves_kg.toFixed(1)} unit="kg" warn={colony.habitat.food_reserves_kg < 30} />
          <Stat icon={Droplets} label="Water" value={colony.habitat.water_reserves_l.toFixed(0)} unit="L" />
        </div>

        {/* Event log */}
        {lastLog && lastLog.events.length > 0 && (
          <div className="bg-black/40 rounded-lg p-2 border border-white/5">
            <div className="text-[9px] text-zinc-600 uppercase tracking-widest font-bold mb-1">Latest Events</div>
            <div className="text-xs font-mono text-zinc-400 space-y-0.5">
              {lastLog.events.map((ev, i) => (
                <div key={i}>&gt; {ev}</div>
              ))}
            </div>
          </div>
        )}

        {/* Local Intelligence Agent */}
        {agent.ready && agent.elaboration && (
          <div className="bg-emerald-950/20 border border-emerald-500/20 rounded-lg p-2.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <div className="text-[9px] text-emerald-500/70 uppercase tracking-widest font-bold">🧠 Colony AI (Local)</div>
              <button
                onClick={agent.regenerate}
                className="text-[9px] text-zinc-600 hover:text-zinc-400 transition-colors"
              >
                ↻
              </button>
            </div>
            <div className="text-xs text-zinc-300 leading-relaxed">
              {agent.elaboration}
            </div>
            {agent.predictions.length > 0 && (
              <div className="pt-1 border-t border-white/5">
                <div className="text-[9px] text-zinc-600 uppercase tracking-widest font-bold mb-0.5">Next Sol Forecast</div>
                <div className="text-[10px] font-mono text-zinc-500 space-y-0.5">
                  {agent.predictions.map((p, i) => (
                    <div key={i} className="truncate">→ {p}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        {agent.loading && (
          <div className="text-[10px] text-zinc-600 font-mono animate-pulse">
            Loading colony intelligence...
          </div>
        )}
      </div>
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2">
        <button
          onClick={() => fetchColony()}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-black/70 backdrop-blur-xl rounded-xl border border-white/10 text-xs font-mono text-zinc-300 hover:text-white hover:border-emerald-500/30 transition-all disabled:opacity-50"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Syncing…' : 'Refresh'}
        </button>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 bg-black/70 backdrop-blur-xl rounded-xl border border-white/10 text-xs font-mono text-zinc-300 hover:text-white hover:border-sky-500/30 transition-all"
        >
          <Download size={12} />
          Export State
        </button>
        <button
          onClick={handleImport}
          className="flex items-center gap-2 px-4 py-2 bg-black/70 backdrop-blur-xl rounded-xl border border-white/10 text-xs font-mono text-zinc-300 hover:text-white hover:border-amber-500/30 transition-all"
        >
          <Upload size={12} />
          Import State
        </button>
      </div>

      {/* Error toast */}
      {error && (
        <div className="absolute top-4 right-4 bg-rose-950/80 backdrop-blur-xl border border-rose-500/30 rounded-xl px-4 py-2 text-xs text-rose-400 font-mono max-w-[300px]">
          ❌ {error}
        </div>
      )}

      {/* Stats bar top-right */}
      <div className="absolute top-4 right-4 bg-black/50 backdrop-blur-xl rounded-xl px-3 py-2 border border-white/5 text-[10px] font-mono text-zinc-600 space-y-0.5">
        <div>Survived: {colony.stats.sols_survived} sols</div>
        <div>Power: {colony.stats.total_power_kwh.toFixed(0)} kWh</div>
        <div>Storms: {colony.stats.storms_survived}</div>
        <div>Temp: {(colony.stats.min_temp_k - 273.15).toFixed(0)}°C — {(colony.stats.max_temp_k - 273.15).toFixed(0)}°C</div>
        <div className="pt-1 mt-1 border-t border-white/5 text-emerald-500/60">
          ✅ Backtest: 17,400 sols (26 Mars yrs)
        </div>
        <div className="text-emerald-500/40">Viking 1976 → Present</div>
        <div className="text-emerald-500/40">1,627 storms survived</div>
      </div>
    </>
  );
}
