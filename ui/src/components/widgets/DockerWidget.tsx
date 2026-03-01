"use client";

import { useState } from 'react';

import { Play, Square, RefreshCcw } from 'lucide-react';


export default function DockerWidget() {
    const [services, setServices] = useState([
        { name: 'traefik-proxy', status: 'running', mem: '45MB' },
        { name: 'postgres-db', status: 'running', mem: '210MB' },
        { name: 'redis-cache', status: 'running', mem: '18MB' },
        { name: 'grafana', status: 'stopped', mem: '0MB' },
    ]);

    const toggleStatus = (idx: number) => {
        const copy = [...services];
        copy[idx].status = copy[idx].status === 'running' ? 'stopped' : 'running';
        if (copy[idx].status === 'running') copy[idx].mem = Math.floor(Math.random() * 100 + 20) + 'MB';
        else copy[idx].mem = '0MB';
        setServices(copy);
    };

    return (
        <div className="flex flex-col h-full gap-3 overflow-y-auto pr-2">
            {services.map((s, i) => (
                <div key={s.name} className="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                    <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${s.status === 'running' ? 'bg-green-500' : 'bg-red-500'}`} />
                        <div>
                            <p className="text-sm font-medium text-slate-200">{s.name}</p>
                            <p className="text-xs text-slate-500 font-mono">{s.mem}</p>
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={(e) => { e.stopPropagation(); toggleStatus(i); }}
                            className="p-1.5 rounded bg-white/10 hover:bg-white/20 text-slate-300 transition-colors"
                        >
                            {s.status === 'running' ? <Square size={14} /> : <Play size={14} />}
                        </button>
                        <button className="p-1.5 rounded bg-white/10 hover:bg-white/20 text-slate-300 transition-colors">
                            <RefreshCcw size={14} />
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
