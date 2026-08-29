import React from 'react';
import { 
  Users, 
  Clock, 
  TrendingUp, 
  Timer, 
  ArrowRight, 
  UserCheck, 
  CheckCircle2, 
  PlusCircle, 
  Zap,
  Activity,
  Compass
} from 'lucide-react';
import { QueueZoneState, QueuePrediction } from '../types';
import { api } from '../services/api';

interface QueueIntelligenceCardProps {
  queueStates?: Record<string, QueueZoneState>;
  queuePredictions?: QueuePrediction[];
  onTriggerAction?: () => void;
}

export const QueueIntelligenceCard: React.FC<QueueIntelligenceCardProps> = ({
  queueStates = {},
  queuePredictions = [],
  onTriggerAction
}) => {
  const activeZoneId = Object.keys(queueStates)[0] || 'zone-queue-01';
  const qstate = queueStates[activeZoneId];
  const qpred = queuePredictions.find(p => p.zone_id === activeZoneId) || queuePredictions[0];

  const queueLength = qstate ? qstate.queue_length : 3;
  const growthRate = qstate ? qstate.growth_rate : 0.0;
  const waitFormatted = qpred ? qpred.wait_minutes_formatted : '2m 15s';
  const avgSvcTime = qpred ? qpred.average_service_time_sec : 45.0;
  const confidencePct = qpred ? Math.round(qpred.confidence * 100) : 88;
  const inQueueTracks = qstate ? qstate.in_queue_tracks : [];
  const browsingTracks = qstate ? qstate.browsing_tracks : [];

  const handleAddShopper = async () => {
    try {
      await api.controlSimulation('add_queue');
      if (onTriggerAction) onTriggerAction();
    } catch (e) {
      console.error(e);
    }
  };

  const handleServeCustomer = async () => {
    try {
      await api.controlSimulation('serve_queue');
      if (onTriggerAction) onTriggerAction();
    } catch (e) {
      console.error(e);
    }
  };

  const handleQueueSurge = async () => {
    try {
      await api.controlSimulation('queue_surge');
      if (onTriggerAction) onTriggerAction();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-sm">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-bold text-white">Queue Intelligence & Wait Prediction</h3>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/60 uppercase font-mono">
                FR-Q01–Q06 Active
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Pose estimation + trajectory classifier tracking line formation and customer service ETAs.
            </p>
          </div>
        </div>

        {/* Quick Sim Controls */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleAddShopper}
            className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center space-x-1 transition-all"
            title="Simulate a customer joining the queue"
          >
            <PlusCircle className="w-3.5 h-3.5 text-cyan-400" />
            <span>+ Shopper</span>
          </button>
          <button
            onClick={handleServeCustomer}
            className="px-2.5 py-1.5 rounded-lg bg-emerald-950/40 hover:bg-emerald-950/70 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center space-x-1 transition-all"
            title="Simulate front checkout completion"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Serve Checkout</span>
          </button>
          <button
            onClick={handleQueueSurge}
            className="px-2.5 py-1.5 rounded-lg bg-amber-950/40 hover:bg-amber-950/70 text-amber-300 border border-amber-500/30 text-xs font-semibold flex items-center space-x-1 transition-all"
            title="Simulate sudden queue buildup"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>Surge</span>
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Queue Length */}
        <div className="p-3.5 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Queue Length</span>
          <div className="flex items-baseline space-x-2">
            <span className={`text-2xl font-extrabold font-mono ${queueLength >= 5 ? 'text-rose-400' : (queueLength >= 3 ? 'text-amber-400' : 'text-emerald-400')}`}>
              {queueLength}
            </span>
            <span className="text-xs text-slate-400">shoppers</span>
          </div>
          <p className="text-[10px] text-slate-400 font-mono">
            Growth: <strong className={growthRate > 0 ? 'text-amber-300' : 'text-emerald-300'}>{growthRate >= 0 ? `+${growthRate}` : growthRate}/min</strong>
          </p>
        </div>

        {/* Estimated Wait Time */}
        <div className="p-3.5 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Predicted Wait Time</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold text-cyan-400 font-mono">
              {waitFormatted}
            </span>
          </div>
          <div className="flex items-center space-x-1 text-[10px] text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
            <span>Time to be served</span>
          </div>
        </div>

        {/* Avg Service Duration */}
        <div className="p-3.5 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Avg Service Rate</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold text-slate-100 font-mono">
              {avgSvcTime.toFixed(0)}s
            </span>
            <span className="text-xs text-slate-400">/ customer</span>
          </div>
          <p className="text-[10px] text-slate-400">Empirically measured</p>
        </div>

        {/* Model Confidence */}
        <div className="p-3.5 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-1">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Model Confidence</span>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-extrabold text-emerald-400 font-mono">
              {confidencePct}%
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Tier 2 Hybrid</span>
          </div>
          <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-400 rounded-full" style={{ width: `${confidencePct}%` }} />
          </div>
        </div>
      </div>

      {/* Shopper Line Roster & Pose Classification */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-slate-200 flex items-center gap-1.5">
            <Compass className="w-3.5 h-3.5 text-cyan-400" />
            <span>Active Queue Roster & Pose Heading</span>
          </span>
          <span className="text-[11px] text-slate-400 font-mono">
            {inQueueTracks.length} in queue • {browsingTracks.length} browsing nearby
          </span>
        </div>

        {inQueueTracks.length === 0 ? (
          <div className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/40 text-center text-xs text-slate-400">
            No customers currently waiting in the checkout queue.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {inQueueTracks.map((t) => (
              <div 
                key={t.track_id}
                className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/70 space-y-1.5 hover:border-cyan-500/40 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1.5">
                    <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-300 font-mono text-[10px] font-bold flex items-center justify-center border border-cyan-500/30">
                      #{t.queue_position}
                    </span>
                    <span className="text-xs font-bold text-slate-200">Track #{t.track_id}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                    IN QUEUE
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-1 text-[10px] text-slate-400 pt-1 border-t border-slate-700/50">
                  <div>Axis Distance: <strong className="text-slate-200 font-mono">{(t.projection_distance * 100).toFixed(0)}%</strong></div>
                  <div>Heading: <strong className="text-cyan-300 font-mono">{t.facing_angle_deg.toFixed(0)}°</strong> (Counter)</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
