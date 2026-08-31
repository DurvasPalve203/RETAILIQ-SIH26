import React, { useState, useEffect } from 'react';
import { 
  PackagePlus, 
  Upload, 
  Camera, 
  CheckCircle2, 
  Sparkles, 
  Layers, 
  Trash2,
  Zap,
  Image as ImageIcon
} from 'lucide-react';
import { SkuItem } from '../types';
import { api } from '../services/api';

export const SkuOnboarding: React.FC = () => {
  const [skus, setSkus] = useState<SkuItem[]>([]);
  const [skuId, setSkuId] = useState('');
  const [name, setName] = useState('');
  const [category, setCategory] = useState('Dairy & Beverages');
  const [price, setPrice] = useState('4.49');
  const [sampleImages, setSampleImages] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchSkus = async () => {
    try {
      const list = await api.getSkus();
      setSkus(list);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchSkus();
  }, []);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    
    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (loadEvt) => {
        if (loadEvt.target?.result) {
          setSampleImages((prev) => [...prev, loadEvt.target!.result as string]);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const handleAddSyntheticSample = (color: string) => {
    // Generate synthetic canvas crop for rapid demo onboarding
    const canvas = document.createElement('canvas');
    canvas.width = 120;
    canvas.height = 160;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 120, 160);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(10, 40, 100, 40);
      ctx.fillStyle = '#1e293b';
      ctx.font = '12px sans-serif';
      ctx.fillText(skuId || 'NEW-SKU', 15, 65);
      setSampleImages((prev) => [...prev, canvas.toDataURL('image/jpeg')]);
    }
  };

  const handleSnapFromLiveCamera = async () => {
    try {
      const snap = await api.getVideoSnapshot();
      if (snap?.image_base64) {
        setSampleImages((prev) => [...prev, snap.image_base64]);
      }
    } catch (e) {
      console.error('Failed to snap from camera:', e);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!skuId || !name) return;

    setLoading(true);
    setSuccessMsg(null);

    try {
      await api.onboardSku({
        sku_id: skuId.trim().toUpperCase(),
        name: name.trim(),
        category,
        price: parseFloat(price) || 3.99,
        images_base64: sampleImages
      });

      setSuccessMsg(`SKU "${name}" successfully onboarded into edge gallery with ${Math.max(1, sampleImages.length)} few-shot embeddings!`);
      setSkuId('');
      setName('');
      setSampleImages([]);
      fetchSkus();
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <PackagePlus className="w-5 h-5 text-cyan-400" />
          <span>Few-Shot SKU Onboarding (Zero Model Retraining)</span>
        </h2>
        <p className="text-xs text-slate-400">
          Upload 5–10 sample product photos or snap live crops from the mobile camera feed. The feature encoder generates normalized embeddings instantly into SQLite.
        </p>
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-200 text-xs flex items-center space-x-3 shadow-lg shadow-emerald-950/20">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Onboarding Form */}
        <div className="lg:col-span-1 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <span>Register New Product</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase">SKU Identifier</label>
              <input
                type="text"
                required
                placeholder="e.g. SKU-OATMILK-06"
                value={skuId}
                onChange={(e) => setSkuId(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-cyan-500 uppercase"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-400 uppercase">Product Name</label>
              <input
                type="text"
                required
                placeholder="e.g. Silk Barista Oat Milk 32oz"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-semibold text-white focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase">Category</label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase">Unit Price ($)</label>
                <input
                  type="number"
                  step="0.01"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            {/* Sample Photo Capture / Upload */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <label className="text-[11px] font-semibold text-slate-400 uppercase flex items-center justify-between">
                <span>Sample Photos ({sampleImages.length})</span>
                <span className="text-[10px] text-cyan-400">5-10 recommended</span>
              </label>

              {/* Upload Drop Area & Live Snap */}
              <div className="grid grid-cols-2 gap-2">
                <div className="relative border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-3 text-center cursor-pointer transition-all">
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleImageUpload}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                  />
                  <Upload className="w-5 h-5 text-slate-400 mx-auto mb-0.5" />
                  <p className="text-[11px] text-slate-300 font-medium">Upload File</p>
                </div>

                <button
                  type="button"
                  onClick={handleSnapFromLiveCamera}
                  className="border-2 border-dashed border-cyan-800/60 hover:border-cyan-500 bg-cyan-950/20 hover:bg-cyan-950/40 rounded-xl p-3 text-center transition-all flex flex-col items-center justify-center"
                >
                  <Camera className="w-5 h-5 text-cyan-400 mx-auto mb-0.5" />
                  <p className="text-[11px] text-cyan-300 font-medium">Snap Live Frame</p>
                </button>
              </div>

              {/* Quick sample generators for demo */}
              <div className="flex items-center space-x-1.5 pt-1">
                <span className="text-[10px] text-slate-400">Quick Test Crops:</span>
                <button
                  type="button"
                  onClick={() => handleAddSyntheticSample('#2563eb')}
                  className="px-2 py-0.5 text-[10px] bg-blue-600/30 text-blue-300 rounded border border-blue-500/30 hover:bg-blue-600/50"
                >
                  + Blue Box
                </button>
                <button
                  type="button"
                  onClick={() => handleAddSyntheticSample('#16a34a')}
                  className="px-2 py-0.5 text-[10px] bg-emerald-600/30 text-emerald-300 rounded border border-emerald-500/30 hover:bg-emerald-600/50"
                >
                  + Green Box
                </button>
              </div>

              {/* Image Previews */}
              {sampleImages.length > 0 && (
                <div className="grid grid-cols-4 gap-2 pt-2">
                  {sampleImages.map((src, idx) => (
                    <div key={idx} className="relative aspect-square rounded-lg overflow-hidden border border-slate-700">
                      <img src={src} alt="Crop sample" className="w-full h-full object-cover" />
                      <button
                        type="button"
                        onClick={() => setSampleImages(sampleImages.filter((_, i) => i !== idx))}
                        className="absolute top-1 right-1 p-0.5 rounded bg-black/70 text-rose-400 hover:text-white"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !skuId || !name}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-cyan-600/25 flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
            >
              <Zap className="w-4 h-4" />
              <span>{loading ? 'Generating Embeddings...' : 'Onboard SKU (Instant)'}</span>
            </button>
          </form>
        </div>

        {/* Gallery Browser */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>Active SKU Gallery in SQLite ({skus.length} SKUs)</span>
            </h3>
            <span className="text-xs text-slate-400">128-d L2 Normalized Embeddings</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {skus.map((sku) => (
              <div 
                key={sku.sku_id}
                className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 hover:border-slate-700 transition-all shadow-md"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                      {sku.sku_id}
                    </span>
                    <h4 className="text-sm font-bold text-white mt-1.5">{sku.name}</h4>
                    <p className="text-xs text-slate-400">{sku.category} • ${sku.price.toFixed(2)}</p>
                  </div>

                  <div className="text-right">
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Ready
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span>Samples: <strong className="text-slate-200">{sku.sample_count}</strong></span>
                  <span>Retrain Required: <strong className="text-emerald-400">NO</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
