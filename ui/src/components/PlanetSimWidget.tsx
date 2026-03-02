import { useSimulationData } from '../lib/useSimulationData';
import { motion } from 'framer-motion';

// Multi-planet backtest results (from src/planetary_climate.py, 669 sols)
const BACKTEST_RESULTS: Record<string, { survived: boolean; sols: number; tempRange: string; penalty: string }> = {
  moon:    { survived: true,  sols: 669, tempRange: '+15 to +22°C', penalty: '2.0×' },
  mars:    { survived: true,  sols: 669, tempRange: '+17 to +20°C', penalty: '1.0×' },
  venus:   { survived: false, sols: 1,   tempRange: '-110°C',       penalty: '5.0×' },
  mercury: { survived: false, sols: 12,  tempRange: '-76 to +11°C', penalty: '3.0×' },
  jupiter: { survived: false, sols: 4,   tempRange: '-19 to -12°C', penalty: '6.0×' },
  saturn:  { survived: false, sols: 4,   tempRange: '-27 to -13°C', penalty: '5.0×' },
  europa:  { survived: false, sols: 4,   tempRange: '-26 to -12°C', penalty: '4.0×' },
  titan:   { survived: false, sols: 4,   tempRange: '-40 to -17°C', penalty: '4.5×' },
};

interface Props {
  planetId: string;
  title: string;
  emoji: string;
  index?: number;
  onEnterColony?: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  nominal: 'border-emerald-500/20 bg-emerald-950/20 shadow-[0_0_15px_rgba(16,185,129,0.05)]',
  warning: 'border-amber-500/20 bg-amber-950/20 shadow-[0_0_15px_rgba(245,158,11,0.08)]',
  critical: 'border-rose-500/20 bg-rose-950/20 shadow-[0_0_20px_rgba(239,68,68,0.1)]',
};

const STATUS_DOT: Record<string, string> = {
  nominal: 'bg-emerald-500',
  warning: 'bg-amber-500',
  critical: 'bg-rose-500',
};

function MetricRow({ label, value, unit, display }: { label: string; value: string | number; unit?: string; display?: string }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">{label}</span>
      <span className="text-sm font-mono text-zinc-300">
        {display ?? <>{value}{unit && <span className="text-zinc-600 ml-0.5">{unit}</span>}</>}
      </span>
    </div>
  );
}

export default function PlanetSimWidget({ planetId, title, emoji, index = 0, onEnterColony }: Props) {
  // Stagger tick intervals so widgets don't all flash at once
  const t = useSimulationData(planetId, 1800 + index * 200);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ delay: index * 0.07, duration: 0.4 }}
      className={`p-6 rounded-[2rem] border backdrop-blur-3xl shadow-2xl transition-all duration-500 flex flex-col ${STATUS_COLORS[t.status]}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">{emoji}</span>
          <span className="font-bold tracking-wide text-white/90">{title}</span>
        </div>
        <span className="text-xs font-mono px-3 py-1 rounded-full bg-black/40 border border-white/5">
          Sol {t.missionDay}
        </span>
      </div>

      {/* Status */}
      <div className="flex items-center gap-2 mb-3">
        <motion.div
          className={`w-2 h-2 rounded-full ${STATUS_DOT[t.status]}`}
          animate={{ opacity: t.status === 'critical' ? [1, 0.3, 1] : 1 }}
          transition={{ repeat: t.status === 'critical' ? Infinity : 0, duration: 0.8 }}
        />
        <span className={`text-xs font-semibold uppercase tracking-widest ${STATUS_DOT[t.status].replace('bg-', 'text-').replace('-500', '-400')}`}>
          {t.status}
        </span>
        {t.crewCount > 0 && (
          <span className="ml-auto text-xs font-mono text-zinc-500">{t.crewCount} crew</span>
        )}
      </div>

      {/* Metrics */}
      <div className="flex-1 space-y-0.5 mb-3">
        <MetricRow label="Surface Temp" value={t.surfaceTemp} unit="°C" />
        <MetricRow label="Pressure" value={t.atmosphericPressure} unit="kPa"
          display={t.atmosphericPressure < 0.001 ? '< 0.001 kPa' : undefined} />
        <MetricRow label="Wind" value={t.windSpeed} unit="km/h"
          display={t.windSpeed === 0 ? '—' : undefined} />
        <MetricRow label="Radiation" value={t.radiation} unit="mSv/h" />
        <MetricRow label="Gravity" value={t.gravity} unit="m/s²" />
        <MetricRow label="Power" value={t.powerOutput} unit="kW" />
        <MetricRow label="Comms Delay" value={t.commsLatency} unit="s"
          display={t.commsLatency < 2 ? `${t.commsLatency}s` : `${(t.commsLatency / 60).toFixed(1)} min`} />
        <MetricRow label="Experiments" value={t.activeExperiments} />
      </div>

      {/* Event ticker */}
      <div className="bg-black/20 rounded-2xl p-4 text-xs leading-relaxed italic text-zinc-400 font-mono mt-auto shadow-inner">
        <motion.span
          key={t.lastEvent}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
        >
          &gt; {t.lastEvent}
        </motion.span>
      </div>

      {/* Backtest survival badge */}
      {BACKTEST_RESULTS[planetId] && (
        <div className={`mt-2 px-3 py-1.5 rounded-xl text-[10px] font-mono border ${
          BACKTEST_RESULTS[planetId].survived
            ? 'bg-emerald-950/30 border-emerald-500/20 text-emerald-400'
            : 'bg-rose-950/30 border-rose-500/20 text-rose-400'
        }`}>
          <div className="flex items-center justify-between">
            <span>{BACKTEST_RESULTS[planetId].survived ? '✅' : '❌'} Backtest: {BACKTEST_RESULTS[planetId].sols} sols</span>
            <span className="text-zinc-600">{BACKTEST_RESULTS[planetId].penalty}</span>
          </div>
          <div className="text-zinc-500 mt-0.5">{BACKTEST_RESULTS[planetId].tempRange}</div>
        </div>
      )}

      {/* Enter Colony button for Mars */}
      {onEnterColony && (
        <button
          onClick={onEnterColony}
          className="mt-3 w-full py-2 rounded-xl bg-emerald-600/20 border border-emerald-500/30 text-emerald-400 text-xs font-bold uppercase tracking-widest hover:bg-emerald-600/30 transition-all"
        >
          🔭 Enter Colony 3D
        </button>
      )}
    </motion.div>
  );
}
