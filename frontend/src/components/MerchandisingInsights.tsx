import React, { useEffect, useState } from 'react';
import { 
  TrendingUp, 
  AlertOctagon, 
  Sparkles, 
  HelpCircle, 
  ShieldAlert,
  ArrowUpRight,
  Info
} from 'lucide-react';
import { MerchandisingInsightItem } from '../types';
import { api } from '../services/api';

export const MerchandisingInsights: React.FC = () => {
  const [insights, setInsights] = useState<MerchandisingInsightItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const data = await api.getInsights();
        setInsights(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchInsights();
  }, []);

  const getCardStyle = (classification: string) => {
    switch (classification) {
      case 'high_traffic_high_depletion':
        return {
          bg: 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300',
          badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
          icon: Sparkles
        };
      case 'high_traffic_low_depletion':
        return {
          bg: 'bg-amber-950/30 border-amber-500/40 text-amber-300',
          badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
          icon: HelpCircle
        };
      case 'low_traffic_high_depletion':
        return {
          bg: 'bg-rose-950/30 border-rose-500/40 text-rose-300',
          badge: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
          icon: ShieldAlert
        };
      default:
        return {
          bg: 'bg-slate-900/60 border-slate-800 text-slate-300',
          badge: 'bg-slate-800 text-slate-400 border-slate-700',
          icon: AlertOctagon
        };
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-cyan-400" />
          <span>Footfall × Shelf Depletion Correlation (2×2 Merchandising Matrix)</span>
        </h2>
        <p className="text-xs text-slate-400">
          Statistical correlation between customer dwell time and shelf velocity surfaced as plain-language retail decisions.
        </p>
      </div>

      {/* 2x2 Matrix Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Quadrant 1: High Traffic, Low Depletion */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-amber-500/30 space-y-3">
          <div className="flex items-center justify-between">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5" />
              <span>High Traffic • Low Depletion</span>
            </span>
            <span className="text-[11px] text-slate-400 font-medium">Placement Friction</span>
          </div>
          <p className="text-xs text-slate-300">
            Shoppers frequently dwell at this zone, but conversion into product pick-up is low.
          </p>
          <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-500/20 text-xs text-amber-200">
            <strong>Merchandiser Action:</strong> Review shelf tag clarity, product pricing competitiveness, or package aesthetics.
          </div>
        </div>

        {/* Quadrant 2: High Traffic, High Depletion */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-emerald-500/30 space-y-3">
          <div className="flex items-center justify-between">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>High Traffic • High Depletion</span>
            </span>
            <span className="text-[11px] text-emerald-400 font-medium">Healthy Fast-Mover</span>
          </div>
          <p className="text-xs text-slate-300">
            Optimal sales velocity. Product demand correlates directly with heavy customer dwell.
          </p>
          <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/20 text-xs text-emerald-200">
            <strong>Merchandiser Action:</strong> Protect floor safety stock and maintain active predictive replenishment rules.
          </div>
        </div>

        {/* Quadrant 3: Low Traffic, Low Depletion */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1.5">
              <AlertOctagon className="w-3.5 h-3.5 text-slate-400" />
              <span>Low Traffic • Low Depletion</span>
            </span>
            <span className="text-[11px] text-slate-400 font-medium">Dead Stock Candidate</span>
          </div>
          <p className="text-xs text-slate-300">
            Low customer engagement and slow shelf inventory turn.
          </p>
          <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs text-slate-300">
            <strong>Merchandiser Action:</strong> Consider repositioning to primary aisle eye-level or promotional end-cap bundling.
          </div>
        </div>

        {/* Quadrant 4: Low Traffic, High Depletion */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-rose-500/30 space-y-3">
          <div className="flex items-center justify-between">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-300 border border-rose-500/30 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Low Traffic • High Depletion</span>
            </span>
            <span className="text-[11px] text-rose-400 font-medium">Investigate Shrink</span>
          </div>
          <p className="text-xs text-slate-300">
            Inventory depletion occurred without normal tracked customer footfall or dwell duration.
          </p>
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/20 text-xs text-rose-200">
            <strong>Merchandiser Action:</strong> Flag for store manager loss-prevention audit, unlogged restock movement, or shrinkage investigation.
          </div>
        </div>
      </div>

      {/* Zone Level Classification Cards */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-white">Current Zone Classifications</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {insights.map((item) => {
            const style = getCardStyle(item.classification);
            const Icon = style.icon;

            return (
              <div key={item.zone_id} className={`p-4 rounded-xl border ${style.bg} space-y-3 shadow-lg`}>
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono text-slate-400">{item.zone_id}</span>
                    <h4 className="text-sm font-bold text-white">{item.label}</h4>
                  </div>
                  <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${style.badge}`}>
                    {item.tag}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs text-slate-300 py-2 border-y border-slate-800/80">
                  <div>Footfall: <strong className="text-white">{item.footfall_count} visits</strong></div>
                  <div>Avg Dwell: <strong className="text-white">{item.avg_dwell_seconds}s</strong></div>
                </div>

                <div className="text-xs space-y-1">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase">Recommendation</span>
                  <p className="text-slate-200 text-[11px] leading-relaxed">{item.action_recommendation}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
