import { useEffect, useState, useRef } from 'react';

/** Demo widget — displays simulated log output. Not connected to a live API. */
export default function LogsWidget() {
    const [logs, setLogs] = useState<string[]>([
        '[INFO] System started and initialized.',
        '[WARN] Port 8080 already in use, binding to 8081.',
    ]);
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const msgs = [
            '[INFO] Refreshing token cache...',
            '[DEBUG] Handling incoming request GET /api/v1/health',
            '[ERROR] Failed to connect to Redis instance at 10.0.0.5',
            '[INFO] Container trfk-proxy restarted successfully.',
            '[WARN] High memory utilization detected in prometheus.',
            '[INFO] Syncing filesystem block 0x00FFa...',
        ];

        const interval = setInterval(() => {
            setLogs(prev => {
                const next = [...prev, msgs[Math.floor(Math.random() * msgs.length)]];
                if (next.length > 50) return next.slice(next.length - 50); // Keep last 50
                return next;
            });
        }, 1500);

        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    return (
        <div className="h-full w-full bg-black/50 rounded-lg p-3 overflow-y-auto font-mono text-xs border border-white/5">
            {logs.map((log, i) => (
                <div key={i} className={`mb-1 ${log.includes('[ERROR]') ? 'text-red-400' :
                        log.includes('[WARN]') ? 'text-yellow-400' :
                            log.includes('[DEBUG]') ? 'text-slate-500' : 'text-green-400'
                    }`}>
                    {log}
                </div>
            ))}
            <div ref={endRef} />
        </div>
    );
}
