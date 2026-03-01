import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type WidgetType = 'PLATFORM_STATS' | 'AGENT_ACTIVITY' | 'CRON_MANAGER' | 'TRENDING_TOPICS' | 'RAPPTER_CONTROL' | 'COLONY_GPT';

export interface WidgetData {
    id: string;
    type: WidgetType;
    title: string;
    score: number;
    isArchived: boolean;
}

const INITIAL_WIDGETS: WidgetData[] = [
    { id: 'w-stats', type: 'PLATFORM_STATS', title: 'Platform Statistics', score: 100, isArchived: false },
    { id: 'w-agents', type: 'AGENT_ACTIVITY', title: 'Live Agent Roster', score: 100, isArchived: false },
    { id: 'w-trends', type: 'TRENDING_TOPICS', title: 'Network Trending Topics', score: 100, isArchived: false },
    { id: 'w-cron', type: 'CRON_MANAGER', title: 'Scheduled Cron Jobs', score: 100, isArchived: false },
    { id: 'w-rappter', type: 'RAPPTER_CONTROL', title: 'Meta-Awareness Module', score: 100, isArchived: false },
    { id: 'w-gpt', type: 'COLONY_GPT', title: 'Colony MicroGPT', score: 100, isArchived: false },
];

interface DashboardState {
    widgets: WidgetData[];
    recordInteraction: (id: string, points: number) => void;
    resetScores: () => void;
    archiveWidget: (id: string) => void;
    restoreWidget: (id: string) => void;
}

export const useDashboardStore = create<DashboardState>()(
    persist(
        (set) => ({
            widgets: INITIAL_WIDGETS,

            // Increment score for a specific widget. Max cap to prevent integer overflow over years.
            recordInteraction: (id: string, points: number) => set((state: DashboardState) => {
                const updated = state.widgets.map((w: WidgetData) => {
                    if (w.id === id) {
                        const newScore = Math.min(w.score + points, 10000);
                        return { ...w, score: newScore, isArchived: false }; // Interaction natively unarchives
                    }
                    // Slight decay for others to allow shifts in habit
                    return { ...w, score: Math.max(w.score - (points * 0.05), 0) };
                });

                // Auto-archive logic if score falls extremely low compared to others
                // We'll manage archiving manually via UI for now to avoid jump scares, 
                // but the decay readies them for it.
                return { widgets: updated };
            }),

            resetScores: () => set({ widgets: INITIAL_WIDGETS }),

            archiveWidget: (id: string) => set((state: DashboardState) => ({
                widgets: state.widgets.map((w: WidgetData) => w.id === id ? { ...w, isArchived: true, score: 0 } : w)
            })),

            restoreWidget: (id: string) => set((state: DashboardState) => ({
                widgets: state.widgets.map((w: WidgetData) => w.id === id ? { ...w, isArchived: false, score: 50 } : w)
            }))
        }),
        {
            name: 'homelab-evolving-storage',
        }
    )
);
