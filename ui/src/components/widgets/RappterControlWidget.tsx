import useSWR from "swr";
import { useState, useRef, useEffect } from 'react';
import { RadioReceiver, Send, Loader2, User, Bot } from 'lucide-react';

const fetcher = (url: string) => fetch(url).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });

interface Message {
    role: 'user' | 'agent';
    content: string;
    isError?: boolean;
}

export default function RappterControlWidget() {
    const { data } = useSWR('/api/engine/status', fetcher, { refreshInterval: 10000 });

    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);

    const isOnline = data?.online === true;

    // Auto-scroll to bottom of messages
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, loading]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const query = input;
        setInput('');
        setLoading(true);
        setMessages(prev => [...prev, { role: 'user', content: query }]);

        try {
            const res = await fetch('/api/engine/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            const result = await res.json();
            if (result.success) {
                setMessages(prev => [...prev, { role: 'agent', content: result.output }]);
            } else {
                setMessages(prev => [...prev, { role: 'agent', content: `Error: ${result.error || result.stderr}`, isError: true }]);
            }
        } catch (err: unknown) {
            setMessages(prev => [...prev, { role: 'agent', content: `Network Error: ${err instanceof Error ? err.message : 'Connection failed'}`, isError: true }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full gap-4">
            {/* Status Header */}
            <div className="flex items-center justify-between bg-white/5 p-3 rounded-lg border border-white/10 shrink-0 shadow-lg">
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-full ${isOnline ? 'bg-blue-500/20 text-blue-400' : 'bg-red-500/20 text-red-400'}`}>
                        <RadioReceiver size={18} />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-white tracking-wide">OPEN RAPPTER</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                            <div className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">{isOnline ? 'ACTIVE' : 'OFFLINE'}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Chat Terminal Area (Moltbot UI style) */}
            <div
                ref={scrollRef}
                className="flex-1 rounded-xl bg-[#0F111A] border border-white/10 p-4 overflow-y-auto font-sans text-sm flex flex-col gap-4 shadow-inner"
            >
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs text-center opacity-80">
                        <Bot size={40} className="mb-3 text-blue-500/50" />
                        <p>Rappter Agent Online.<br />Ready for administrative tasks.</p>
                    </div>
                ) : (
                    messages.map((msg, i) => (
                        <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role === 'agent' && (
                                <div className="w-8 h-8 rounded shrink-0 bg-blue-600/20 flex items-center justify-center border border-blue-500/30">
                                    <Bot size={16} className="text-blue-400" />
                                </div>
                            )}
                            <div className={`rounded-xl px-4 py-2.5 max-w-[85%] leading-relaxed tracking-wide ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white shadow-md'
                                    : msg.isError
                                        ? 'bg-red-950/50 text-red-400 border border-red-900/50 font-mono text-xs'
                                        : 'bg-white/5 text-slate-200 border border-white/5 whitespace-pre-wrap'
                                }`}>
                                {msg.content}
                            </div>
                            {msg.role === 'user' && (
                                <div className="w-8 h-8 rounded-full shrink-0 bg-slate-800 flex items-center justify-center">
                                    <User size={16} className="text-slate-400" />
                                </div>
                            )}
                        </div>
                    ))
                )}
                {loading && (
                    <div className="flex gap-3 justify-start items-center text-slate-500 text-xs font-mono animate-pulse">
                        <div className="w-8 h-8 rounded shrink-0 bg-blue-600/10 flex items-center justify-center border border-blue-500/20">
                            <Loader2 size={14} className="animate-spin text-blue-400" />
                        </div>
                        <span>Executing payload via local engine...</span>
                    </div>
                )}
            </div>

            {/* Command Input Area */}
            <form onSubmit={handleSubmit} className="flex gap-2 mt-auto shrink-0 relative">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={isOnline ? "Admin command..." : "Engine Offline"}
                    disabled={!isOnline || loading}
                    onClick={(e) => e.stopPropagation()}
                    onMouseEnter={(e) => e.stopPropagation()}
                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-3 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition-colors disabled:opacity-50 text-sm font-sans shadow-lg"
                />
                <button type="button"
                    type="submit"
                    disabled={!isOnline || loading || !input.trim()}
                    onClick={(e) => e.stopPropagation()}
                    className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white rounded-lg px-4 flex items-center justify-center transition-colors shadow-lg"
                >
                    {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                </button>
            </form>
        </div>
    );
}
