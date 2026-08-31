import time
from fastapi import APIRouter, Response, status
from typing import Dict, Any, Optional
from backend.app.config import settings
from backend.app.database import check_db_health, get_db_connection
from backend.app.services.metrics_service import metrics_service

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

_start_time = time.time()
pipeline_instance_ref = None

def set_pipeline_instance_health(p):
    global pipeline_instance_ref
    pipeline_instance_ref = p

@router.get("/live")
def liveness_check():
    """
    Lightweight liveness probe for Docker / Kubernetes orchestrators.
    Returns 200 if the FastAPI application process is alive.
    """
    return {
        "status": "alive",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "timestamp": time.time()
    }

@router.get("/ready")
def readiness_check(response: Response):
    """
    Readiness probe: validates critical subsystems (Database, Pipeline Coordinator, Camera).
    Returns HTTP 503 if a critical dependency (like the database) is non-functional.
    """
    db_health = check_db_health()
    db_ok = db_health.get("operational", False)

    pipeline_ok = True
    camera_connected = True
    if pipeline_instance_ref:
        pipeline_ok = getattr(pipeline_instance_ref, "_running", False)
        if pipeline_instance_ref.capture_service:
            camera_connected = pipeline_instance_ref.capture_service.is_connected

    is_ready = db_ok and pipeline_ok

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "subsystems": {
            "database": "healthy" if db_ok else "unhealthy",
            "pipeline_thread": "running" if pipeline_ok else "stopped",
            "camera_connected": camera_connected
        },
        "timestamp": time.time()
    }

@router.get("")
def get_system_health():
    """
    Comprehensive diagnostic telemetry for SystemHealthHUD, Admin Monitor, and Prometheus exporters.
    Reflects true live dynamic values from the edge inference pipeline.
    """
    now = time.time()
    db_health = check_db_health()
    db_ok = db_health.get("operational", False)
    
    # Offline sync queue count
    queue_size = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM offline_sync_queue WHERE status = 'pending'")
        queue_size = cursor.fetchone()["cnt"]
    except Exception:
        pass

    # Read live camera & inference state from pipeline instance
    camera_connected = False
    is_synthetic = False
    inference_fps = 0.0
    capture_fps = 0.0
    camera_source = settings.video_capture.source
    active_alerts_count = 0

    if pipeline_instance_ref:
        inference_fps = getattr(pipeline_instance_ref, "inference_fps", 0.0)
        if pipeline_instance_ref.capture_service:
            cap_stat = pipeline_instance_ref.capture_service.get_status()
            camera_connected = cap_stat.get("is_connected", False)
            is_synthetic = cap_stat.get("is_synthetic", False)
            capture_fps = cap_stat.get("fps_actual", 0.0)
            camera_source = cap_stat.get("source", camera_source)
        if pipeline_instance_ref.alert_manager:
            active_alerts = pipeline_instance_ref.alert_manager.get_ranked_active_alerts()
            active_alerts_count = len(active_alerts)

    metrics_service.set_fps(capture_fps, inference_fps)
    metrics_summary = metrics_service.get_metrics_summary()

    overall_status = "healthy"
    if not db_ok:
        overall_status = "unhealthy"
    elif not camera_connected and not is_synthetic:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "camera_connected": camera_connected,
        "is_synthetic": is_synthetic,
        "camera_source": camera_source,
        "capture_fps": capture_fps,
        "inference_fps": inference_fps,
        "db_operational": db_ok,
        "db_health": db_health,
        "offline_sync_queue_size": queue_size,
        "active_alerts_count": active_alerts_count,
        "uptime_seconds": round(now - _start_time, 1),
        "hardware_target": settings.edge_device.hardware_target,
        "node_id": settings.edge_device.node_id,
        "store_name": settings.edge_device.store_name,
        "system_metrics": metrics_summary,
        "timestamp": now
    }
