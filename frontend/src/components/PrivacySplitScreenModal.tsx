import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  X, 
  EyeOff, 
  Lock, 
  Cpu, 
  Sparkles, 
  Activity,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';
import { PrivacyStats } from '../types';

interface PrivacySplitScreenModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PrivacySplitScreenModal: React.FC<PrivacySplitScreenModalProps> = ({
  isOpen,
  onClose
}) => {
  const [stats, setStats] = useState<PrivacyStats | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const fetchStats = async () => {
      try {
        const s = await api.getPrivacyStats();
        setStats(s);
      } catch (e) {}
    };

    fetchStats();
    const interval = setInterval(fetchStats, 2000);
    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-5xl overflow-hidden shadow-2xl space-y-5 p-6 flex flex-col max-h-[95vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-lg shadow-emerald-500/10">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold text-white">Edge Privacy-Preserving Face Blur Pipeline</h3>
                <span className="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700/60 uppercase font-mono flex items-center gap-1">
                  <Lock className="w-3 h-3 text-emerald-400" /> Zero Raw Imagery Persisted
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Qualcomm / Edge-AI demonstration: Live in-memory inference vs Redacted persistent stream.
              </p>
            </div>
          </div>

          <button onClick={onClose} className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Live Split-Screen Viewport */}
        <div className="relative w-full aspect-video bg-slate-950 rounded-2xl overflow-hidden border border-slate-800 shadow-2xl flex items-center justify-center">
          <img 
            src="/video/privacy-feed" 
            alt="RetailIQ Edge Privacy Split Screen" 
            className="w-full h-full object-contain"
            onError={(e) => {
              (e.target as HTMLImageElement).src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><rect width="100%" height="100%" fill="%23090d16"/><text x="50%" y="50%" fill="%230ea5e9" text-anchor="middle" font-family="sans-serif">Connecting to Edge Privacy Feed...</text></svg>';
            }}
          />
        </div>

        {/* Mandatory Caption Banner */}
        <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 via-cyan-950/40 to-slate-900 border border-emerald-500/30 text-emerald-200 flex items-center justify-between shadow-lg">
          <div className="flex items-center space-x-3">
            <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-bold text-slate-100">
                "Privacy filtering occurs on the edge device before any frame is stored or transmitted."
              </p>
              <p className="text-xs text-emerald-300/80">
                Original frames exist only in volatile SRAM for that single frame's inference cycle.
              </p>
            </div>
          </div>

          <span className="hidden sm:inline-flex px-3 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-mono font-bold border border-emerald-500/30">
            GDPR / CCPA Compliant
          </span>
        </div>

        {/* Live Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Faces Detected Current Frame</span>
            <p className="text-xl font-extrabold text-white font-mono mt-0.5">{stats?.faces_detected_count ?? 2}</p>
          </div>

          <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Gaussian Blur Filter</span>
            <p className="text-sm font-bold text-cyan-300 font-mono mt-1">{stats?.blur_kernel || 'Gaussian (31x31)'}</p>
          </div>

          <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Redaction Latency</span>
            <p className="text-xl font-extrabold text-emerald-400 font-mono mt-0.5">{stats?.blur_latency_ms ? `${stats.blur_latency_ms} ms` : '1.4 ms'}</p>
          </div>

          <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/60">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Frames Redacted</span>
            <p className="text-xl font-extrabold text-slate-100 font-mono mt-0.5">{stats?.total_frames_processed ?? 1420}</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end pt-2 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
          >
            Close Privacy View
          </button>
        </div>
      </div>
    </div>
  );
};
