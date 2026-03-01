"use client";

import { useDashboardStore, WidgetData } from '@/lib/store';
import { motion } from 'framer-motion';
import { ReactNode } from 'react';
import {
    BarChart3,
    Users,
    CalendarClock,
    Flame,
    RadioReceiver,
    X
} from 'lucide-react';

interface Props {
    widget: WidgetData;
    children: ReactNode;
}

const getIcon = (type: string) => {
    switch (type) {
        case 'PLATFORM_STATS': return <BarChart3 size={18} />;
        case 'AGENT_ACTIVITY': return <Users size={18} />;
        case 'TRENDING_TOPICS': return <Flame size={18} />;
        case 'CRON_MANAGER': return <CalendarClock size={18} />;
        case 'RAPPTER_CONTROL': return <RadioReceiver size={18} />;
        default: return <BarChart3 size={18} />;
    }
};

export default function WidgetContainer({ widget, children }: Props) {
    const { recordInteraction, archiveWidget } = useDashboardStore();

    // The telemetry hooks
    const handleHover = () => recordInteraction(widget.id, 1);
    const handleClick = () => recordInteraction(widget.id, 5);

    // Dynamic styling based on score (Heuristic evolution)
    // 100 is baseline.
    // > 200 = Primary/Hero widget
    // < 50 = Demoted/Shrinking widget
    let sizeClass = "col-span-1 min-h-[250px]";
    let borderClass = "border-surface-rings";
    let opacity = 1;

    if (widget.score > 300) {
        sizeClass = "col-span-2 min-h-[350px]"; // Hero size
        borderClass = "border-accent shadow-[0_0_15px_rgba(59,130,246,0.3)]";
    } else if (widget.score > 200) {
        sizeClass = "col-span-2 min-h-[250px]"; // Featured size
        borderClass = "border-slate-500";
    } else if (widget.score < 50) {
        opacity = 0.6; // Demoted visibility
    }

    return (
        <motion.div
            layout // This single prop allows Framer Motion to automatically animate position/size changes!
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onMouseEnter={handleHover}
            onClick={handleClick}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className={`widget-panel flex flex-col relative group rounded-[2rem] overflow-hidden backdrop-blur-2xl bg-white/5 border border-white/5 shadow-2xl transition-all ${sizeClass} ${borderClass}`}
        >
            {/* Header */}
            <div className="flex items-center gap-2 p-5 border-b border-white/5 bg-white/5">
                <div className="text-slate-400">
                    {getIcon(widget.type)}
                </div>
                <h3 className="font-semibold text-sm tracking-wide text-slate-200">
                    {widget.title}
                </h3>
                {/* Interaction/Score badge for debug visualization */}
                {/* <span className="ml-auto text-xs font-mono text-slate-500">Pts: {Math.round(widget.score)}</span> */}

                <div className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                    <button
                        onClick={(e) => { e.stopPropagation(); archiveWidget(widget.id); }}
                        className="text-slate-500 hover:text-red-400 transition-colors p-1"
                    >
                        <X size={14} />
                    </button>
                </div>
            </div>

            {/* Content Body */}
            <div className="flex-1 p-5 overflow-hidden relative">
                {children}
            </div>
        </motion.div>
    );
}
