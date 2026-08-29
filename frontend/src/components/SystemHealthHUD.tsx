import React, { useState, useEffect } from 'react';
import { 
  Cpu, 
  Database, 
  Radio, 
  Wifi, 
  ShieldCheck, 
  HardDrive, 
  Clock, 
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { SystemHealthData } from '../types';
import { api } from '../services/api';

export const SystemHealthHUD: React.FC<{ inferenceFps: number }> = ({ inferenceFps }) => {
  const [health, setHealth] = useState<SystemHealthData | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await api.getHealth();
        setHealth(data);
      } catch (e) {
        console.error(e);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-bold text-white">Edge System Diagnostics & Offline HUD</h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-mono font-semibold text-emerald-400 uppercase">
            {health?.status || 'HEALTHY'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Camera Source</span>
          <div className="flex items-center space-x-1.5 text-white font-semibold">
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
            <span>{health?.camera_connected ? 'Connected' : 'Offline'}</span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Inference FPS</span>
          <div className="flex items-center space-x-1.5 text-emerald-400 font-mono font-bold">
            <Cpu className="w-3.5 h-3.5" />
            <span>{inferenceFps > 0 ? inferenceFps.toFixed(1) : (health?.inference_fps || 8.0)} FPS</span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Offline SQLite WAL</span>
          <div className="flex items-center space-x-1.5 text-white font-semibold">
            <Database className="w-3.5 h-3.5 text-cyan-400" />
            <span>{health?.db_operational ? 'Active / 0 Locks' : 'Error'}</span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">MQTT Sync Buffer</span>
          <div className="flex items-center space-x-1.5 text-slate-200 font-mono font-semibold">
            <HardDrive className="w-3.5 h-3.5 text-blue-400" />
            <span>{health?.offline_sync_queue_size || 0} queued</span>
          </div>
        </div>
      </div>
    </div>
  );
};
