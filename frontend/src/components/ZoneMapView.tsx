import React, { useState } from 'react';
import { 
  Layers, 
  Video, 
  Settings2, 
  Maximize2, 
  Radio, 
  UserCheck,
  AlertCircle
} from 'lucide-react';
import { Zone, ZoneStatus } from '../types';

interface ZoneMapViewProps {
  zones: Zone[];
  zoneStatuses: ZoneStatus[];
  onOpenCalibration: () => void;
}

export const ZoneMapView: React.FC<ZoneMapViewProps> = ({
  zones,
  zoneStatuses,
  onOpenCalibration
}) => {
  const [showLiveStream, setShowLiveStream] = useState(true);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  const statusMap = new Map(zoneStatuses.map(zs => [zs.zone_id, zs]));

  return (
    <div className="space-y-6">
      {/* Header controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-cyan-400" />
            <span>2D Store Zone Map & Live Computer Vision Stream</span>
          </h2>
          <p className="text-xs text-slate-400">
            Real-time visual grounding of calibrated shelf zones, shopper tracks, and stock status.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowLiveStream(!showLiveStream)}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-bold border transition-all ${
              showLiveStream
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 shadow-sm shadow-cyan-500/20'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            <Video className="w-4 h-4" />
            <span>{showLiveStream ? 'Hide CV Video Feed' : 'Show CV Video Feed'}</span>
          </button>

          <button
            onClick={onOpenCalibration}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all"
          >
            <Settings2 className="w-4 h-4 text-slate-400" />
            <span>Calibrate Zones</span>
          </button>
        </div>
      </div>

      {/* Main Viewport Container */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Interactive Map & Live CV Stream */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative">
          <div className="relative w-full aspect-video bg-slate-950 flex items-center justify-center">
            {showLiveStream ? (
              <img 
                src="/video/feed" 
                alt="RetailIQ Edge Inference Stream" 
                className="w-full h-full object-contain"
                onError={(e) => {
                  // Fallback if backend stream restarts
                  (e.target as HTMLImageElement).src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><rect width="100%" height="100%" fill="%23090d16"/><text x="50%" y="50%" fill="%230ea5e9" text-anchor="middle" font-family="sans-serif">Connecting to Edge MJPEG Feed...</text></svg>';
                }}
              />
            ) : (
              /* 2D Schematic Plan */
              <div className="relative w-full h-full p-8 flex flex-col justify-between bg-gradient-to-b from-slate-900 to-slate-950">
                <div className="grid grid-cols-1 gap-4">
                  {zones.map((zone) => {
                    const status = statusMap.get(zone.zone_id);
                    const occPct = Math.round((status?.occupancy_score ?? 1.0) * 100);
                    let borderColor = 'border-emerald-500/60 bg-emerald-950/20';
                    if (occPct < 30) borderColor = 'border-rose-500/80 bg-rose-950/30';
                    else if (occPct < 60) borderColor = 'border-amber-500/80 bg-amber-950/30';

                    return (
                      <div 
                        key={zone.zone_id}
                        onClick={() => setSelectedZoneId(zone.zone_id)}
                        className={`p-4 rounded-xl border-2 ${borderColor} cursor-pointer transition-all hover:scale-[1.01]`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-xs font-mono text-cyan-400">{zone.zone_id}</span>
                            <h4 className="text-sm font-bold text-white">{zone.label}</h4>
                          </div>
                          {zone.zone_type === 'shelf' && (
                            <div className="text-right">
                              <span className="text-base font-extrabold text-white font-mono">{occPct}%</span>
                              <p className="text-[10px] text-slate-400">Occupancy</p>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Live Indicator Overlay */}
            <div className="absolute top-4 left-4 flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/80 backdrop-blur-md border border-slate-700/80 text-xs font-mono text-cyan-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>LIVE EDGE CV PIPELINE</span>
            </div>
          </div>
        </div>

        {/* Right Col: Zone Inspector Details */}
        <div className="space-y-4">
          <h3 className="text-base font-bold text-white">Zone Calibration Details</h3>

          <div className="space-y-3">
            {zones.map((zone) => {
              const status = statusMap.get(zone.zone_id);
              const occPct = Math.round((status?.occupancy_score ?? 1.0) * 100);
              
              return (
                <div 
                  key={zone.zone_id}
                  className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 hover:border-slate-700 transition-all"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                          {zone.zone_type}
                        </span>
                        <span className="text-xs font-mono text-slate-400">{zone.zone_id}</span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-100 mt-1">{zone.label}</h4>
                    </div>

                    {zone.zone_type === 'shelf' ? (
                      <span className={`px-2 py-1 text-xs font-mono font-bold rounded ${
                        occPct >= 60 ? 'bg-emerald-500/20 text-emerald-300' : (occPct >= 30 ? 'bg-amber-500/20 text-amber-300' : 'bg-rose-500/20 text-rose-300')
                      }`}>
                        {occPct}%
                      </span>
                    ) : zone.zone_type === 'queue_zone' ? (
                      <span className="px-2 py-1 text-xs font-mono font-bold rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                        Queue Active
                      </span>
                    ) : null}
                  </div>

                  <div className="text-[11px] text-slate-400 grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80">
                    <div>Capacity: <strong className="text-slate-200">{zone.expected_capacity} units</strong></div>
                    <div>
                      {zone.zone_type === 'queue_zone' ? (
                        <span>Axis: <strong className="text-cyan-400 font-mono">Calibrated Vector</strong></span>
                      ) : (
                        <span>Target SKU: <strong className="text-cyan-400">{zone.target_sku_id || 'N/A'}</strong></span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
