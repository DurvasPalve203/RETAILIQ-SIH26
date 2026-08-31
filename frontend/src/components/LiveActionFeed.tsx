import React, { useState } from 'react';
import { 
  AlertTriangle, 
  Clock, 
  CheckCircle2, 
  Flame, 
  ArrowRight,
  ShieldCheck, 
  RefreshCw, 
  EyeOff, 
  Activity,
  Users,
  Package,
  BellRing,
  Check,
  Zap,
  Camera,
  Video,
  Filter,
  SlidersHorizontal,
  Smartphone
} from 'lucide-react';
import { LiveAlert, ZoneStatus, QueueZoneState, QueuePrediction, HardwareStatus } from '../types';
import { api } from '../services/api';
import { QueueIntelligenceCard } from './QueueIntelligenceCard';
import { HardwareAlertHUD } from './HardwareAlertHUD';

interface LiveActionFeedProps {
  alerts: LiveAlert[];
  zoneStatuses: ZoneStatus[];
  queueStates?: Record<string, QueueZoneState>;
  queuePredictions?: QueuePrediction[];
  hardwareStatus?: HardwareStatus;
  isOccluded: boolean;
  isLowLight: boolean;
  isSynthetic?: boolean;
  footfallToday: number;
  onRestock: (zoneId: string) => void;
  onRefreshData?: () => void;
  onOpenPrivacyModal?: () => void;
  onOpenSourceModal?: () => void;
}

export const LiveActionFeed: React.FC<LiveActionFeedProps> = ({
  alerts,
  zoneStatuses,
  queueStates,
  queuePredictions,
  hardwareStatus,
  isOccluded,
  isLowLight,
  isSynthetic = false,
  footfallToday,
  onRestock,
  onRefreshData,
  onOpenPrivacyModal,
  onOpenSourceModal
}) => {
  const [filterType, setFilterType] = useState<'all' | 'critical' | 'queue' | 'shelf'>('all');
  const [showLiveStreamTile, setShowLiveStreamTile] = useState<boolean>(true);

  const getSeverityBadge = (severity: string, state: string) => {
    const s = severity.toUpperCase();
    if (state === 'ESCALATED') {
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-rose-600 text-white shadow-md shadow-rose-600/30 flex items-center gap-1 animate-pulse">
          <Flame className="w-3.5 h-3.5" /> ESCALATED TO CRITICAL (SMS DISPATCHED)
        </span>
      );
    }
    switch (s) {
      case 'CRITICAL':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 flex items-center gap-1">
            <Flame className="w-3.5 h-3.5 text-rose-400" /> CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> HIGH PRIORITY
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30">
            LOW
          </span>
        );
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    try {
      await api.acknowledgeAlert(alertId, 'staff_dashboard');
      if (onRefreshData) onRefreshData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleResolve = async (alertId: string, zoneId: string) => {
    try {
      await api.resolveAlert(alertId, 'manual_staff_restock');
      onRestock(zoneId);
      if (onRefreshData) onRefreshData();
    } catch (e) {
      console.error(e);
    }
  };

  // Filter alerts
  const filteredAlerts = alerts.filter(a => {
    if (filterType === 'critical') return a.severity.toUpperCase() === 'CRITICAL' || a.severity.toUpperCase() === 'HIGH';
    if (filterType === 'queue') return a.source_module === 'queue' || a.type.includes('queue');
    if (filterType === 'shelf') return a.source_module === 'shelf' || a.type.includes('stock');
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Occlusion / Environmental Alert Banner */}
      {isOccluded && (
        <div className="p-4 rounded-2xl bg-amber-950/60 border border-amber-500/40 text-amber-200 flex items-start space-x-3 shadow-xl animate-pulse">
          <EyeOff className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-bold tracking-tight">Camera Occlusion Active — Alert Storm Protection</h4>
            <p className="text-xs text-amber-300/80 mt-0.5">
              Camera lens obstructed. Shelf gap alerts are temporarily suppressed to prevent false stock-out notifications.
            </p>
          </div>
        </div>
      )}

      {isLowLight && !isOccluded && (
        <div className="p-3 rounded-xl bg-slate-800/90 border border-slate-700 text-slate-300 flex items-center space-x-2 text-xs">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span>Low ambient illumination detected — automatic CLAHE histogram normalization engaged.</span>
        </div>
      )}

      {/* Live Video Monitor Banner & Quick Control */}
      {showLiveStreamTile && (
        <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
          <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <Camera className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-white">Live Edge Camera Video Stream & Detection HUD</h3>
                  <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full uppercase font-mono ${
                    !isSynthetic ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/50' : 'bg-amber-950 text-amber-300 border border-amber-500/50'
                  }`}>
                    {!isSynthetic ? 'LIVE MOBILE CAMERA' : 'SIMULATION MODE'}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Real-time face-blurred overlay, shelf occupancy bounding boxes, and queue tracker.
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={onOpenSourceModal}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all"
              >
                <Smartphone className="w-3.5 h-3.5 text-cyan-400" />
                <span>Switch Camera IP</span>
              </button>

              <button
                onClick={onOpenPrivacyModal}
                className="px-3 py-1.5 bg-emerald-950/50 hover:bg-emerald-900/50 text-emerald-300 border border-emerald-500/30 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Split-Screen Debug</span>
              </button>

              <button
                onClick={() => setShowLiveStreamTile(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 text-xs"
                title="Hide live monitor tile"
              >
                ✕
              </button>
            </div>
          </div>

          <div className="relative w-full aspect-video max-h-[460px] bg-slate-950 flex items-center justify-center">
            <img 
              src="/video/feed" 
              alt="RetailIQ Live Edge Inference Stream" 
              className="w-full h-full object-contain"
              onError={(e) => {
                (e.target as HTMLImageElement).src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><rect width="100%" height="100%" fill="%23090d16"/><text x="50%" y="50%" fill="%230ea5e9" text-anchor="middle" font-family="sans-serif">Connecting to Edge Camera Feed...</text></svg>';
              }}
            />
          </div>
        </div>
      )}

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <p className="text-xs text-slate-400 uppercase font-semibold tracking-wider">Active Floor Alerts</p>
            <p className="text-2xl font-extrabold text-white mt-1">{alerts.length}</p>
          </div>
          <div className={`p-3 rounded-xl ${alerts.length > 0 ? 'bg-rose-500/10 text-rose-400 ring-1 ring-rose-500/20' : 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20'}`}>
            {alerts.length > 0 ? <Flame className="w-6 h-6" /> : <CheckCircle2 className="w-6 h-6" />}
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <p className="text-xs text-slate-400 uppercase font-semibold tracking-wider">Checkout Wait ETA</p>
            <p className="text-2xl font-extrabold text-cyan-400 mt-1">
              {queuePredictions && queuePredictions[0] ? queuePredictions[0].wait_minutes_formatted : '0s'}
            </p>
          </div>
          <div className="p-3 rounded-xl bg-cyan-500/10 text-cyan-400 ring-1 ring-cyan-500/20">
            <Users className="w-6 h-6" />
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex items-center justify-between shadow-lg">
          <div>
            <p className="text-xs text-slate-400 uppercase font-semibold tracking-wider">Today's Footfall</p>
            <p className="text-2xl font-extrabold text-slate-100 mt-1">{footfallToday} shoppers</p>
          </div>
          <div className="p-3 rounded-xl bg-slate-800 text-slate-300 ring-1 ring-slate-700">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        <div 
          onClick={onOpenPrivacyModal}
          className="bg-slate-900/80 border border-slate-800 hover:border-emerald-500/50 rounded-2xl p-4 flex items-center justify-between shadow-lg cursor-pointer transition-all group"
        >
          <div>
            <p className="text-xs text-slate-400 uppercase font-semibold tracking-wider group-hover:text-emerald-300 transition-colors">Privacy Pipeline</p>
            <p className="text-xl font-extrabold text-emerald-400 mt-1 flex items-center gap-1">
              Face Redacted <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </p>
          </div>
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Real-Time Queue Intelligence Visualizer */}
      <QueueIntelligenceCard
        queueStates={queueStates}
        queuePredictions={queuePredictions}
        onTriggerAction={onRefreshData}
      />

      {/* Main Grid: Priority Floor Tasks & Zone State */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Unified Priority Action Feed */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Prioritized Floor Action Feed</span>
              <span className="text-xs font-normal text-slate-400">({filteredAlerts.length} ranked tasks)</span>
            </h2>
            
            {/* Filter Pills */}
            <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs">
              {(['all', 'critical', 'queue', 'shelf'] as const).map((ft) => (
                <button
                  key={ft}
                  onClick={() => setFilterType(ft)}
                  className={`px-2.5 py-1 rounded-lg font-semibold uppercase text-[10px] tracking-wider transition-all ${
                    filterType === ft
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {ft}
                </button>
              ))}
            </div>
          </div>

          {filteredAlerts.length === 0 ? (
            <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 mx-auto flex items-center justify-center ring-1 ring-emerald-500/20">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">Store Operating in Optimal State</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No active out-of-stock events matching the selected filter, and checkout queues are flowing within bounds.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredAlerts.map((alert) => {
                const isQueueAlert = alert.source_module === 'queue' || alert.type.includes('queue');
                const isAck = alert.state === 'ACKNOWLEDGED';
                const isEscalated = alert.state === 'ESCALATED';

                return (
                  <div 
                    key={alert.alert_id}
                    className={`p-4 rounded-2xl border transition-all duration-200 space-y-3 ${
                      isEscalated
                        ? 'bg-rose-950/40 border-rose-500 shadow-lg shadow-rose-950/30'
                        : alert.severity.toLowerCase() === 'critical' || alert.severity.toLowerCase() === 'high'
                        ? 'bg-rose-950/20 border-rose-500/40 hover:border-rose-500/60'
                        : alert.severity.toLowerCase() === 'medium'
                        ? 'bg-amber-950/20 border-amber-500/40 hover:border-amber-500/60'
                        : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div className="space-y-1.5 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          {getSeverityBadge(alert.severity, alert.state)}
                          
                          {isQueueAlert ? (
                            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center gap-1">
                              <Users className="w-3 h-3" /> Queue Delay
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                              <Package className="w-3 h-3" /> Shelf Depletion
                            </span>
                          )}

                          <span className="text-xs font-mono text-slate-400">
                            State: <strong className={isAck ? 'text-amber-300' : (isEscalated ? 'text-rose-400' : 'text-cyan-300')}>{alert.state}</strong>
                          </span>
                        </div>

                        <h3 className="text-base font-bold text-slate-100">{alert.title}</h3>
                        <p className="text-xs text-slate-300">{alert.message}</p>
                      </div>

                      {/* State Action Buttons */}
                      <div className="flex items-center space-x-2 flex-shrink-0">
                        {alert.state === 'NEW' && (
                          <button
                            onClick={() => handleAcknowledge(alert.alert_id)}
                            className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 text-xs font-bold flex items-center space-x-1.5 transition-all"
                            title="Staff acknowledges alert, silences buzzer/LED, and initiates cooldown"
                          >
                            <BellRing className="w-3.5 h-3.5 text-amber-400" />
                            <span>Acknowledge</span>
                          </button>
                        )}

                        <button
                          onClick={() => handleResolve(alert.alert_id, alert.zone_id)}
                          className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-md shadow-cyan-600/20 flex items-center space-x-1.5 transition-all"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>{isQueueAlert ? 'Clear / Resolved' : 'Mark Restocked'}</span>
                        </button>
                      </div>
                    </div>

                    {/* Metadata Footer */}
                    <div className="pt-2.5 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-[11px] text-slate-400 gap-2">
                      <div className="flex items-center space-x-4">
                        <span>Zone: <strong className="text-slate-200">{alert.zone_id}</strong></span>
                        {alert.estimated_lost_sales > 0 && (
                          <span>Prevented Loss: <strong className="text-emerald-400">${alert.estimated_lost_sales.toFixed(2)}</strong></span>
                        )}
                        {alert.state === 'NEW' && alert.escalation_remaining_sec !== undefined && (
                          <span className="text-amber-400/90 font-mono">
                            Auto-escalates in: {Math.round(alert.escalation_remaining_sec)}s
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-cyan-400">Priority Score: {alert.priority_score.toFixed(1)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Col: Shelf Zone Live Gauges */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white">Shelf Zone Status</h2>
            <span className="text-xs text-slate-400">Occupancy %</span>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 space-y-4">
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

      {/* Multi-Channel Alert & Hardware Status HUD */}
      <HardwareAlertHUD
        hardwareStatus={hardwareStatus}
        onRefresh={onRefreshData}
      />
    </div>
  );
};
