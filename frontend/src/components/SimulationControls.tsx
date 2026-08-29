import React, { useState } from 'react';
import { 
  Sliders, 
  X, 
  Flame, 
  RefreshCw, 
  EyeOff, 
  Moon, 
  CheckCircle2, 
  Sparkles,
  Zap
} from 'lucide-react';
import { api } from '../services/api';

interface SimulationControlsProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({ isOpen, onClose }) => {
  const [occluded, setOccluded] = useState(false);
  const [lowLight, setLowLight] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAction = async (action: string, params: any, label: string) => {
    try {
      await api.controlSimulation(action, params);
      setStatusMsg(label);
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleOcclusion = () => {
    const next = !occluded;
    setOccluded(next);
    handleAction('occlusion', { enabled: next }, next ? 'Camera Occlusion ON (Alerts Suppressed)' : 'Camera Occlusion OFF');
  };

  const handleToggleLowLight = () => {
    const next = !lowLight;
    setLowLight(next);
    handleAction('low_light', { enabled: next }, next ? 'Low-Light Mode ON' : 'Normal Lighting Restored');
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-bold text-white">Interactive Edge Simulation Controls</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {statusMsg && (
          <div className="p-3 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-200 text-xs flex items-center space-x-2">
            <Zap className="w-4 h-4 text-cyan-400 flex-shrink-0" />
            <span>{statusMsg}</span>
          </div>
        )}

        <div className="space-y-4">
          {/* Stock-Out Simulation */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">Trigger Shelf Stock-Out</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleAction('deplete', { zone_id: 'zone-shelf-01', count: 0 }, 'Emptied Zone 1: Organic Whole Milk')}
                className="p-3 rounded-xl bg-rose-950/30 hover:bg-rose-950/50 border border-rose-500/30 text-rose-300 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div className="flex items-center space-x-1.5"><Flame className="w-3.5 h-3.5 text-rose-400" /> <span>Empty Milk (Zone 1)</span></div>
                <p className="text-[10px] text-rose-400/80 font-normal">Triggers High Priority Alert</p>
              </button>

              <button
                onClick={() => handleAction('deplete', { zone_id: 'zone-shelf-03', count: 1 }, 'Depleted Zone 3: Cold Brew to 1 unit')}
                className="p-3 rounded-xl bg-amber-950/30 hover:bg-amber-950/50 border border-amber-500/30 text-amber-300 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div className="flex items-center space-x-1.5"><Flame className="w-3.5 h-3.5 text-amber-400" /> <span>Deplete Cold Brew</span></div>
                <p className="text-[10px] text-amber-400/80 font-normal">Triggers ETA Prediction</p>
              </button>
            </div>
          </div>

          {/* Restock Simulation */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">Simulate Restock Recovery</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleAction('restock', { zone_id: 'zone-shelf-01' }, 'Restocked Zone 1: Organic Milk')}
                className="p-3 rounded-xl bg-emerald-950/30 hover:bg-emerald-950/50 border border-emerald-500/30 text-emerald-300 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div className="flex items-center space-x-1.5"><RefreshCw className="w-3.5 h-3.5 text-emerald-400" /> <span>Restock Milk (Z1)</span></div>
                <p className="text-[10px] text-emerald-400/80 font-normal">Closes alert automatically</p>
              </button>

              <button
                onClick={() => handleAction('restock', { zone_id: 'zone-shelf-03' }, 'Restocked Zone 3: Cold Brew')}
                className="p-3 rounded-xl bg-emerald-950/30 hover:bg-emerald-950/50 border border-emerald-500/30 text-emerald-300 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div className="flex items-center space-x-1.5"><RefreshCw className="w-3.5 h-3.5 text-emerald-400" /> <span>Restock Cold Brew (Z3)</span></div>
                <p className="text-[10px] text-emerald-400/80 font-normal">Closes alert automatically</p>
              </button>
            </div>
          </div>

          {/* Environmental Edge Cases */}
          <div className="space-y-2 pt-2 border-t border-slate-800">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">Edge Case Toggles</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={handleToggleOcclusion}
                className={`p-3 rounded-xl border text-xs font-bold text-left space-y-1 transition-all ${
                  occluded ? 'bg-amber-500/20 border-amber-500/50 text-amber-300' : 'bg-slate-800 border-slate-700 text-slate-300'
                }`}
              >
                <div className="flex items-center space-x-1.5"><EyeOff className="w-3.5 h-3.5" /> <span>Camera Occlusion</span></div>
                <p className="text-[10px] text-slate-400 font-normal">{occluded ? 'Active (Suppressed)' : 'Disabled'}</p>
              </button>

              <button
                onClick={handleToggleLowLight}
                className={`p-3 rounded-xl border text-xs font-bold text-left space-y-1 transition-all ${
                  lowLight ? 'bg-blue-500/20 border-blue-500/50 text-blue-300' : 'bg-slate-800 border-slate-700 text-slate-300'
                }`}
              >
                <div className="flex items-center space-x-1.5"><Moon className="w-3.5 h-3.5" /> <span>Low-Light Mode</span></div>
                <p className="text-[10px] text-slate-400 font-normal">{lowLight ? 'Active (CLAHE on)' : 'Disabled'}</p>
              </button>
            </div>
          </div>
        </div>

        <div className="pt-2 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
          >
            Close Controls
          </button>
        </div>
      </div>
    </div>
  );
};
