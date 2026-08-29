export interface Point2D {
  x: number;
  y: number;
}

export interface Zone {
  zone_id: string;
  camera_id: string;
  polygon: Point2D[];
  zone_type: 'shelf' | 'entrance' | 'aisle' | 'staff';
  label: string;
  target_sku_id?: string;
  expected_capacity: number;
  created_at: number;
}

export interface SkuItem {
  sku_id: string;
  name: string;
  category: string;
  price: number;
  sample_count: number;
  thumbnail_path?: string;
  created_at: number;
  updated_at: number;
}

export interface LiveAlert {
  alert_id: string;
  zone_id: string;
  title: string;
  message: string;
  type: 'immediate_stockout' | 'predictive_stockout';
  severity: 'high' | 'medium' | 'low';
  eta_minutes: number;
  priority_score: number;
  ts: number;
  estimated_lost_sales: number;
}

export interface ZoneStatus {
  zone_id: string;
  label: string;
  zone_type: string;
  occupancy_score: number;
  status: 'normal' | 'depleted';
  severity: 'high' | 'medium' | 'low' | null;
  item_count: number;
  target_sku_id?: string;
  prediction?: {
    prediction_id: string;
    eta_minutes: number;
    confidence: number;
    depletion_rate_per_hour?: number;
  };
}

export interface LiveStatePayload {
  timestamp: number;
  fps: number;
  is_occluded: boolean;
  is_low_light: boolean;
  zone_statuses: ZoneStatus[];
  active_alerts: LiveAlert[];
  predictions: any[];
  footfall_today: number;
  active_tracks_count: number;
}

export interface DashboardSummaryData {
  total_active_stockouts: number;
  predicted_stockouts_next_hour: number;
  today_footfall_count: number;
  lost_sales_prevented_dollars: number;
  lost_sale_minutes_prevented: number;
  sales_loss_rate_constant: number;
  resolved_stockout_events_count: number;
}

export interface MerchandisingInsightItem {
  zone_id: string;
  label: string;
  target_sku_id?: string;
  footfall_count: number;
  avg_dwell_seconds: number;
  depletion_rate_pct_per_hour: number;
  classification: 'high_traffic_high_depletion' | 'high_traffic_low_depletion' | 'low_traffic_low_depletion' | 'low_traffic_high_depletion';
  tag: string;
  action_recommendation: string;
}

export interface ReviewQueueItem {
  item_id: string;
  crop_ref: string;
  predicted_sku_id?: string;
  confidence: number;
  status: 'pending' | 'corrected' | 'dismissed';
  ts: number;
}

export interface SystemHealthData {
  status: string;
  camera_connected: boolean;
  inference_fps: number;
  db_operational: boolean;
  offline_sync_queue_size: number;
  uptime_seconds: number;
  hardware_target: string;
  node_id: string;
  store_name: string;
  timestamp: number;
}
