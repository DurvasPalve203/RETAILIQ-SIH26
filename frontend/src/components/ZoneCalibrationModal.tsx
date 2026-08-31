import React, { useState, useEffect } from 'react';
import { 
  X, 
  Check, 
  Plus, 
  Trash2, 
  Edit3, 
  Compass, 
  Users, 
  Camera, 
  Sparkles, 
  RefreshCw,
  Layers,
  Image as ImageIcon
} from 'lucide-react';
import { Zone, Point2D } from '../types';
import { api } from '../services/api';

interface ZoneCalibrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  zones: Zone[];
  onRefreshZones: () => void;
}

export const ZoneCalibrationModal: React.FC<ZoneCalibrationModalProps> = ({
  isOpen,
  onClose,
  zones,
  onRefreshZones
}) => {
  const [editingZones, setEditingZones] = useState<Zone[]>(zones);
  const [liveSnapshot, setLiveSnapshot] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [capturingBaseline, setCapturingBaseline] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const fetchLiveSnapshot = async () => {
    try {
      const snap = await api.getLiveSnapshot();
      if (snap?.image_base64) {
        setLiveSnapshot(snap.image_base64);
      }
    } catch (e) {}
  };

  useEffect(() => {
    if (isOpen) {
      setEditingZones(zones);
      fetchLiveSnapshot();
    }
  }, [isOpen, zones]);

  if (!isOpen) return null;

  const handleUpdateCapacity = (index: number, val: number) => {
    const next = [...editingZones];
    next[index].expected_capacity = val;
    setEditingZones(next);
  };

  const handleUpdateLabel = (index: number, val: string) => {
    const next = [...editingZones];
    next[index].label = val;
    setEditingZones(next);
  };

  const handleUpdateType = (index: number, type: any) => {
    const next = [...editingZones];
    next[index].zone_type = type;
    if (type === 'queue_zone' && !next[index].axis_start_xy) {
      next[index].axis_start_xy = { x: 0.28, y: 0.86 };
      next[index].axis_end_xy = { x: 0.70, y: 0.86 };
    }
    setEditingZones(next);
  };

  const handleCaptureBaseline = async (zoneId: string) => {
    setCapturingBaseline(zoneId);
    setFeedbackMsg(null);
    try {
      const res = await api.captureZoneBaseline(zoneId);
      setFeedbackMsg(`Captured fresh 100% full-shelf baseline reference for "${zoneId}"`);
      onRefreshZones();
    } catch (e: any) {
      setFeedbackMsg(`Failed to capture baseline: ${e.message || 'Error'}`);
    } finally {
      setCapturingBaseline(null);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.calibrateZones(editingZones);
      onRefreshZones();
      onClose();
    } catch (e) {
      console.error('Failed to save calibration:', e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-4xl overflow-hidden shadow-2xl space-y-5 p-6 flex flex-col max-h-[95vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Live Camera Zone Calibration & Baseline Reference</h3>
              <p className="text-xs text-slate-400">
                Calibrate zone boundaries against the live mobile feed and capture fresh full-shelf baseline images.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all">
            <X className="w-5 h-5" />
          </button>
        </div>

        {feedbackMsg && (
          <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs flex items-center justify-between shadow-lg">
            <span>{feedbackMsg}</span>
            <button onClick={() => setFeedbackMsg(null)} className="text-emerald-400 hover:text-white"><X className="w-4 h-4" /></button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 overflow-hidden flex-1">
          {/* Left: Live Frame Snapshot View */}
          <div className="lg:col-span-2 space-y-2 flex flex-col">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Camera className="w-3.5 h-3.5 text-cyan-400" /> <span>Current Live Frame</span>
              </span>
              <button 
                onClick={fetchLiveSnapshot} 
                className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-[10px] text-cyan-300 rounded border border-slate-700 flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" /> Refresh Frame
              </button>
            </div>

            <div className="relative aspect-video bg-slate-950 rounded-2xl overflow-hidden border border-slate-800 flex items-center justify-center">
              {liveSnapshot ? (
                <img src={liveSnapshot} alt="Live frame calibration" className="w-full h-full object-contain" />
              ) : (
                <div className="text-center p-4 text-xs text-slate-500 font-mono">
                  Loading live camera snapshot...
                </div>
              )}
            </div>

            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <strong className="text-slate-200 block">Baseline Calibration Workflow:</strong>
              <p>1. Point camera at shelf when 100% full.</p>
              <p>2. Click <strong className="text-cyan-300">"Capture Baseline"</strong> on each shelf zone below.</p>
              <p>3. Live inference computes SSIM differencing directly against that reference image.</p>
            </div>
          </div>

          {/* Right: Zone List & Baseline Capture Controls */}
          <div className="lg:col-span-3 space-y-3 overflow-y-auto pr-1">
            {editingZones.map((z, idx) => (
              <div key={z.zone_id} className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/80 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <span className="text-[10px] font-mono text-cyan-400 uppercase font-bold">{z.zone_id}</span>
                    <input
                      type="text"
                      value={z.label}
                      onChange={(e) => handleUpdateLabel(idx, e.target.value)}
                      className="w-full mt-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs font-semibold text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="w-32">
                    <label className="text-[10px] font-semibold text-slate-400 uppercase">Type</label>
                    <select
                      value={z.zone_type}
                      onChange={(e) => handleUpdateType(idx, e.target.value)}
                      className="w-full mt-1 px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500"
                    >
                      <option value="shelf">shelf</option>
                      <option value="queue_zone">queue_zone</option>
                      <option value="entrance">entrance</option>
                      <option value="aisle">aisle</option>
                      <option value="staff">staff</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-[10px] font-semibold text-slate-400 uppercase">Expected Capacity (Units)</label>
                    <input
                      type="number"
                      value={z.expected_capacity}
                      onChange={(e) => handleUpdateCapacity(idx, parseInt(e.target.value) || 1)}
                      className="w-full mt-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  {/* Baseline Capture Action for Shelf Zones */}
                  {z.zone_type === 'shelf' && (
                    <div>
                      <label className="text-[10px] font-semibold text-slate-400 uppercase">Baseline Reference</label>
                      <button
                        type="button"
                        onClick={() => handleCaptureBaseline(z.zone_id)}
                        disabled={capturingBaseline === z.zone_id}
                        className="w-full mt-1 px-3 py-1.5 bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 border border-cyan-500/40 rounded-lg text-xs font-bold flex items-center justify-center space-x-1.5 transition-all"
                      >
                        <Camera className="w-3.5 h-3.5 text-cyan-400" />
                        <span>{capturingBaseline === z.zone_id ? 'Capturing...' : 'Capture Full-Shelf Baseline'}</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Queue Axis Info */}
                {z.zone_type === 'queue_zone' && (
                  <div className="p-2.5 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-xs flex items-center justify-between">
                    <div className="flex items-center space-x-1.5 text-cyan-300 font-bold text-[11px]">
                      <Compass className="w-3.5 h-3.5" />
                      <span>Queue Axis: (0.28, 0.86) → (0.70, 0.86)</span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">Counter Vector</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-cyan-600/20 flex items-center space-x-1.5"
          >
            <Check className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Zone Calibration'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
