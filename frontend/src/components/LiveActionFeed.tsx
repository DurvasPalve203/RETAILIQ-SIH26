import React from 'react';
import { 
  AlertTriangle, 
  Clock, 
  CheckCircle2, 
  TrendingDown, 
  Flame, 
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  EyeOff,
  Activity
} from 'lucide-react';
import { LiveAlert, ZoneStatus } from '../types';
import { api } from '../services/api';

interface LiveActionFeedProps {
  alerts: LiveAlert[];
  zoneStatuses: ZoneStatus[];
  isOccluded: boolean;
  isLowLight: boolean;
  footfallToday: number;
  onRestock: (zoneId: string) => void;
}

export const LiveActionFeed: React.FC<LiveActionFeedProps> = ({
  alerts,
  zoneStatuses,
  isOccluded,
  isLowLight,
  footfallToday,
  onRestock
}) => {
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'high':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1"><Flame className="w-3 h-3 text-rose-400" /> High Priority</span>;
      case 'medium':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1"><AlertTriangle className="w-3 h-3 text-amber-400" /> Medium</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30">Low</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Occlusion / Environmental Alert Banner */}
      {isOccluded && (
        <div className="p-4 rounded-xl bg-amber-950/60 border border-amber-500/40 text-amber-200 flex items-start space-x-3 shadow-lg shadow-amber-900/10">
          <EyeOff className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0 animate-bounce" />
          <div>
            <h4 className="text-sm font-bold tracking-tight">Camera Occlusion Active — Alert Storm Protection</h4>
            <p className="text-xs text-amber-300/80 mt-0.5">
              Someone is standing directly in front of the lens or the camera is obstructed. Shelf gap alerts are temporarily suppressed to prevent false stock-out notifications.
            </p>
          </div>
        </div>
      )}

      {isLowLight && !isOccluded && (
        <div className="p-3 rounded-lg bg-slate-800/90 border border-slate-700 text-slate-300 flex items-center space-x-2 text-xs">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span>Low ambient illumination detected — automatic CLAHE histogram normalization engaged.</span>
        </div>
      )}

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 uppercase font-semibold tracking-wider">Active Urgent Actions</p>
            <p className="text-2xl font-extrabold text-white mt-1">{alerts.length}</p>
          </div>
          <div className={`p-3 rounded-xl ${alerts.length > 0 ? 'bg-rose-500/10 text-rose-400 ring-1 ring-rose-500/20' : 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20'}`}>
            {alerts.length > 0 ? <Flame className="w-6 h-6" /> : <CheckCircle2 className="w-6 h-6" />}
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 uppercase font-semibold tracking-wider">Today's Footfall</p>
            <p className="text-2xl font-extrabold text-cyan-400 mt-1">{footfallToday} shoppers</p>
          </div>
          <div className="p-3 rounded-xl bg-cyan-500/10 text-cyan-400 ring-1 ring-cyan-500/20">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 uppercase font-semibold tracking-wider">Edge Inference Status</p>
            <p className="text-2xl font-extrabold text-emerald-400 mt-1">100% Offline</p>
          </div>
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Grid: Live Action Feed & Zone Shelf Gauges */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Primary Action Feed */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Prioritized Floor Tasks</span>
              <span className="text-xs font-normal text-slate-400">(Ranked by urgency × depletion rate)</span>
            </h2>
            <span className="text-xs text-slate-400 font-mono">Auto-refreshed via WebSocket</span>
          </div>

          {alerts.length === 0 ? (
            <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 mx-auto flex items-center justify-center ring-1 ring-emerald-500/20">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">All Shelves Optimally Stocked</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No active out-of-stock events or rapid depletion warnings. The local intelligence engine will automatically trigger priority tasks when an item depletes.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <div 
                  key={alert.alert_id}
                  className={`p-4 rounded-xl border transition-all duration-200 ${
                    alert.severity === 'high'
                      ? 'bg-rose-950/20 border-rose-500/30 hover:border-rose-500/50'
                      : alert.severity === 'medium'
                      ? 'bg-amber-950/20 border-amber-500/30 hover:border-amber-500/50'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        {getSeverityBadge(alert.severity)}
                        <span className="text-xs text-slate-400 font-mono">
                          {alert.type === 'immediate_stockout' ? 'Stock Depleted' : `ETA: ~${Math.round(alert.eta_minutes)}m to empty`}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-slate-100">{alert.title}</h3>
                      <p className="text-xs text-slate-300">{alert.message}</p>
                    </div>

                    <button
                      onClick={() => onRestock(alert.zone_id)}
                      className="px-3.5 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-md shadow-cyan-600/20 flex items-center space-x-1.5 transition-all flex-shrink-0 ml-4"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Mark Restocked</span>
                    </button>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                    <div className="flex items-center space-x-4">
                      <span>Zone: <strong className="text-slate-200">{alert.zone_id}</strong></span>
                      {alert.estimated_lost_sales > 0 && (
                        <span>Prevented Loss: <strong className="text-emerald-400">${alert.estimated_lost_sales.toFixed(2)}</strong></span>
                      )}
                    </div>
                    <span className="font-mono">Priority Score: {alert.priority_score.toFixed(1)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Col: Shelf Zone Live Gauges */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white">Zone Shelf State</h2>
            <span className="text-xs text-slate-400">Occupancy %</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-4">
            {zoneStatuses.filter(z => z.zone_type === 'shelf').map((z) => {
              const occPct = Math.round(z.occupancy_score * 100);
              let barColor = 'bg-emerald-500';
              let badgeColor = 'text-emerald-400 bg-emerald-500/10';
              
              if (occPct < 30) {
                barColor = 'bg-rose-500';
                badgeColor = 'text-rose-400 bg-rose-500/10';
              } else if (occPct < 60) {
                barColor = 'bg-amber-500';
                badgeColor = 'text-amber-400 bg-amber-500/10';
              }

              return (
                <div key={z.zone_id} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{z.label}</span>
                    <span className={`px-2 py-0.5 rounded font-mono font-bold ${badgeColor}`}>
                      {occPct}%
                    </span>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${barColor} transition-all duration-300`} 
                      style={{ width: `${Math.max(4, occPct)}%` }} 
                    />
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span>Items on shelf: <strong className="text-slate-300">{z.item_count}</strong></span>
                    {z.prediction ? (
                      <span className="text-amber-300 font-mono">
                        Depleting ({z.prediction.eta_minutes.toFixed(0)}m ETA)
                      </span>
                    ) : (
                      <span className="text-slate-400">Stable</span>
                    )}
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
