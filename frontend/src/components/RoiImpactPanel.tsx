import React, { useState, useEffect } from 'react';
import { 
  DollarSign, 
  Clock, 
  TrendingUp, 
  HelpCircle, 
  CheckCircle2, 
  Calculator,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';

export const RoiImpactPanel: React.FC = () => {
  const [salesRate, setSalesRate] = useState<number>(2.50);
  const [roiData, setRoiData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchRoi = async (rate: number) => {
    try {
      const data = await api.getRoiImpact(rate);
      setRoiData(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoi(salesRate);
  }, [salesRate]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-emerald-400" />
          <span>Business ROI & Lost-Sale Prevention Analytics</span>
        </h2>
        <p className="text-xs text-slate-400">
          Quantified financial impact derived from automated stock-out response time deltas.
        </p>
      </div>

      {/* Primary Financial Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-6 rounded-2xl bg-gradient-to-br from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-500/30 space-y-2 shadow-xl">
          <div className="flex items-center justify-between text-xs text-emerald-400 font-semibold uppercase tracking-wider">
            <span>Lost Sales Revenue Prevented</span>
            <DollarSign className="w-5 h-5" />
          </div>
          <p className="text-3xl font-extrabold text-white">
            ${roiData?.estimated_lost_sales_prevented?.toFixed(2) || '0.00'}
          </p>
          <p className="text-[11px] text-slate-400">
            Based on ${salesRate.toFixed(2)}/minute shelf sales rate
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2 shadow-xl">
          <div className="flex items-center justify-between text-xs text-cyan-400 font-semibold uppercase tracking-wider">
            <span>Out-Of-Stock Minutes Prevented</span>
            <Clock className="w-5 h-5" />
          </div>
          <p className="text-3xl font-extrabold text-cyan-300">
            {roiData?.prevented_minutes?.toFixed(1) || '0.0'} min
          </p>
          <p className="text-[11px] text-slate-400">
            Cumulative alert-to-replenishment reduction
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2 shadow-xl">
          <div className="flex items-center justify-between text-xs text-blue-400 font-semibold uppercase tracking-wider">
            <span>Automated Restock Cycles</span>
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <p className="text-3xl font-extrabold text-blue-300">
            {roiData?.historical_resolved_stockouts || 0} events
          </p>
          <p className="text-[11px] text-slate-400">
            Closed automatically via occupancy recovery
          </p>
        </div>
      </div>

      {/* Assumptions & Configurable Parameters Panel */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-5 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <Calculator className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">Transparent ROI Calculation Assumptions</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Real-Time Interactive Model</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span>Assumed Sales Loss Constant ($ / minute)</span>
              <span className="font-mono text-cyan-400 font-bold">${salesRate.toFixed(2)}/min</span>
            </label>
            <input
              type="range"
              min="0.50"
              max="10.00"
              step="0.25"
              value={salesRate}
              onChange={(e) => setSalesRate(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
            <p className="text-[11px] text-slate-400">
              Adjustable constant reflecting typical gross margin opportunity cost per out-of-stock shelf minute.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2 text-xs text-slate-300">
            <h4 className="font-bold text-white flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Methodology & Formula</span>
            </h4>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              $$\text{Loss Prevented} = \left(\text{Resolved Stockouts} \times 18.0\text{ min response delta}\right) \times \text{Sales Constant}$$
            </p>
            <p className="text-slate-500 text-[10px]">
              *Based on industry benchmark of 18-minute delta between unassisted physical store patrols vs real-time push alerting.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
