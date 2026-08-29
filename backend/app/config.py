import os
import yaml
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field

CONFIG_PATH = Path(os.environ.get("RETAILIQ_CONFIG", "config.yaml"))

class EdgeDeviceConfig(BaseModel):
    node_id: str = "edge-store-01"
    store_name: str = "Apex Retail - Bay Area Express"
    location: str = "Aisle 4 & Checkout Zone"
    hardware_target: str = "edge_offline"

class VideoCaptureConfig(BaseModel):
    source: str = "synthetic"
    width: int = 1280
    height: int = 720
    target_fps: int = 8
    ring_buffer_size: int = 3
    reconnect_initial_delay_sec: float = 1.0
    reconnect_max_delay_sec: float = 30.0
    reconnect_backoff_factor: float = 2.0
    low_light_luma_threshold: float = 45.0
    occlusion_diff_threshold: float = 65.0
    occlusion_min_area_ratio: float = 0.35

class DetectionConfig(BaseModel):
    detector_confidence_threshold: float = 0.45
    nms_iou_threshold: float = 0.45
    embedding_dimension: int = 128
    sku_similarity_threshold: float = 0.72
    min_samples_per_sku_onboarding: int = 5

class OccupancyConfig(BaseModel):
    weight_ssim: float = 0.45
    weight_detection_density: float = 0.55
    rolling_window_frames: int = 12
    depletion_threshold_high: float = 0.30
    depletion_threshold_medium: float = 0.55
    depletion_threshold_low: float = 0.75
    sustained_gap_duration_sec: float = 3.0
    restock_recovery_threshold: float = 0.82
    staff_cooldown_duration_sec: float = 15.0

class TrackingConfig(BaseModel):
    track_high_threshold: float = 0.6
    track_low_threshold: float = 0.1
    match_threshold: float = 0.7
    track_buffer_frames: int = 30
    min_dwell_seconds: float = 2.0

class IntelligenceConfig(BaseModel):
    eta_prediction_lookback_minutes: int = 15
    stockout_warning_eta_minutes: float = 30.0
    sales_loss_dollar_per_minute: float = 2.50
    alert_deduplication_cooldown_sec: float = 45.0

class ActiveLearningConfig(BaseModel):
    min_triage_confidence: float = 0.72
    max_queue_items: int = 200

class SyncLayerConfig(BaseModel):
    mqtt_enabled: bool = False
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic_prefix: str = "retailiq/stores/store-01"
    retry_interval_sec: float = 10.0
    batch_sync_size: int = 50

class DatabaseConfig(BaseModel):
    db_path: str = "backend/data/retailiq.db"

class QueueConfig(BaseModel):
    rolling_window_frames: int = 10
    hysteresis_frames: int = 4
    counter_end_threshold: float = 0.88
    default_service_time_sec: float = 45.0
    service_history_sample_size: int = 20
    critical_wait_threshold_sec: float = 600.0
    medium_wait_threshold_sec: float = 300.0
    weight_orientation: float = 0.35
    weight_velocity: float = 0.25
    weight_spacing: float = 0.20
    weight_dwell: float = 0.20

class PrivacyConfig(BaseModel):
    enabled: bool = True
    face_detector_type: str = "opencv_fast"
    face_confidence_threshold: float = 0.35
    downsample_scale: float = 0.5
    blur_kernel_size: int = 31
    blur_sigma: float = 12.0

class AlertChannelsConfig(BaseModel):
    dashboard_enabled: bool = True
    mqtt_enabled: bool = True
    mqtt_topic_prefix: str = "retailiq/alerts"
    buzzer_enabled: bool = True
    buzzer_gpio_pin: int = 18
    rgb_led_enabled: bool = True
    rgb_led_pins: list[int] = [23, 24, 25]
    sms_enabled: bool = True
    sms_uart_port: str = "COM3"
    sms_uart_baudrate: int = 9600
    store_manager_phone: str = "+1-800-555-0199"

class AlertSubsystemConfig(BaseModel):
    escalation_timeout_sec: float = 300.0
    ack_cooldown_sec: float = 120.0
    channels: AlertChannelsConfig = Field(default_factory=AlertChannelsConfig)

class AppConfig(BaseModel):
    edge_device: EdgeDeviceConfig = Field(default_factory=EdgeDeviceConfig)
    video_capture: VideoCaptureConfig = Field(default_factory=VideoCaptureConfig)
    detection_and_recognition: DetectionConfig = Field(default_factory=DetectionConfig)
    occupancy_and_gap: OccupancyConfig = Field(default_factory=OccupancyConfig)
    tracking_and_footfall: TrackingConfig = Field(default_factory=TrackingConfig)
    intelligence_and_prediction: IntelligenceConfig = Field(default_factory=IntelligenceConfig)
    active_learning: ActiveLearningConfig = Field(default_factory=ActiveLearningConfig)
    sync_layer: SyncLayerConfig = Field(default_factory=SyncLayerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    queue_intelligence: QueueConfig = Field(default_factory=QueueConfig)
    privacy_pipeline: PrivacyConfig = Field(default_factory=PrivacyConfig)
    alert_subsystem: AlertSubsystemConfig = Field(default_factory=AlertSubsystemConfig)


def load_config(config_path: Path = CONFIG_PATH) -> AppConfig:
    if not config_path.exists():
        # Look relative to project root
        root_config = Path(__file__).resolve().parent.parent.parent / "config.yaml"
        if root_config.exists():
            config_path = root_config
        else:
            return AppConfig()
    
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return AppConfig(**data)

# Singleton global configuration instance
settings = load_config()
