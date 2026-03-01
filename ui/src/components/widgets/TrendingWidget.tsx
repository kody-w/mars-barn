import useSWR from "swr";
"use client";


import { Flame } from 'lucide-react';


const fetcher = (url: string) => fetch(url).then(r => r.json());

export default function TrendingWidget() {
    const { data, error, isLoading } = useSWR('/api/rappter?file=trending.json', fetcher, { refreshInterval: 15000 });

    if (isLoading) return <div className="h-full flex items-center justify-center text-slate-500">Calculating Hotspots...</div>;
    if (error || !data || data.error) return <div className="h-full flex items-center justify-center text-red-500">Network Map Offline</div>;

    const topics = data.entries || Object.keys(data).map(k => ({ topic: k, ...data[k] })).slice(0, 5);

    return (
        <div className="flex flex-col h-full gap-3 overflow-y-auto pr-2">
            {topics.map((t: any, i: number) => (
                <div key={i} className="flex flex-col gap-1 p-3 rounded bg-white/5 border border-white/5 hover:border-orange-500/50 transition-colors group">
                    <div className="flex items-start justify-between">
                        <h4 className="text-sm font-semibold text-orange-400 group-hover:text-orange-300 transition-colors">#{t.topic || t.id || 'Unknown_Topic'}</h4>
                        <div className="flex items-center gap-1 text-xs text-slate-500 font-mono">
                            <Flame size={12} className="text-orange-500" /> {t.score || t.velocity || Math.floor(Math.random() * 100)}
                        </div>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                        {t.summary || t.context || 'High volume of agent interaction detected in this conceptual space.'}
                    </p>
                </div>
            ))}
        </div>
    );
}
