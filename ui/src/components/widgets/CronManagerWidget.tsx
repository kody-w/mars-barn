import useSWR from "swr";
import { Clock, Play, Pause, Trash2, CalendarClock, Power, PowerOff, Activity } from 'lucide-react';
import { useState } from 'react';
const fetcher = (url: string) => fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ method: 'cron.list' })
}).then(r => r.json());

export default function CronManagerWidget() {
    const { data, error, isLoading, mutate } = useSWR('/api/engine/gateway', fetcher, { refreshInterval: 5000 });
    const [loadingId, setLoadingId] = useState<string | null>(null);
    const [isDaemonLoading, setIsDaemonLoading] = useState(false);

    const isConnected = data?.success === true;
    const jobs = data?.data || [];

    const handleStartDaemon = async () => {
        setIsDaemonLoading(true);
        try {
            await fetch('/api/engine/daemon', { method: 'POST' });
            setTimeout(() => mutate(), 3000); // Wait for boot before re-fetching
        } finally {
            setIsDaemonLoading(false);
        }
    };

    const handleStopDaemon = async () => {
        if (!confirm("Are you sure you want to kill the OpenRappter daemon?")) return;
        setIsDaemonLoading(true);
        try {
            await fetch('/api/engine/daemon', { method: 'DELETE' });
            setTimeout(() => mutate(), 1000);
        } finally {
            setIsDaemonLoading(false);
        }
    };

    const handleAction = async (jobId: string, action: string, actionParams: Record<string, unknown> = {}) => {
        setLoadingId(`${jobId}-${action}`);
        try {
            const res = await fetch('/api/engine/gateway', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    method: action,
                    params: { jobId, ...actionParams }
                })
            });
            if (!res.ok) throw new Error(`Action failed (${res.status})`);
            mutate();
        } catch {
            // Engine is offline — action silently ignored
        } finally {
            setLoadingId(null);
        }
    };

    const handleCreateTestCron = async () => {
        setLoadingId('create');
        try {
            await fetch('/api/engine/gateway', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    method: 'cron.add',
                    params: {
                        name: `System Cleanup Task`,
                        schedule: "0 0 * * *",
                        action: "Forget memories older than 30 days",
                        enabled: true
                    }
                })
            });
            mutate();
        } finally {
            setLoadingId(null);
        }
    }

    // MacOS Menu App style UI
    return (
        <div className="flex flex-col h-full bg-[#1b1c20]/80 backdrop-blur-xl rounded-xl border border-white/10 shadow-2xl overflow-hidden font-sans">

            {/* macOS Menu Header Style */}
            <div className="flex items-center justify-between px-4 py-3 bg-white/[0.02] border-b border-white/5 relative">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <div className={`p-2 rounded-lg ${isConnected ? 'bg-green-500/20 text-green-400' : 'bg-slate-800 text-slate-500'}`}>
                            <Activity size={16} />
                        </div>
                        {isConnected && <div className="absolute top-0 right-0 w-2 h-2 rounded-full bg-green-500 border border-[#1b1c20]" />}
                    </div>

                    <div className="flex flex-col">
                        <span className="text-sm font-semibold text-slate-200 tracking-tight flex items-center gap-2">
                            OpenRappter Daemon
                            {isConnected && (
                                <button type="button"
                                    onClick={handleStopDaemon}
                                    disabled={isDaemonLoading}
                                    title="Kill Local Daemon"
                                    className="text-slate-500 hover:text-red-400 transition-colors"
                                >
                                    <PowerOff size={11} />
                                </button>
                            )}
                        </span>
                        <span className="text-[10px] text-slate-500 font-medium tracking-wide">
                            {isLoading || isDaemonLoading ? "CONNECTING..." : isConnected ? "GATEWAY CONNECTED" : "OFFLINE"}
                        </span>
                    </div>
                </div>

                <button type="button"
                    onClick={handleCreateTestCron}
                    disabled={!isConnected || loadingId === 'create'}
                    className="text-[11px] bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 font-medium px-3 py-1.5 rounded-md transition-colors border border-blue-500/20 disabled:opacity-50"
                >
                    + New Schedule
                </button>
            </div>

            {/* JobList: macOS List View Style */}
            <div className="flex-1 overflow-y-auto bg-black/20 p-2">
                {error || !isConnected ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-3">
                        <PowerOff size={32} className="opacity-40" />
                        <p className="text-sm">Daemon Unreachable</p>
                        <div className="flex gap-2 mt-2">
                            <button type="button"
                                onClick={handleStartDaemon}
                                disabled={isDaemonLoading}
                                className="text-[11px] bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded font-semibold transition disabled:opacity-50"
                            >
                                {isDaemonLoading ? 'Booting...' : 'Start Local Engine'}
                            </button>
                            <button onClick={() => mutate()} className="text-[11px] bg-slate-800 hover:bg-slate-700 px-3 py-2 rounded transition">
                                Retry
                            </button>
                        </div>
                    </div>
                ) : jobs.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-xs text-slate-500 text-center px-6 gap-2 opacity-80">
                        <CalendarClock size={28} className="text-slate-600 mb-1" />
                        <p>No active scheduled tasks running on the Open Rappter engine.</p>
                    </div>
                ) : (
                    <div className="space-y-1">
                        {jobs.map((job: Record<string, string | boolean>) => (
                            <div key={job.id} className="group flex items-center justify-between p-3 rounded bg-white/5 hover:bg-white/10 border border-transparent hover:border-white/5 transition-all">
                                <div className="flex items-start gap-3">
                                    <div className="mt-1">
                                        <div className={`w-2.5 h-2.5 rounded-full ${job.enabled ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 'bg-slate-600 shadow-inner'}`} />
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-semibold text-slate-200 tracking-tight">{job.name || job.action}</h4>
                                        <p className="text-[11px] text-slate-400 mt-0.5 truncate max-w-[180px]" title={job.action}>{job.action}</p>
                                        <div className="flex items-center gap-2 mt-1.5 text-[10px] font-mono text-slate-500">
                                            <Clock size={10} />
                                            <span>{job.schedule}</span>
                                            {job.lastRun && <span>• Ran {new Date(job.lastRun).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
                                        </div>
                                    </div>
                                </div>

                                {/* macOS style discrete action icons */}
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button type="button"
                                        onClick={() => handleAction(job.id, 'cron.run')}
                                        disabled={loadingId !== null}
                                        className="p-1.5 bg-black/20 hover:bg-blue-500/20 text-slate-400 hover:text-blue-400 rounded-md transition border border-transparent hover:border-blue-500/20"
                                        title="Execute Immediately"
                                    >
                                        <Play size={14} className="fill-current" />
                                    </button>
                                    <button type="button"
                                        onClick={() => handleAction(job.id, 'cron.enable', { enabled: !job.enabled })}
                                        disabled={loadingId !== null}
                                        className="p-1.5 bg-black/20 hover:bg-yellow-500/20 text-slate-400 hover:text-yellow-500 rounded-md transition border border-transparent hover:border-yellow-500/20"
                                        title={job.enabled ? "Pause Schedule" : "Resume Schedule"}
                                    >
                                        {job.enabled ? <Pause size={14} className="fill-current" /> : <Power size={14} />}
                                    </button>
                                    <button type="button"
                                        onClick={() => handleAction(job.id, 'cron.remove')}
                                        disabled={loadingId !== null}
                                        className="p-1.5 bg-black/20 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-md transition border border-transparent hover:border-red-500/20 ml-1"
                                        title="Delete Job"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* macOS StatusBar Footer */}
            {isConnected && (
                <div className="px-4 py-2 bg-white/[0.02] border-t border-white/5 flex justify-between items-center shrink-0">
                    <span className="text-[10px] font-mono text-slate-500">
                        Active Jobs: {jobs.length}
                    </span>
                    <span className="flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-blue-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                    </span>
                </div>
            )}
        </div>
    );
}
