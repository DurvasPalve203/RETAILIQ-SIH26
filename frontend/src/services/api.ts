import { 
  Zone, 
  SkuItem, 
  DashboardSummaryData, 
  MerchandisingInsightItem, 
  ReviewQueueItem, 
  SystemHealthData,
  LiveAlert,
  HardwareStatus,
  PrivacyStats,
  QueuePrediction,
  CameraStatus
} from '../types';

const API_BASE = '/api';

export const api = {
  // Zones & Calibration
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
  getLiveSnapshot: async (): Promise<{ image_base64: string }> => {
    const res = await fetch(`${API_BASE}/zones/live-snapshot`);
    return res.json();
  },
  captureZoneBaseline: async (zoneId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/zones/capture-baseline/${zoneId}`, {
      method: 'POST'
    });
    return res.json();
  },

  // Camera & Video Ingestion
  getCameraStatus: async (): Promise<CameraStatus> => {
    const res = await fetch(`${API_BASE}/video/status`);
    return res.json();
  },
  setCameraSource: async (source: string, rotation_deg: number = 0): Promise<any> => {
    const res = await fetch(`${API_BASE}/video/source`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source, rotation_deg })
    });
    return res.json();
  },
  togglePrivacyBlur: async (enabled?: boolean): Promise<any> => {
    const res = await fetch(`${API_BASE}/video/privacy-toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled })
    });
    return res.json();
  },
  getVideoSnapshot: async (): Promise<{ image_base64: string }> => {
    const res = await fetch(`${API_BASE}/video/snapshot`);
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

  // Multi-Level Alert Manager
  getAlerts: async (): Promise<LiveAlert[]> => {
    const res = await fetch(`${API_BASE}/alerts`);
    return res.json();
  },
  acknowledgeAlert: async (alertId: string, acknowledgedBy: string = 'staff_tablet'): Promise<any> => {
    const res = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acknowledged_by: acknowledgedBy })
    });
    return res.json();
  },
  resolveAlert: async (alertId: string, reason: string = 'restock_cleared'): Promise<any> => {
    const res = await fetch(`${API_BASE}/alerts/${alertId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolved_by: 'staff_tablet', reason })
    });
    return res.json();
  },
  getHardwareStatus: async (): Promise<HardwareStatus> => {
    const res = await fetch(`${API_BASE}/alerts/hardware/status`);
    return res.json();
  },
  testAlertChannel: async (channel: string, pattern_or_color: string = 'HIGH', test_message?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/alerts/test-channel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel, pattern_or_color, test_message })
    });
    return res.json();
  },

  // Queue Intelligence & Wait-Time Predictions
  getQueueState: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/queue/state`);
    return res.json();
  },
  getQueuePredictions: async (): Promise<QueuePrediction[]> => {
    const res = await fetch(`${API_BASE}/queue/predictions`);
    return res.json();
  },

  // Privacy Pipeline
  getPrivacyStats: async (): Promise<PrivacyStats> => {
    const res = await fetch(`${API_BASE}/video/privacy-stats`);
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
  controlSimulation: async (action: string, params: { zone_id?: string; count?: number; enabled?: boolean } = {}): Promise<any> => {
    const res = await fetch(`${API_BASE}/video/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...params })
    });
    return res.json();
  }
};
