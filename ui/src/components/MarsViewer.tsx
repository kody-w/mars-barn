import MarsScene from './MarsScene';
import ColonyHUD from './ColonyHUD';

interface MarsViewerProps {
  onBack?: () => void;
}

export default function MarsViewer({ onBack }: MarsViewerProps) {
  return (
    <div className="relative w-full h-full min-h-[600px] bg-black rounded-xl overflow-hidden border border-white/10">
      <MarsScene />
      <ColonyHUD />
      {onBack && (
        <button type="button"
          onClick={onBack}
          className="absolute top-4 left-4 z-50 flex items-center gap-2 px-4 py-2 rounded-full bg-black/60 backdrop-blur-sm border border-white/10 text-zinc-300 text-xs font-bold uppercase tracking-widest hover:bg-black/80 hover:text-white transition-all"
        >
          ← Orbital View
        </button>
      )}
    </div>
  );
}
