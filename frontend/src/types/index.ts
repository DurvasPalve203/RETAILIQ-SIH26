export interface Point2D {
  x: number;
  y: number;
}

export interface Zone {
  zone_id: string;
  camera_id: string;
  polygon: Point2D[];
  zone_type: 'shelf' | 'entrance' | 'aisle' | 'staff' | 'queue_zone';
  label: string;
  target_sku_id?: string;
  expected_capacity: number;
  axis_start_xy?: Point2D;
  axis_end_xy?: Point2D;
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
  source_module: 'shelf' | 'queue' | 'system';
  zone_id: string;
  zone_label?: string;
  title: string;
  message: string;
  type: string; // 'immediate_stockout' | 'predictive_stockout' | 'queue_critical_wait' | 'queue_buildup'
  severity: 'CRITICAL' | 'HIGH' | 'LOW' | 'high' | 'medium' | 'low';
  state: 'NEW' | 'ACKNOWLEDGED' | 'ESCALATED' | 'RESOLVED';
  eta_minutes: number;
  priority_score: number;
  estimated_lost_sales: number;
  created_at: number;
  acknowledged_at?: number;
  resolved_at?: number;
  escalate_count: number;
  escalation_remaining_sec?: number;
  details?: Record<string, any>;
}

export interface QueueTrackInfo {
  track_id: number;
  zone_id: string;
  projection_distance: number;
  classification: 'in_queue' | 'browsing';
  facing_angle_deg: number;
  queue_position: number;
  score?: number;
}

export interface QueueZoneState {
  zone_id: string;
  label: string;
  queue_length: number;
  growth_rate: number;
  total_occupants: number;
  in_queue_tracks: QueueTrackInfo[];
  browsing_tracks: QueueTrackInfo[];
  axis_start: [number, number];
  axis_end: [number, number];
}

export interface QueuePrediction {
  prediction_id: string;
  zone_id: string;
  zone_label?: string;
  queue_length: number;
  growth_rate: number;
  average_service_time_sec: number;
  tier1_wait_seconds: number;
  estimated_wait_seconds: number;
  wait_minutes_formatted: string;
  confidence: number;
  method: string;
  generated_at: number;
  is_critical?: boolean;
  is_high?: boolean;
}

export interface HardwareStatus {
  dashboard_active: boolean;
  mqtt_connected: boolean;
  mqtt_broker: string;
  buzzer_enabled: boolean;
  buzzer_active: boolean;
  buzzer_pattern: string;
  rgb_led_enabled: boolean;
  rgb_led_color: string;
  rgb_led_state: string;
  sms_enabled: boolean;
  sms_status: string;
  sms_manager_phone: string;
  last_sms_event?: {
    phone: string;
    severity: string;
    message: string;
    status: string;
    timestamp: number;
    hardware_mode: string;
    at_sequence: string;
  };
}

export interface PrivacyStats {
  enabled: boolean;
  faces_detected_count: number;
  blur_latency_ms: number;
  total_frames_processed: number;
  detection_method: string;
  blur_kernel: string;
  caption: string;
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
  queue_predictions?: QueuePrediction[];
  queue_states?: Record<string, QueueZoneState>;
  footfall_today: number;
  active_tracks_count: number;
  hardware_status?: HardwareStatus;
  privacy_stats?: PrivacyStats;
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
