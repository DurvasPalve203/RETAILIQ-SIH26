from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Point2D(BaseModel):
    x: float
    y: float

class ZoneCreate(BaseModel):
    zone_id: str
    camera_id: str = "cam-01"
    polygon: List[Point2D]  # Normalized coordinates [0, 1] or absolute pixel [x, y]
    zone_type: str = "shelf"  # shelf | entrance | aisle | staff | queue_zone
    label: str
    target_sku_id: Optional[str] = None
    expected_capacity: int = 10
    axis_start_xy: Optional[Point2D] = None # Queue Start (Back of line)
    axis_end_xy: Optional[Point2D] = None   # Counter End (Billing point)

class ZoneResponse(BaseModel):
    zone_id: str
    camera_id: str
    polygon: List[Point2D]
    zone_type: str
    label: str
    target_sku_id: Optional[str] = None
    baseline_image_path: Optional[str] = None
    expected_capacity: int = 10
    axis_start_xy: Optional[Point2D] = None
    axis_end_xy: Optional[Point2D] = None
    created_at: float

class QueueTrackInfo(BaseModel):
    track_id: int
    projection_distance: float
    classification: str # 'in_queue' | 'browsing'
    facing_angle_deg: float = 0.0
    queue_position: int = 1
    estimated_wait_seconds: float = 0.0

class QueueStateResponse(BaseModel):
    zone_id: str
    label: str
    queue_length: int
    growth_rate: float
    tracks: List[QueueTrackInfo]
    average_service_time_sec: float
    estimated_wait_seconds: float
    prediction_confidence: float
    timestamp: float

class QueuePredictionResponse(BaseModel):
    prediction_id: str
    zone_id: str
    zone_label: Optional[str] = None
    estimated_wait_seconds: float
    wait_minutes_formatted: str
    average_service_time_sec: float
    method: str = "rule" # 'rule' | 'lstm'
    confidence: float
    generated_at: float

class AlertItem(BaseModel):
    alert_id: str
    source_module: str # 'shelf' | 'queue' | 'system'
    zone_id: str
    zone_label: Optional[str] = None
    title: str
    message: str
    severity: str # 'CRITICAL' | 'HIGH' | 'LOW'
    state: str # 'NEW' | 'ACKNOWLEDGED' | 'ESCALATED' | 'RESOLVED'
    type: str = "shelf_stockout" # 'immediate_stockout' | 'predictive_stockout' | 'queue_critical_wait' | 'queue_buildup'
    eta_minutes: float = 0.0
    priority_score: float = 50.0
    estimated_lost_sales: float = 0.0
    created_at: float
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    escalate_count: int = 0
    escalation_remaining_sec: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str = "store_staff"

class AlertResolveRequest(BaseModel):
    resolved_by: str = "store_staff"
    reason: str = "manual_override"

class HardwareStatusResponse(BaseModel):
    dashboard_active: bool = True
    mqtt_connected: bool = True
    mqtt_broker: str = "localhost:1883"
    buzzer_enabled: bool = True
    buzzer_active: bool = False
    buzzer_pattern: str = "OFF" # 'OFF' | 'LOW_BEEP' | 'HIGH_DOUBLE_BEEP' | 'CRITICAL_CONTINUOUS'
    rgb_led_enabled: bool = True
    rgb_led_color: str = "OFF" # 'OFF' | 'GREEN' | 'YELLOW' | 'RED'
    rgb_led_state: str = "SOLID" # 'SOLID' | 'BLINKING'
    sms_enabled: bool = True
    sms_status: str = "READY" # 'READY' | 'SENDING' | 'FAILED' | 'EMULATED'
    sms_manager_phone: str = "+1-800-555-0199"
    last_sms_event: Optional[Dict[str, Any]] = None

class PrivacyStreamStats(BaseModel):
    enabled: bool = True
    faces_detected_count: int = 0
    detection_method: str = "OpenCV Face Detector (CPU-Optimized)"
    blur_kernel: str = "Gaussian (31x31)"
    fps: float = 8.0
    caption: str = "Privacy filtering occurs on the edge device before any frame is stored or transmitted."


class SkuOnboardRequest(BaseModel):
    sku_id: str
    name: str
    category: str = "General"
    price: float = 3.99
    images_base64: List[str] = [] # list of base64 encoded photo crops

class SkuResponse(BaseModel):
    sku_id: str
    name: str
    category: str
    price: float
    sample_count: int
    thumbnail_path: Optional[str] = None
    created_at: float
    updated_at: float

class StockEventResponse(BaseModel):
    event_id: str
    zone_id: str
    sku_id_nullable: Optional[str] = None
    sku_name: Optional[str] = None
    type: str  # stock_out | restock | depletion_warning
    severity: str  # low | medium | high
    confidence: float
    ts_start: float
    ts_end: Optional[float] = None
    duration_seconds: float = 0.0
    estimated_lost_sales: float = 0.0
    status: str = "open"

class PredictionResponse(BaseModel):
    prediction_id: str
    zone_id: str
    zone_label: Optional[str] = None
    sku_id_nullable: Optional[str] = None
    sku_name: Optional[str] = None
    eta_minutes: float
    confidence: float
    generated_at: float

class ReviewQueueItem(BaseModel):
    item_id: str
    crop_ref: str
    predicted_sku_id: Optional[str] = None
    confidence: float
    status: str
    corrected_sku_id: Optional[str] = None
    corrected_by: Optional[str] = None
    ts: float

class ReviewCorrectionRequest(BaseModel):
    corrected_sku_id: str
    corrected_by: str = "staff_tablet"
    create_as_new_sku: bool = False
    new_sku_name: Optional[str] = None
    new_sku_category: Optional[str] = "General"

class MerchandisingInsight(BaseModel):
    zone_id: str
    label: str
    zone_type: str
    footfall_count: int
    avg_dwell_seconds: float
    depletion_rate_pct_per_hour: float
    classification: str # 'high_traffic_high_depletion' | 'high_traffic_low_depletion' | 'low_traffic_low_depletion' | 'low_traffic_high_depletion'
    action_recommendation: str

class DashboardSummary(BaseModel):
    total_active_stockouts: int
    predicted_stockouts_next_hour: int
    today_footfall_count: int
    lost_sales_prevented_dollars: float
    lost_sale_minutes_prevented: float
    active_alerts: List[Dict[str, Any]]
    zone_statuses: List[Dict[str, Any]]
    system_health: Dict[str, Any]

class HealthStatus(BaseModel):
    status: str = "healthy"
    camera_connected: bool
    inference_fps: float
    db_operational: bool
    offline_sync_queue_size: int
    uptime_seconds: float
    hardware_target: str
    node_id: str
