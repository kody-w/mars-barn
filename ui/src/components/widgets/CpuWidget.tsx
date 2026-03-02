import { useEffect, useState } from 'react';
export default function CpuWidget() {
    const [load, setLoad] = useState<number[]>(Array(20).fill(0));

    useEffect(() => {
        const interval = setInterval(() => {
            setLoad(prev => {
                const next = [...prev.slice(1), Math.floor(Math.random() * 60) + 20];
                return next;
            });
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    const currentLoad = load[load.length - 1];

    return (
        <div className="flex flex-col h-full w-full justify-between gap-4">
            <div className="flex items-end gap-2">
                <span className="text-4xl font-light text-white">{currentLoad}%</span>
                <span className="text-slate-400 mb-1">Global User Metric Load</span>
            </div>

            <div className="flex-1 w-full flex items-end justify-between gap-1 mt-auto h-24">
                {load.map((val, i) => (
                    <div key={i} className="flex-1 bg-slate-800 rounded-t-sm relative overflow-hidden group">
                        <div
                            className="absolute bottom-0 left-0 w-full bg-blue-500 transition-all duration-300"
                            style={{ height: `${val}%` }}
                        />
                    </div>
                ))}
            </div>
        </div>
    );
}
