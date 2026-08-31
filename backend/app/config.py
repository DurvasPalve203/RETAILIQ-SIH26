import os
import json
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

logger = logging.getLogger("retailiq.config")

# Automatically load .env file from workspace root or current directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

CONFIG_PATH = Path(os.environ.get("RETAILIQ_CONFIG", str(PROJECT_ROOT / "config.yaml")))

class EdgeDeviceConfig(BaseModel):
    node_id: str = "edge-store-01"
    store_name: str = "Apex Retail - Bay Area Express"
    location: str = "Aisle 4 & Checkout Zone"
    hardware_target: str = "edge_offline"

class VideoCaptureConfig(BaseModel):
    source: str = "http://172.20.10.3:8080/video"
    width: int = 1280
    height: int = 720
    target_fps: int = 8
    rotation_deg: int = 0
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
    seed_on_startup: bool = False

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
    rgb_led_pins: List[int] = [23, 24, 25]
    sms_enabled: bool = True
    sms_uart_port: str = "COM3"
    sms_uart_baudrate: int = 9600
    store_manager_phone: str = "+1-800-555-0199"

class AlertSubsystemConfig(BaseModel):
    escalation_timeout_sec: float = 300.0
    ack_cooldown_sec: float = 120.0
    channels: AlertChannelsConfig = Field(default_factory=AlertChannelsConfig)

class SecurityConfig(BaseModel):
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "*"]
    admin_api_key: str = "retailiq-edge-admin-secret"
    rate_limit_per_minute: int = 120
    jwt_secret: str = "retailiq-edge-jwt-secret-key-prod-2026"

class AppConfig(BaseModel):
    env: str = "development"
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
    security: SecurityConfig = Field(default_factory=SecurityConfig)


def _apply_env_overrides(data: Dict[str, Any]) -> Dict[str, Any]:
    """Applies environment variable overrides to parsed config dictionary."""
    env_name = os.getenv("RETAILIQ_ENV", data.get("env", "development"))
    data["env"] = env_name

    # Edge Device
    if "edge_device" not in data:
        data["edge_device"] = {}
    if os.getenv("NODE_ID"):
        data["edge_device"]["node_id"] = os.getenv("NODE_ID")
    if os.getenv("STORE_NAME"):
        data["edge_device"]["store_name"] = os.getenv("STORE_NAME")
    if os.getenv("LOCATION"):
        data["edge_device"]["location"] = os.getenv("LOCATION")
    if os.getenv("HARDWARE_TARGET"):
        data["edge_device"]["hardware_target"] = os.getenv("HARDWARE_TARGET")

    # Video Capture
    if "video_capture" not in data:
        data["video_capture"] = {}
    if os.getenv("CAMERA_SOURCE"):
        data["video_capture"]["source"] = os.getenv("CAMERA_SOURCE")
    if os.getenv("CAMERA_WIDTH"):
        data["video_capture"]["width"] = int(os.getenv("CAMERA_WIDTH"))
    if os.getenv("CAMERA_HEIGHT"):
        data["video_capture"]["height"] = int(os.getenv("CAMERA_HEIGHT"))
    if os.getenv("CAMERA_TARGET_FPS"):
        data["video_capture"]["target_fps"] = int(os.getenv("CAMERA_TARGET_FPS"))
    if os.getenv("CAMERA_ROTATION_DEG"):
        data["video_capture"]["rotation_deg"] = int(os.getenv("CAMERA_ROTATION_DEG"))

    # Detection
    if "detection_and_recognition" not in data:
        data["detection_and_recognition"] = {}
    if os.getenv("DETECTOR_CONFIDENCE_THRESHOLD"):
        data["detection_and_recognition"]["detector_confidence_threshold"] = float(os.getenv("DETECTOR_CONFIDENCE_THRESHOLD"))
    if os.getenv("SKU_SIMILARITY_THRESHOLD"):
        data["detection_and_recognition"]["sku_similarity_threshold"] = float(os.getenv("SKU_SIMILARITY_THRESHOLD"))

    # Database
    if "database" not in data:
        data["database"] = {}
    if os.getenv("DATABASE_PATH"):
        data["database"]["db_path"] = os.getenv("DATABASE_PATH")
    if os.getenv("SEED_DB_ON_STARTUP") is not None:
        data["database"]["seed_on_startup"] = os.getenv("SEED_DB_ON_STARTUP").lower() in ("true", "1", "yes")

    # Sync
    if "sync_layer" not in data:
        data["sync_layer"] = {}
    if os.getenv("MQTT_ENABLED") is not None:
        data["sync_layer"]["mqtt_enabled"] = os.getenv("MQTT_ENABLED").lower() in ("true", "1", "yes")
    if os.getenv("MQTT_BROKER"):
        data["sync_layer"]["mqtt_broker"] = os.getenv("MQTT_BROKER")
    if os.getenv("MQTT_PORT"):
        data["sync_layer"]["mqtt_port"] = int(os.getenv("MQTT_PORT"))
    if os.getenv("MQTT_TOPIC_PREFIX"):
        data["sync_layer"]["mqtt_topic_prefix"] = os.getenv("MQTT_TOPIC_PREFIX")

    # Security
    if "security" not in data:
        data["security"] = {}
    if os.getenv("CORS_ORIGINS"):
        try:
            data["security"]["cors_origins"] = json.loads(os.getenv("CORS_ORIGINS"))
        except Exception:
            data["security"]["cors_origins"] = [o.strip() for o in os.getenv("CORS_ORIGINS").split(",") if o.strip()]
    if os.getenv("ADMIN_API_KEY"):
        data["security"]["admin_api_key"] = os.getenv("ADMIN_API_KEY")
    if os.getenv("RATE_LIMIT_PER_MINUTE"):
        data["security"]["rate_limit_per_minute"] = int(os.getenv("RATE_LIMIT_PER_MINUTE"))

    # Alert Subsystem
    if "alert_subsystem" not in data:
        data["alert_subsystem"] = {}
    if "channels" not in data["alert_subsystem"]:
        data["alert_subsystem"]["channels"] = {}
    if os.getenv("SMS_UART_PORT"):
        data["alert_subsystem"]["channels"]["sms_uart_port"] = os.getenv("SMS_UART_PORT")
    if os.getenv("STORE_MANAGER_PHONE"):
        data["alert_subsystem"]["channels"]["store_manager_phone"] = os.getenv("STORE_MANAGER_PHONE")

    return data


def load_config(config_path: Path = CONFIG_PATH) -> AppConfig:
    data: Dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Error reading YAML config from {config_path}: {e}")
    else:
        root_config = PROJECT_ROOT / "config.yaml"
        if root_config.exists():
            try:
                with open(root_config, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Error reading root config.yaml: {e}")

    # Merge with environment variables
    merged_data = _apply_env_overrides(data)
    return AppConfig(**merged_data)

# Singleton global configuration instance
settings = load_config()
