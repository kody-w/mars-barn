import useSWR from "swr";
const fetcher = (url: string) => fetch(url).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });

export default function PlatformStatsWidget() {
    const { data, error, isLoading } = useSWR('/api/engine/stats', fetcher, { refreshInterval: 5000 });

    if (isLoading) return <div className="h-full flex items-center justify-center text-slate-500">Loading Stats...</div>;
    if (error || !data || data.error) return <div className="h-full flex items-center justify-center text-red-500">Gateway Offline</div>;

    // Helper to format uptime (seconds) to HH:MM:SS
    const formatUptime = (seconds: number) => {
        if (!data.online || !seconds) return "00:00:00";
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex flex-col h-full w-full justify-between gap-4">
            <div className="flex items-end gap-2">
                <span className="text-4xl font-light text-white font-mono">{formatUptime(data.uptime)}</span>
                <span className="text-slate-400 mb-1">Daemon Uptime</span>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-auto">
                <div className="bg-white/5 border border-white/10 rounded p-3">
                    <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">WS Connections</p>
                    <p className="text-xl font-mono text-green-400">{data.connections || 0}</p>
                </div>
                <div className="bg-white/5 border border-white/10 rounded p-3">
                    <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">Loaded Agents</p>
                    <p className="text-xl font-mono text-blue-400">{data.loadedAgents || 0}</p>
                </div>
            </div>
        </div>
    );
}
