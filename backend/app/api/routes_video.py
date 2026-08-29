import cv2
import time
from fastapi import APIRouter
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
        time.sleep(0.08) # ~12 FPS for preview stream

@router.get("/feed")
def video_feed():
    """Live MJPEG video stream with bounding boxes, zone overlays, and tracking tags."""
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

class SimControlRequest(BaseModel):
    action: str # "deplete" | "restock" | "occlusion" | "low_light"
    zone_id: Optional[str] = "zone-shelf-01"
    count: Optional[int] = 0
    enabled: Optional[bool] = True

@router.post("/control")
def control_simulation(req: SimControlRequest):
    """
    Simulation endpoints to let users / judges test:
    - Depleting milk or yogurt on shelf
    - Restocking a shelf
    - Simulating camera occlusion
    - Simulating store lighting drop
    """
    if not pipeline_instance or not pipeline_instance.capture_service.synthetic_stream:
        return {"status": "error", "message": "Synthetic stream not active"}

    stream = pipeline_instance.capture_service.synthetic_stream

    if req.action == "deplete":
        stream.set_depletion(req.zone_id, req.count or 0)
        return {"status": "success", "message": f"Set {req.zone_id} count to {req.count}"}
    elif req.action == "restock":
        stream.restock(req.zone_id)
        return {"status": "success", "message": f"Restocked {req.zone_id}"}
    elif req.action == "occlusion":
        stream.toggle_occlusion(req.enabled)
        return {"status": "success", "message": f"Occlusion set to {req.enabled}"}
    elif req.action == "low_light":
        stream.toggle_low_light(req.enabled)
        return {"status": "success", "message": f"Low-light set to {req.enabled}"}

    return {"status": "unknown_action"}
