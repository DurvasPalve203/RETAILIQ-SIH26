from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Point2D(BaseModel):
    x: float
    y: float

class ZoneCreate(BaseModel):
    zone_id: str
    camera_id: str = "cam-01"
    polygon: List[Point2D]  # Normalized coordinates [0, 1] or absolute pixel [x, y]
    zone_type: str = "shelf"  # shelf | entrance | aisle | staff
    label: str
    target_sku_id: Optional[str] = None
    expected_capacity: int = 10

class ZoneResponse(BaseModel):
    zone_id: str
    camera_id: str
    polygon: List[Point2D]
    zone_type: str
    label: str
    target_sku_id: Optional[str] = None
    baseline_image_path: Optional[str] = None
    expected_capacity: int = 10
    created_at: float

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
