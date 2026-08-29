import React, { useState } from 'react';
import { X, Check, Plus, Trash2, Edit3, Compass, Users } from 'lucide-react';
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
  const [saving, setSaving] = useState(false);

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
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-3xl overflow-hidden shadow-2xl space-y-6 p-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-lg font-bold text-white">Zone Calibration Setup</h3>
            <p className="text-xs text-slate-400">Configure shelf zones, queue zones, target SKUs, and capacity baselines.</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Zone List Editor */}
        <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
          {editingZones.map((z, idx) => (
            <div key={z.zone_id} className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/80 space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-semibold text-slate-400 uppercase">Zone Label</label>
                  <input
                    type="text"
                    value={z.label}
                    onChange={(e) => handleUpdateLabel(idx, e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs font-semibold text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase">Zone Type</label>
                  <select
                    value={z.zone_type}
                    onChange={(e) => handleUpdateType(idx, e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs font-mono text-cyan-400 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="shelf">shelf</option>
                    <option value="queue_zone">queue_zone</option>
                    <option value="entrance">entrance</option>
                    <option value="aisle">aisle</option>
                    <option value="staff">staff</option>
                  </select>
                </div>
              </div>

              {/* Queue Axis configuration if queue_zone */}
              {z.zone_type === 'queue_zone' && (
                <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-500/30 text-xs space-y-2">
                  <div className="flex items-center space-x-1.5 text-cyan-300 font-bold">
                    <Compass className="w-3.5 h-3.5" />
                    <span>Queue Axis Vector (Back of line → Checkout Counter)</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300">
                    <div>
                      <span>Queue-Start (Back): </span>
                      <strong className="font-mono text-cyan-400">
                        {z.axis_start_xy ? `(${z.axis_start_xy.x.toFixed(2)}, ${z.axis_start_xy.y.toFixed(2)})` : '(0.28, 0.86)'}
                      </strong>
                    </div>
                    <div>
                      <span>Counter-End (Billing): </span>
                      <strong className="font-mono text-cyan-400">
                        {z.axis_end_xy ? `(${z.axis_end_xy.x.toFixed(2)}, ${z.axis_end_xy.y.toFixed(2)})` : '(0.70, 0.86)'}
                      </strong>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase">Capacity (Units)</label>
                  <input
                    type="number"
                    value={z.expected_capacity}
                    onChange={(e) => handleUpdateCapacity(idx, parseInt(e.target.value) || 1)}
                    className="w-full mt-1 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 uppercase">Target SKU</label>
                  <div className="mt-1 px-3 py-2 bg-slate-900/60 border border-slate-800 rounded-lg text-xs font-mono text-slate-300">
                    {z.target_sku_id || 'None'}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-cyan-600/20 flex items-center space-x-1.5"
          >
            <Check className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Calibration'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
