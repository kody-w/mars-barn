import { useSimulationData } from '../lib/useSimulationData';
import { motion } from 'framer-motion';

interface Props {
  planetId: string;
  title: string;
  emoji: string;
}

const STATUS_COLORS: Record<string, string> = {
  nominal: 'border-emerald-500/20 bg-emerald-950/20',
  warning: 'border-amber-500/20 bg-amber-950/20',
  critical: 'border-rose-500/20 bg-rose-950/20',
};

const STATUS_DOT: Record<string, string> = {
  nominal: 'bg-emerald-500',
  warning: 'bg-amber-500',
  critical: 'bg-rose-500',
};

const STATUS_TEXT: Record<string, string> = {
  nominal: 'text-emerald-400',
  warning: 'text-amber-400',
  critical: 'text-rose-400',
};

function MetricRow({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">{label}</span>
      <span className="text-sm font-mono text-zinc-300">
        {value}{unit && <span className="text-zinc-600 ml-0.5">{unit}</span>}
      </span>
    </div>
  );
}

export default function PlanetSimWidget({ planetId, title, emoji }: Props) {
  const t = useSimulationData(planetId, 2000);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      className={`p-5 rounded-2xl border backdrop-blur-xl transition-all duration-500 flex flex-col ${STATUS_COLORS[t.status]}`}
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
        <span className={`text-xs font-semibold uppercase tracking-widest ${STATUS_TEXT[t.status]}`}>
          {t.status}
        </span>
        {t.crewCount > 0 && (
          <span className="ml-auto text-xs font-mono text-zinc-500">{t.crewCount} crew</span>
        )}
      </div>

      {/* Metrics */}
      <div className="flex-1 space-y-0.5 mb-3">
        <MetricRow label="Surface Temp" value={t.surfaceTemp} unit="°C" />
        <MetricRow label="Pressure" value={t.atmosphericPressure} unit="kPa" />
        <MetricRow label="Wind" value={t.windSpeed} unit="km/h" />
        <MetricRow label="Radiation" value={t.radiation} unit="mSv/h" />
        <MetricRow label="Gravity" value={t.gravity} unit="m/s²" />
        <MetricRow label="Power" value={t.powerOutput} unit="kW" />
        <MetricRow label="Comms Delay" value={t.commsLatency} unit="s" />
        <MetricRow label="Experiments" value={t.activeExperiments} />
      </div>

      {/* Event ticker */}
      <div className="bg-black/30 border-l-2 border-current p-3 text-xs leading-relaxed italic text-zinc-400 font-mono mt-auto">
        <motion.span
          key={t.lastEvent}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
        >
          &gt; {t.lastEvent}
        </motion.span>
      </div>
    </motion.div>
  );
}
