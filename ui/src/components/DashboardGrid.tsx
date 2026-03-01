"use client";

import { useDashboardStore, type WidgetData } from '@/lib/store';
import { AnimatePresence } from 'framer-motion';
import WidgetContainer from './WidgetContainer';
import { ArchiveRestore, RefreshCcw } from 'lucide-react';
import PlatformStatsWidget from './widgets/PlatformStatsWidget';
import AgentActivityWidget from './widgets/AgentActivityWidget';
import CronManagerWidget from './widgets/CronManagerWidget';
import TrendingWidget from './widgets/TrendingWidget';
import RappterControlWidget from './widgets/RappterControlWidget';
import ColonyGPTWidget from './widgets/ColonyGPTWidget';

export default function DashboardGrid() {
    const { widgets, resetScores, restoreWidget } = useDashboardStore();

    // Active widgets on the main stage
    const activeWidgets = widgets.filter((w: WidgetData) => !w.isArchived);

    // Sort heavily dictates the layout. Highest scores go first (top/left).
    const sortedActiveWidgets = [...activeWidgets].sort((a: WidgetData, b: WidgetData) => {
        return b.score - a.score;
    });

    const archivedWidgets = widgets.filter((w: WidgetData) => w.isArchived);

    return (
        <div className="h-full w-full flex flex-col pt-8 px-8 pb-4 relative overflow-y-auto">

            {/* Header area */}
            <div className="flex items-center justify-between mb-8 shrink-0">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white mb-1">
                        Homelab Operations
                    </h1>
                    <p className="text-sm text-slate-400">
                        The interface adapts to your workflow. Higher usage = higher priority space.
                    </p>
                </div>
                <button
                    onClick={resetScores}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/5 hover:bg-white/10 text-sm text-slate-300 transition-colors border border-white/10"
                >
                    <RefreshCcw size={14} /> Reset Layout Learning
                </button>
            </div>

            {/* The Evolving Grid Stage */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 auto-rows-min pb-20">
                <AnimatePresence>
                    {sortedActiveWidgets.map((widget: WidgetData) => (
                        <WidgetContainer key={widget.id} widget={widget}>
                            {widget.type === 'PLATFORM_STATS' && <PlatformStatsWidget />}
                            {widget.type === 'AGENT_ACTIVITY' && <AgentActivityWidget />}
                            {widget.type === 'CRON_MANAGER' && <CronManagerWidget />}
                            {widget.type === 'TRENDING_TOPICS' && <TrendingWidget />}
                            {widget.type === 'RAPPTER_CONTROL' && <RappterControlWidget />}
                            {widget.type === 'COLONY_GPT' && <ColonyGPTWidget />}
                        </WidgetContainer>
                    ))}
                </AnimatePresence>

                {activeWidgets.length === 0 && (
                    <div className="col-span-full h-40 flex items-center justify-center text-slate-500 italic">
                        All modules archived.
                    </div>
                )}
            </div>

            {/* Archived / Low Priority Drawer */}
            {archivedWidgets.length > 0 && (
                <div className="mt-auto shrink-0 border-t border-white/10 pt-4 pb-4">
                    <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3 flex items-center gap-2">
                        <ArchiveRestore size={14} /> Archive / Low Priority
                    </h4>
                    <div className="flex gap-3 flex-wrap">
                        {archivedWidgets.map((w: WidgetData) => (
                            <button
                                key={w.id}
                                onClick={() => restoreWidget(w.id)}
                                className="px-3 py-1.5 rounded-full bg-surface border border-white/10 text-sm text-slate-400 hover:text-white hover:border-slate-500 transition-all flex items-center gap-2 group"
                            >
                                {w.title}
                                <span className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">Restore</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

        </div>
    );
}
