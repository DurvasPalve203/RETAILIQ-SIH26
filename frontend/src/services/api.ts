import { Zone, SkuItem, DashboardSummaryData, MerchandisingInsightItem, ReviewQueueItem, SystemHealthData } from '../types';

const API_BASE = '/api';

export const api = {
  // Zones
  getZones: async (): Promise<Zone[]> => {
    const res = await fetch(`${API_BASE}/zones`);
    return res.json();
  },
  calibrateZones: async (zones: any[]): Promise<any> => {
    const res = await fetch(`${API_BASE}/zones/calibrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(zones)
    });
    return res.json();
  },

  // SKUs
  getSkus: async (): Promise<SkuItem[]> => {
    const res = await fetch(`${API_BASE}/sku/list`);
    return res.json();
  },
  onboardSku: async (payload: { sku_id: string; name: string; category: string; price: number; images_base64: string[] }): Promise<any> => {
    const res = await fetch(`${API_BASE}/sku/onboard`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  // Dashboard & Insights
  getSummary: async (): Promise<DashboardSummaryData> => {
    const res = await fetch(`${API_BASE}/dashboard/summary`);
    return res.json();
  },
  getInsights: async (): Promise<MerchandisingInsightItem[]> => {
    const res = await fetch(`${API_BASE}/dashboard/insights`);
    return res.json();
  },
  getRoiImpact: async (dollarRate?: number): Promise<any> => {
    const url = dollarRate ? `${API_BASE}/dashboard/roi?dollar_rate=${dollarRate}` : `${API_BASE}/dashboard/roi`;
    const res = await fetch(url);
    return res.json();
  },

  // Active Learning Review Queue
  getReviewQueue: async (): Promise<ReviewQueueItem[]> => {
    const res = await fetch(`${API_BASE}/review-queue`);
    return res.json();
  },
  submitReviewCorrection: async (itemId: string, payload: { corrected_sku_id: string; create_as_new_sku?: boolean; new_sku_name?: string; new_sku_category?: string }): Promise<any> => {
    const res = await fetch(`${API_BASE}/review-queue/${itemId}/correct`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  // System Health & Diagnostics
  getHealth: async (): Promise<SystemHealthData> => {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  // Simulation Controls
  controlSimulation: async (action: string, params: { zone_id?: string; count?: number; enabled?: boolean }): Promise<any> => {
    const res = await fetch(`${API_BASE}/video/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...params })
    });
    return res.json();
  }
};
