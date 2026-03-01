"use client";



export default function NetworkWidget() {
    return (
        <div className="flex flex-col h-full justify-between items-center relative overflow-hidden bg-gradient-to-br from-black to-slate-950 p-4 rounded-lg rounded-tl-none -m-4">
            {/* Fake radar map effect for network load */}
            <div className="absolute inset-0 opacity-20 pointer-events-none">
                <div className="w-[150%] h-[150%] absolute border-4 border-blue-500 rounded-full left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-[ping_4s_ease-out_infinite]" />
                <div className="w-full h-full absolute border-2 border-blue-400 rounded-full left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-[ping_4s_ease-out_1s_infinite]" />
            </div>

            <div className="z-10 bg-black/60 backdrop-blur-md p-4 rounded-xl border border-white/10 flex items-center gap-4 text-center mt-auto mb-auto">
                <div>
                    <p className="text-xs text-green-400 uppercase tracking-widest font-semibold mb-1">Inbound RX</p>
                    <p className="text-2xl font-mono text-white">4.2 GB/s</p>
                </div>
                <div className="h-10 w-px bg-white/20" />
                <div>
                    <p className="text-xs text-blue-400 uppercase tracking-widest font-semibold mb-1">Outbound TX</p>
                    <p className="text-2xl font-mono text-white">1.8 GB/s</p>
                </div>
            </div>
        </div>
    );
}
