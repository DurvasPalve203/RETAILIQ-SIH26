import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  HelpCircle, 
  Sparkles, 
  RefreshCw, 
  Tag, 
  ArrowRight,
  ShieldCheck
} from 'lucide-react';
import { ReviewQueueItem, SkuItem } from '../types';
import { api } from '../services/api';

export const ReviewQueue: React.FC = () => {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [skus, setSkus] = useState<SkuItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSkuMap, setSelectedSkuMap] = useState<Record<string, string>>({});
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [queueData, skuData] = await Promise.all([
        api.getReviewQueue(),
        api.getSkus()
      ]);
      setItems(queueData);
      setSkus(skuData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCorrect = async (itemId: string, skuId: string) => {
    try {
      await api.submitReviewCorrection(itemId, {
        corrected_sku_id: skuId,
        create_as_new_sku: false
      });
      setFeedbackMsg(`Item updated to ${skuId} — embedding vector refined online!`);
      setItems(items.filter(i => i.item_id !== itemId));
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateNewSku = async (itemId: string) => {
    try {
      await api.submitReviewCorrection(itemId, {
        corrected_sku_id: `SKU-AUTO-${Date.now() % 10000}`,
        create_as_new_sku: true,
        new_sku_name: 'Verified New In-Store Product',
        new_sku_category: 'General'
      });
      setFeedbackMsg('New SKU created and added to gallery immediately!');
      setItems(items.filter(i => i.item_id !== itemId));
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-cyan-400" />
          <span>Active Learning / Human-in-the-Loop Triage</span>
        </h2>
        <p className="text-xs text-slate-400">
          Confidence-based triage. Detections falling below the cosine similarity threshold are routed here for rapid one-tap staff verification.
        </p>
      </div>

      {feedbackMsg && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-200 text-xs flex items-center space-x-3 shadow-lg">
          <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <span>{feedbackMsg}</span>
        </div>
      )}

      {items.length === 0 ? (
        <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-400 mx-auto flex items-center justify-center ring-1 ring-emerald-500/20">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-white">Review Queue is Clear</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            All detected product crops meet the required confidence threshold. Low-confidence candidates will appear here for staff verification.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map((item) => (
            <div 
              key={item.item_id}
              className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl space-y-4 p-5 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/40">
                    Confidence: {Math.round(item.confidence * 100)}%
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">{item.item_id}</span>
                </div>

                {/* Cropped Image View */}
                <div className="w-full h-40 bg-slate-950 rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center">
                  <img src={item.crop_ref} alt="Low confidence crop" className="h-full object-contain" />
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Predicted SKU Match:</span>
                  <p className="text-xs font-bold text-slate-200">
                    {item.predicted_sku_id || 'Unknown / Unrecognized Product'}
                  </p>
                </div>
              </div>

              {/* Triage Actions */}
              <div className="space-y-2 pt-3 border-t border-slate-800">
                <div className="space-y-1">
                  <label className="text-[10px] text-slate-400 uppercase font-semibold">Assign Correct SKU</label>
                  <select
                    value={selectedSkuMap[item.item_id] || item.predicted_sku_id || (skus[0]?.sku_id || '')}
                    onChange={(e) => setSelectedSkuMap({ ...selectedSkuMap, [item.item_id]: e.target.value })}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-cyan-500"
                  >
                    {skus.map((s) => (
                      <option key={s.sku_id} value={s.sku_id}>{s.name} ({s.sku_id})</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    onClick={() => handleCorrect(item.item_id, selectedSkuMap[item.item_id] || item.predicted_sku_id || skus[0]?.sku_id)}
                    className="py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold shadow-md flex items-center justify-center space-x-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Confirm Match</span>
                  </button>

                  <button
                    onClick={() => handleCreateNewSku(item.item_id)}
                    className="py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center justify-center space-x-1 border border-slate-700"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Add As New</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
