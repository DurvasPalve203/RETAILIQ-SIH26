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
  Zap,
  Users,
  Smartphone,
  Volume2
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

  const handleTestSms = async () => {
    try {
      await api.testAlertChannel('sms', 'CRITICAL', 'Emergency stockout and queue breach trigger');
      setStatusMsg('Dispatched SIM800L GSM AT SMS Sequence');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e) {
      console.error(e);
    }
  };

  const handleTestBuzzer = async () => {
    try {
      await api.testAlertChannel('buzzer', 'CRITICAL');
      setStatusMsg('Triggered Continuous Piezo Buzzer Alert');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-xl overflow-hidden shadow-2xl p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            <h3 className="text-base font-bold text-white">Edge Simulation & Hardware Diagnostics</h3>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {statusMsg && (
          <div className="p-3 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-200 text-xs flex items-center space-x-2 animate-bounce">
            <Zap className="w-4 h-4 text-cyan-400 flex-shrink-0" />
            <span>{statusMsg}</span>
          </div>
        )}

        <div className="space-y-4 max-h-[65vh] overflow-y-auto pr-1">
          {/* Queue Intelligence Simulation */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" /> <span>Queue Formation & Checkout Sim</span>
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => handleAction('add_queue', {}, 'Added Shopper to Queue Line')}
                className="p-3 rounded-xl bg-cyan-950/30 hover:bg-cyan-950/60 border border-cyan-500/30 text-cyan-200 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div>+ Add Shopper</div>
                <p className="text-[10px] text-cyan-400/80 font-normal">Joins back of line</p>
              </button>

              <button
                onClick={() => handleAction('serve_queue', {}, 'Customer Checked Out (Service Complete)')}
                className="p-3 rounded-xl bg-emerald-950/30 hover:bg-emerald-950/60 border border-emerald-500/30 text-emerald-200 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div>Serve Customer</div>
                <p className="text-[10px] text-emerald-400/80 font-normal">Front customer exits</p>
              </button>

              <button
                onClick={() => handleAction('queue_surge', {}, 'Queue Surge Triggered (+3 Shoppers)')}
                className="p-3 rounded-xl bg-amber-950/30 hover:bg-amber-950/60 border border-amber-500/30 text-amber-200 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div>Queue Surge</div>
                <p className="text-[10px] text-amber-400/80 font-normal">Buildup &gt; 5 min wait</p>
              </button>
            </div>
          </div>

          {/* Stock-Out Simulation */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-rose-300 uppercase tracking-wider flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5" /> <span>Shelf Stock-Out & Depletion</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleAction('deplete', { zone_id: 'zone-shelf-01', count: 0 }, 'Emptied Zone 1: Organic Whole Milk')}
                className="p-3 rounded-xl bg-rose-950/30 hover:bg-rose-950/50 border border-rose-500/30 text-rose-300 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div>Empty Milk (Zone 1)</div>
                <p className="text-[10px] text-rose-400/80 font-normal">Triggers CRITICAL stock-out</p>
              </button>

              <button
                onClick={() => handleAction('restock', { zone_id: 'zone-shelf-01' }, 'Restocked Zone 1: Organic Milk')}
                className="p-3 rounded-xl bg-emerald-950/30 hover:bg-emerald-950/50 border border-emerald-500/30 text-emerald-300 text-xs font-bold text-left space-y-1 transition-all"
              >
                <div>Restock Milk (Z1)</div>
                <p className="text-[10px] text-emerald-400/80 font-normal">Auto-resolves alert</p>
              </button>
            </div>
          </div>

          {/* Hardware & Peripherals Test */}
          <div className="space-y-2 pt-2 border-t border-slate-800">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Volume2 className="w-3.5 h-3.5 text-blue-400" /> <span>Hardware Trigger Diagnostics</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={handleTestBuzzer}
                className="p-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-left space-y-1 text-slate-200"
              >
                <div>Test Continuous Alarm</div>
                <p className="text-[10px] text-slate-400 font-normal">Buzzer GPIO pin 18</p>
              </button>

              <button
                onClick={handleTestSms}
                className="p-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-left space-y-1 text-slate-200"
              >
                <div>Test SIM800L SMS</div>
                <p className="text-[10px] text-slate-400 font-normal">UART AT Command sequence</p>
              </button>
            </div>
          </div>

          {/* Environmental Edge Cases */}
          <div className="space-y-2 pt-2 border-t border-slate-800">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">Environmental Edge Cases</label>
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
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
          >
            Close Controls
          </button>
        </div>
      </div>
    </div>
  );
};
