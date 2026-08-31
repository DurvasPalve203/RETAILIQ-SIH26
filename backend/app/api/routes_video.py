import cv2
import time
import base64
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter(prefix="/video", tags=["Video Feed & Simulation Controls"])

# Pipeline coordinator reference will be injected at startup
pipeline_instance = None

def set_pipeline_instance(p):
    global pipeline_instance
    pipeline_instance = p

def generate_mjpeg():
    """Generates MJPEG stream frames from pipeline's latest annotated frame."""
    while True:
        if pipeline_instance and pipeline_instance.latest_annotated_frame is not None:
            frame = pipeline_instance.latest_annotated_frame
            ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ret:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        time.sleep(0.06) # ~16 FPS for preview stream

def generate_privacy_mjpeg():
    """Generates MJPEG stream frames from pipeline's split-screen privacy debug view."""
    while True:
        if pipeline_instance and pipeline_instance.latest_privacy_split_frame is not None:
            frame = pipeline_instance.latest_privacy_split_frame
            ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ret:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        time.sleep(0.06)

@router.get("/feed")
def video_feed():
    """Live MJPEG video stream with privacy face blur, bounding boxes, and queue overlays."""
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/privacy-feed")
def privacy_split_feed():
    """Live side-by-side split screen debug view: Raw Feed vs Edge-Blurred Stream with compliance caption."""
    return StreamingResponse(
        generate_privacy_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/privacy-stats")
def get_privacy_stats():
    """Get real-time metrics from the Edge Face Blur Pipeline."""
    if not pipeline_instance or not pipeline_instance.face_blur:
        return {"enabled": True, "faces_detected_count": 0, "detection_method": "Multi-Cascade Face Detector"}
    return pipeline_instance.face_blur.get_stats()

class PrivacyToggleRequest(BaseModel):
    enabled: Optional[bool] = None

@router.post("/privacy-toggle")
def toggle_privacy_blur(req: PrivacyToggleRequest):
    """Dynamically enable, disable, or toggle the Privacy-Preserving Face Blur pipeline."""
    if not pipeline_instance or not pipeline_instance.face_blur:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    if req.enabled is not None:
        pipeline_instance.face_blur.set_enabled(req.enabled)
    else:
        pipeline_instance.face_blur.toggle()

    is_enabled = pipeline_instance.face_blur.enabled
    return {
        "status": "success",
        "privacy_blur_enabled": is_enabled,
        "message": "Privacy Face Blur ENABLED" if is_enabled else "Privacy Face Blur DISABLED (Raw Output Mode)"
    }

class CameraSourceRequest(BaseModel):
    source: str # e.g. "http://172.20.10.3:8080/video" | "0" | "synthetic"
    rotation_deg: Optional[int] = 0

@router.post("/source")
def set_camera_source(req: CameraSourceRequest):
    """
    Module 1: Switch video capture source (Mobile IP Webcam, USB Camera, RTSP, or Synthetic)
    and configure camera orientation rotation (0, 90, 180, 270 degrees) without restarting backend.
    """
    if not pipeline_instance or not pipeline_instance.capture_service:
        raise HTTPException(status_code=503, detail="Pipeline capture service not initialized")

    res = pipeline_instance.capture_service.set_source(
        new_source=req.source,
        rotation_deg=req.rotation_deg or 0
    )
    return res

@router.get("/status")
def get_camera_status():
    """Returns current camera ingestion status, connection health, and capture FPS."""
    if not pipeline_instance or not pipeline_instance.capture_service:
        return {"is_connected": False, "source": "unknown"}
    
    cap_status = pipeline_instance.capture_service.get_status()
    cap_status["inference_fps"] = pipeline_instance.inference_fps
    cap_status["privacy_blur_enabled"] = pipeline_instance.face_blur.enabled if pipeline_instance.face_blur else True
    return cap_status

@router.get("/snapshot")
def get_video_snapshot():
    """Return latest raw frame as base64 JPEG."""
    if not pipeline_instance or pipeline_instance.latest_raw_frame is None:
        raise HTTPException(status_code=503, detail="No video frame available")
    
    frame = pipeline_instance.latest_raw_frame
    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    b64_str = base64.b64encode(jpeg.tobytes()).decode("utf-8")
    return {"image_base64": f"data:image/jpeg;base64,{b64_str}"}

class SimControlRequest(BaseModel):
    action: str # "deplete" | "restock" | "occlusion" | "low_light" | "add_queue" | "serve_queue" | "queue_surge"
    zone_id: Optional[str] = "zone-shelf-01"
    count: Optional[int] = 0
    enabled: Optional[bool] = True

@router.post("/control")
def control_simulation(req: SimControlRequest):
    """
    Module 8: Simulation controls (fallback and interactive demo testing).
    """
    if not pipeline_instance or not pipeline_instance.capture_service.synthetic_stream:
        # If not currently in synthetic mode, notify client
        return {
            "status": "notice",
            "message": "System is currently in LIVE camera mode. Simulation triggers apply to synthetic demo mode.",
            "is_synthetic": False
        }

    stream = pipeline_instance.capture_service.synthetic_stream

    if req.action == "deplete":
        stream.set_depletion(req.zone_id, req.count or 0)
        return {"status": "success", "message": f"Set {req.zone_id} count to {req.count}"}
    elif req.action == "restock":
        stream.restock(req.zone_id)
        return {"status": "success", "message": f"Restocked {req.zone_id}"}
    elif req.action == "add_queue":
        stream.add_queue_shopper()
        return {"status": "success", "message": "Added customer to checkout queue"}
    elif req.action == "serve_queue":
        stream.serve_checkout_customer()
        return {"status": "success", "message": "Front customer checked out & completed service"}
    elif req.action == "queue_surge":
        stream.trigger_queue_surge(count=3)
        return {"status": "success", "message": "Triggered queue surge (+3 customers)"}
    elif req.action == "occlusion":
        stream.toggle_occlusion(req.enabled)
        return {"status": "success", "message": f"Occlusion set to {req.enabled}"}
    elif req.action == "low_light":
        stream.toggle_low_light(req.enabled)
        return {"status": "success", "message": f"Low-light set to {req.enabled}"}

    return {"status": "unknown_action"}
