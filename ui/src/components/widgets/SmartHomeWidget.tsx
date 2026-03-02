
import { useState } from 'react';

import { Lightbulb, Thermometer } from 'lucide-react';


export default function SmartHomeWidget() {
    const [lights, setLights] = useState(true);
    const [temp, setTemp] = useState(72);

    return (
        <div className="flex flex-col h-full gap-4">
            <div className="flex justify-between items-center bg-white/5 p-3 rounded-lg border border-white/10">
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-full ${lights ? 'bg-yellow-500/20 text-yellow-500' : 'bg-slate-800 text-slate-500'}`}>
                        <Lightbulb size={20} />
                    </div>
                    <div>
                        <p className="font-medium text-slate-200">Living Room Hue</p>
                        <p className="text-xs text-slate-500">{lights ? 'On - 85% Brightness' : 'Off'}</p>
                    </div>
                </div>
                <button
                    onClick={(e) => { e.stopPropagation(); setLights(!lights); }}
                    className={`w-12 h-6 rounded-full relative transition-colors ${lights ? 'bg-blue-500' : 'bg-slate-700'}`}
                >
                    <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all ${lights ? 'left-7' : 'left-1'}`} />
                </button>
            </div>

            <div className="flex justify-between items-center bg-white/5 p-3 rounded-lg border border-white/10 mt-auto">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-full bg-red-500/20 text-red-400">
                        <Thermometer size={20} />
                    </div>
                    <div>
                        <p className="font-medium text-slate-200">HVAC Thermostat</p>
                        <p className="text-xs text-slate-500">Target: {temp}°F</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={(e) => { e.stopPropagation(); setTemp(t => t - 1); }} className="w-8 h-8 rounded bg-white/10 flex items-center justify-center hover:bg-white/20">-</button>
                    <button onClick={(e) => { e.stopPropagation(); setTemp(t => t + 1); }} className="w-8 h-8 rounded bg-white/10 flex items-center justify-center hover:bg-white/20">+</button>
                </div>
            </div>
        </div>
    );
}
