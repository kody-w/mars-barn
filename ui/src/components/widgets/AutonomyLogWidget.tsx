import useSWR from "swr";
"use client";


import { useEffect, useRef } from 'react';


const fetcher = (url: string) => fetch(url).then(r => r.json());

export default function AutonomyLogWidget() {
    const { data, error, isLoading } = useSWR('/api/rappter?file=autonomy_log.json', fetcher, { refreshInterval: 5000 });
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [data]);

    if (isLoading) return <div className="h-full flex items-center justify-center text-slate-500">Querying Autonomy Engine...</div>;
    if (error || !data || data.error) return <div className="h-full flex items-center justify-center text-red-500">Log Unavailable</div>;

    const entries = data.entries || [];

    return (
        <div className="h-full w-full bg-black/50 rounded-lg p-3 overflow-y-auto font-mono text-[11px] leading-relaxed border border-white/5 break-words">
            {entries.slice(-50).map((log: any, i: number) => (
                <div key={i} className={`mb-1.5 ${log.level === 'ERROR' ? 'text-red-400' :
                        log.level === 'WARN' ? 'text-yellow-400' :
                            log.level === 'DEBUG' ? 'text-slate-500' : 'text-green-400'
                    }`}>
                    <span className="opacity-50 mr-2">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                    <span className="font-bold mr-2">[{log.agent_name || 'SYSTEM'}]</span>
                    {log.action}: {log.message || log.details}
                </div>
            ))}
            <div ref={endRef} />
        </div>
    );
}
