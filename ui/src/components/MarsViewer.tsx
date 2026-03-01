import MarsScene from './MarsScene';
import ColonyHUD from './ColonyHUD';

export default function MarsViewer() {
  return (
    <div className="relative w-full h-full min-h-[600px] bg-black rounded-xl overflow-hidden border border-white/10">
      <MarsScene />
      <ColonyHUD />
    </div>
  );
}
