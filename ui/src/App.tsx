import { useEffect, useState } from 'react';
import { Activity, Battery, Box, AlertTriangle, ShieldCheck, Skull, Database, Orbit, Network } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import PlanetSimWidget from './components/PlanetSimWidget';
import DashboardGrid from '@/components/DashboardGrid';

interface ColonyStats {
  solar_efficiency: number;
  battery_reserves_kwh: number;
  supply_reserves_tons: number;
}

interface Colony {
  id: string;
  status: 'ALIVE' | 'DEAD' | 'DIGITAL_TWIN';
  age_sols: number;
  last_event: string;
  stats: ColonyStats;
}

const PLANET_SIMS = [
  { id: 'moon', title: 'Moon — Artemis Base', emoji: '🌕' },
  { id: 'mars', title: 'Mars — Olympus Colony', emoji: '🔴' },
  { id: 'venus', title: 'Venus — Cloud Station', emoji: '♀️' },
  { id: 'mercury', title: 'Mercury — Solar Forge', emoji: '☿️' },
  { id: 'jupiter', title: 'Jupiter — Deep Probe', emoji: '🟠' },
  { id: 'saturn', title: 'Saturn — Ring Lab', emoji: '🪐' },
  { id: 'europa', title: 'Europa — Ice Drill', emoji: '🧊' },
  { id: 'titan', title: 'Titan — Methane Explorer', emoji: '🌑' },
];

type Tab = 'simulations' | 'colonies' | 'dashboard';

export default function App() {
  const [colonies, setColonies] = useState<Colony[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>('dashboard');

  useEffect(() => {
    const fetchColonies = async () => {
      try {
        const res = await fetch('/api/colonies');
        const data = await res.json();
        if (Array.isArray(data)) {
          setColonies(data);
        } else if (data.error) {
          console.error("API Proxy Error:", data.error);
        }
      } catch (err) {
        console.error("Failed to fetch colonies", err);
      } finally {
        setLoading(false);
      }
    };

    fetchColonies();
    const interval = setInterval(fetchColonies, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusStyles = (status: Colony['status']) => {
    switch (status) {
      case 'ALIVE':
        return 'text-emerald-400 border-emerald-500/20 bg-emerald-950/20 shadow-[0_0_15px_rgba(16,185,129,0.05)]';
      case 'DEAD':
        return 'text-rose-400 border-rose-500/20 bg-rose-950/20 grayscale-[50%]';
      case 'DIGITAL_TWIN':
        return 'text-amber-400 border-amber-500/30 bg-amber-950/30 shadow-[0_0_20px_rgba(245,158,11,0.1)]';
      default:
        return 'text-slate-400 border-slate-500/30 bg-slate-500/10';
    }
  };

  const StatusIcon = ({ status }: { status: Colony['status'] }) => {
    switch (status) {
      case 'ALIVE': return <Activity size={18} className="text-emerald-400" />;
      case 'DEAD': return <Skull size={18} className="text-rose-400" />;
      case 'DIGITAL_TWIN': return <ShieldCheck size={18} className="text-amber-400" />;
      default: return <AlertTriangle size={18} className="text-slate-400" />;
    }
  };

  return (
    <div className="min-h-screen p-8 lg:p-12 xl:max-w-7xl mx-auto flex flex-col overflow-y-auto">

      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Database className="text-emerald-500" />
            Marsbarn Telemetry
          </h1>
          <p className="text-zinc-500 mt-2 text-sm tracking-wide">
            Live connection established to autonomous orbital database.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center gap-1 bg-zinc-900/80 rounded-full p-1 border border-white/5 whitespace-nowrap overflow-x-auto max-w-full">
          <button
            onClick={() => setTab('dashboard')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all ${tab === 'dashboard'
              ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
              : 'text-zinc-500 hover:text-zinc-300'
              }`}
          >
            <Network size={14} /> Operations UI
          </button>
          <button
            onClick={() => setTab('simulations')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all ${tab === 'simulations'
              ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
              : 'text-zinc-500 hover:text-zinc-300'
              }`}
          >
            <Orbit size={14} /> Solar System Sims
          </button>
          <button
            onClick={() => setTab('colonies')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all ${tab === 'colonies'
              ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
              : 'text-zinc-500 hover:text-zinc-300'
              }`}
          >
            <Database size={14} /> Colony Data
          </button>
        </div>
      </header>

      {/* Dashboard Grid Tab */}
      {tab === 'dashboard' && (
        <main className="flex-1 w-full bg-background text-foreground overflow-hidden font-sans rounded-[2rem] border border-white/10 relative min-h-[600px] shadow-2xl">
          <DashboardGrid />
        </main>
      )}

      {/* Solar System Simulations Tab */}
      {tab === 'simulations' && (
        <motion.main
          key="simulations"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 auto-rows-min pb-8"
        >
          {PLANET_SIMS.map((planet, i) => (
            <PlanetSimWidget
              key={planet.id}
              planetId={planet.id}
              title={planet.title}
              emoji={planet.emoji}
              index={i}
            />
          ))}
        </motion.main>
      )}

      {/* Colony Telemetry Tab */}
      {tab === 'colonies' && (
        <motion.main
          key="colonies"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex-1 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-min pb-8"
        >
          {loading && (
            <div className="col-span-full flex items-center gap-2 text-sm text-zinc-500 font-mono animate-pulse justify-center h-40">
              <div className="h-2 w-2 rounded-full bg-emerald-500" />
              SYNCING...
            </div>
          )}

          {!loading && colonies.length === 0 && (
            <div className="col-span-full h-40 flex items-center justify-center text-zinc-600 font-mono text-sm border border-zinc-800 border-dashed rounded-xl">
              NO SIMULATION SECTORS FOUND IN DATABASE.
            </div>
          )}

          <AnimatePresence>
            {colonies.map((colony) => {
              const battPct = Math.min(100, Math.max(0, (colony.stats.battery_reserves_kwh / 5000) * 100));

              return (
                <motion.div
                  key={colony.id}
                  initial={{ opacity: 0, scale: 0.95, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  className={`p-6 rounded-[2rem] border backdrop-blur-3xl shadow-2xl transition-all duration-500 flex flex-col ${getStatusStyles(colony.status)}`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <StatusIcon status={colony.status} />
                      <span className="font-bold tracking-wide text-lg text-white/90 drop-shadow-md">{colony.id}</span>
                    </div>
                    <span className="text-xs font-mono px-3 py-1 rounded-full bg-black/40 border border-white/5">
                      Sol {colony.age_sols}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-6">
                    <div className="bg-black/20 rounded-2xl p-4 border border-white/5 shadow-inner">
                      <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1.5">
                        <Box size={10} /> Consumables
                      </div>
                      <div className="text-lg font-mono text-zinc-300">
                        {colony.stats.supply_reserves_tons.toFixed(1)}<span className="text-xs text-zinc-600">t</span>
                      </div>
                    </div>
                    <div className="bg-black/20 rounded-2xl p-4 border border-white/5 shadow-inner">
                      <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1.5">
                        <Activity size={10} /> Solar Multiplier
                      </div>
                      <div className="text-lg font-mono text-zinc-300">
                        {(colony.stats.solar_efficiency * 100).toFixed(0)}<span className="text-xs text-zinc-600">%</span>
                      </div>
                    </div>
                  </div>

                  <div className="mb-4 mt-auto">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="text-xs uppercase font-bold tracking-wider flex items-center gap-1.5 opacity-80">
                        <Battery size={12} /> Net Power Buffer
                      </span>
                      <span className="text-xs font-mono opacity-80 font-bold">{colony.stats.battery_reserves_kwh.toFixed(1)} kWh</span>
                    </div>
                    <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden border border-white/5 p-[1px]">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${battPct}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        className={`h-full ${colony.status === 'DEAD' ? 'bg-rose-500/50' : colony.status === 'ALIVE' ? 'bg-emerald-500 tracking-glow' : 'bg-amber-500'} rounded-full`}
                      />
                    </div>
                  </div>

                  <div className="bg-black/20 rounded-2xl p-4 text-xs leading-relaxed italic text-zinc-400 mt-2 font-mono shadow-inner">
                    &gt; {colony.last_event}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </motion.main>
      )}
    </div>
  );
}
