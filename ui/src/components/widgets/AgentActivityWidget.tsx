import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });

export default function AgentActivityWidget() {
    const { data, error, isLoading } = useSWR('/api/rappter?file=agents.json', fetcher, { refreshInterval: 10000 });

    if (isLoading) return <div className="h-full flex items-center justify-center text-slate-500">Incoming Agent Data...</div>;
    if (error || !data || data.error) return <div className="h-full flex items-center justify-center text-red-500">Error reading agents.json</div>;

    // data is an object of agent models { "agent_name": { status: 'awake', ... } }
    const agents = Object.entries(data).map(([name, info]: [string, Record<string, string>]) => ({
        name,
        status: info.status || 'asleep',
        heartbeat: info.last_heartbeat
    })).slice(0, 20);

    return (
        <div className="flex flex-col h-full gap-2 overflow-y-auto pr-2">
            {agents.map((agent) => (
                <div key={agent.name} className="flex items-center justify-between p-2 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                    <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${agent.status === 'awake' || agent.status === 'posting' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] animate-pulse' : 'bg-slate-700'}`} />
                        <div>
                            <p className="text-sm font-medium text-slate-200">{agent.name}</p>
                            <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">{agent.status}</p>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}
