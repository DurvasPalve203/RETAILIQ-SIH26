import React, { useState, useEffect, useRef } from 'react';
import { 
  Camera, 
  X, 
  Check, 
  Radio, 
  RotateCw, 
  Sliders, 
  Sparkles, 
  Zap, 
  Wifi, 
  WifiOff, 
  Cpu, 
  Smartphone, 
  Tv,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';
import { CameraStatus } from '../types';

interface CameraSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSourceChanged?: () => void;
}

export const CameraSourceModal: React.FC<CameraSourceModalProps> = ({
  isOpen,
  onClose,
  onSourceChanged
}) => {
  const [source, setSource] = useState<string>('http://192.168.1.14:8080/video');
  const [rotation, setRotation] = useState<number>(0);
  const [status, setStatus] = useState<CameraStatus | null>(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ msg: string; type: 'success' | 'error' | 'info' } | null>(null);
  
  const hasInitializedRef = useRef(false);

  const fetchStatus = async () => {
    try {
      const s = await api.getCameraStatus();
      setStatus(s);
      // Only set initial source & rotation once when modal opens so typing is NOT overwritten!
      if (!hasInitializedRef.current && s?.source) {
        setSource(s.source);
        setRotation(s.rotation_deg || 0);
        hasInitializedRef.current = true;
      }
    } catch (e) {}
  };

  useEffect(() => {
    if (!isOpen) {
      hasInitializedRef.current = false;
      return;
    }
    fetchStatus();
    const timer = setInterval(fetchStatus, 2000);
    return () => clearInterval(timer);
  }, [isOpen]);

  if (!isOpen) return null;

  const handleApplySource = async (targetSource: string, rotDeg: number = rotation) => {
    setSaving(true);
    setFeedback({ msg: `Connecting to camera source "${targetSource}"...`, type: 'info' });
    try {
      const res = await api.setCameraSource(targetSource, rotDeg);
      setSource(targetSource);
      setRotation(rotDeg);
      
      setTimeout(async () => {
        const s = await api.getCameraStatus();
        setStatus(s);
        if (s.is_connected) {
          setFeedback({ msg: `Camera source "${targetSource}" is successfully CONNECTED & streaming!`, type: 'success' });
        } else {
          setFeedback({ msg: `Watchdog is searching for "${targetSource}". If it's a mobile stream, ensure IP Webcam server is running.`, type: 'info' });
        }
      }, 1000);

      if (onSourceChanged) onSourceChanged();
    } catch (e: any) {
      setFeedback({ msg: `Failed to set source: ${e.message || 'Error'}`, type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const isLive = status ? !status.is_synthetic : source !== 'synthetic';

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl space-y-5 p-6 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-lg">
              <Camera className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold text-white">Camera Feed & Ingestion Setup</h3>
                <span className={`px-2.5 py-0.5 text-[10px] font-extrabold rounded-full uppercase font-mono ${
                  isLive ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/50' : 'bg-amber-950 text-amber-300 border border-amber-500/50'
                }`}>
                  {isLive ? 'LIVE CAMERA MODE' : 'SIMULATION MODE'}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Connect Android IP Webcam, RTSP stream, local USB camera, or switch to simulated demo.
              </p>
            </div>
          </div>

          <button onClick={onClose} className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
            <X className="w-5 h-5" />
          </button>
        </div>

        {feedback && (
          <div className={`p-3 rounded-xl border text-xs flex items-center space-x-2 ${
            feedback.type === 'success' 
              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-200' 
              : feedback.type === 'error'
              ? 'bg-rose-950/60 border-rose-500/40 text-rose-200'
              : 'bg-cyan-950/60 border-cyan-500/40 text-cyan-200'
          }`}>
            <Zap className="w-4 h-4 flex-shrink-0" />
            <span>{feedback.msg}</span>
          </div>
        )}

        {/* Live Status HUD */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Feed Status</span>
            <div className="flex items-center space-x-1.5 mt-1 font-bold">
              {status?.is_connected ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-emerald-400">CONNECTED</span>
                </>
              ) : status?.is_reconnecting ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                  <span className="text-amber-400">RECONNECTING...</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span className="text-rose-400">CONNECTING...</span>
                </>
              )}
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Capture FPS</span>
            <p className="text-lg font-bold font-mono text-cyan-400 mt-0.5">{status?.fps_actual ?? 0.0}</p>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Active Source</span>
            <p className="text-xs font-mono text-slate-200 mt-1 truncate" title={status?.source || source}>
              {status?.source || source}
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Reconnect Retries</span>
            <p className="text-lg font-bold font-mono text-slate-300 mt-0.5">{status?.reconnect_attempts ?? 0}</p>
          </div>
        </div>

        {/* Source Configuration Options */}
        <div className="space-y-4 overflow-y-auto pr-1">
          {/* Quick Presets */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">Select Camera Hardware Preset</label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setSource('http://192.168.1.14:8080/video')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  source.includes(':8080') || source.includes('http')
                    ? 'bg-cyan-950/50 border-cyan-500 text-cyan-200 shadow-md shadow-cyan-950/20'
                    : 'bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center space-x-1.5 font-bold text-xs">
                  <Smartphone className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Android IP Webcam</span>
                </div>
                <p className="text-[10px] text-slate-400 mt-1 font-mono">http://&lt;ip&gt;:8080/video</p>
              </button>

              <button
                type="button"
                onClick={() => setSource('0')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  source === '0' || source === '1'
                    ? 'bg-cyan-950/50 border-cyan-500 text-cyan-200 shadow-md shadow-cyan-950/20'
                    : 'bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center space-x-1.5 font-bold text-xs">
                  <Tv className="w-3.5 h-3.5 text-cyan-400" />
                  <span>USB / Built-in Webcam</span>
                </div>
                <p className="text-[10px] text-slate-400 mt-1 font-mono">Camera Index 0 (or 1)</p>
              </button>

              <button
                type="button"
                onClick={() => setSource('synthetic')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  source === 'synthetic'
                    ? 'bg-amber-950/50 border-amber-500 text-amber-200 shadow-md shadow-amber-950/20'
                    : 'bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center space-x-1.5 font-bold text-xs">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  <span>Synthetic Simulation</span>
                </div>
                <p className="text-[10px] text-slate-400 mt-1 font-mono">Demo Fallback Mode</p>
              </button>
            </div>
          </div>

          {/* Custom Stream Input */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-400 uppercase">Camera Stream URI or Device Index</label>
            <input
              type="text"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="e.g. http://192.168.1.100:8080/video or 0 or 1"
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
            />
            <p className="text-[10px] text-slate-500">
              For Android IP Webcam: install "IP Webcam" app from Play Store, click "Start server" at bottom, and enter the displayed IPv4 address.
            </p>
          </div>

          {/* Orientation Rotation */}
          <div className="space-y-1.5 pt-2 border-t border-slate-800">
            <label className="text-[11px] font-semibold text-slate-400 uppercase flex items-center gap-1.5">
              <RotateCw className="w-3.5 h-3.5 text-cyan-400" /> <span>Phone Camera Orientation / Rotation</span>
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[
                { deg: 0, label: '0° (Normal)' },
                { deg: 90, label: '90° (CW)' },
                { deg: 180, label: '180° (Inverted)' },
                { deg: 270, label: '270° (CCW)' }
              ].map((opt) => (
                <button
                  key={opt.deg}
                  type="button"
                  onClick={() => setRotation(opt.deg)}
                  className={`py-2 rounded-xl text-xs font-semibold border transition-all ${
                    rotation === opt.deg
                      ? 'bg-cyan-600/30 text-cyan-300 border-cyan-500'
                      : 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <button
            onClick={() => handleApplySource('synthetic', 0)}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 text-xs font-semibold flex items-center space-x-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Switch to Simulation Mode</span>
          </button>

          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
            >
              Close
            </button>
            <button
              onClick={() => handleApplySource(source, rotation)}
              disabled={saving}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-cyan-600/25 flex items-center space-x-1.5 disabled:opacity-50"
            >
              <Check className="w-4 h-4" />
              <span>{saving ? 'Connecting...' : 'Connect & Apply Camera'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
