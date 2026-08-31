import os
import time
import json
import base64
from pathlib import Path
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from backend.app.database import get_db_connection
from backend.app.schemas import ZoneCreate, ZoneResponse

router = APIRouter(prefix="/zones", tags=["Zones"])

# Global coordinator reference
pipeline_instance = None

def set_pipeline_instance_zones(p):
    global pipeline_instance
    pipeline_instance = p

BASELINES_DIR = Path("backend/data/baselines")
BASELINES_DIR.mkdir(parents=True, exist_ok=True)

@router.get("", response_model=List[ZoneResponse])
def get_all_zones():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT zone_id, camera_id, polygon_json, zone_type, label, target_sku_id, baseline_image_path, expected_capacity, axis_start_xy, axis_end_xy, created_at FROM zones")
    rows = cursor.fetchall()
    
    result = []
    for r in rows:
        axis_start = json.loads(r["axis_start_xy"]) if r["axis_start_xy"] else None
        axis_end = json.loads(r["axis_end_xy"]) if r["axis_end_xy"] else None
        result.append(ZoneResponse(
            zone_id=r["zone_id"],
            camera_id=r["camera_id"],
            polygon=json.loads(r["polygon_json"]),
            zone_type=r["zone_type"],
            label=r["label"],
            target_sku_id=r["target_sku_id"],
            baseline_image_path=r["baseline_image_path"],
            expected_capacity=r["expected_capacity"] or 10,
            axis_start_xy=axis_start,
            axis_end_xy=axis_end,
            created_at=r["created_at"]
        ))
    return result

@router.get("/live-snapshot")
def get_live_snapshot():
    """Returns current live frame snapshot for zone calibration canvas."""
    if not pipeline_instance or pipeline_instance.latest_raw_frame is None:
        # Fallback dummy canvas
        blank = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(blank, "Connecting to camera stream...", (450, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        _, jpeg = cv2.imencode(".jpg", blank)
        return {"image_base64": f"data:image/jpeg;base64,{base64.b64encode(jpeg.tobytes()).decode('utf-8')}"}

    frame = pipeline_instance.latest_raw_frame
    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    b64_str = base64.b64encode(jpeg.tobytes()).decode("utf-8")
    return {"image_base64": f"data:image/jpeg;base64,{b64_str}"}

@router.post("/capture-baseline/{zone_id}")
def capture_zone_baseline(zone_id: str):
    """
    Module 3.3: Captures current live camera frame crop for the given zone
    and stores it as the 100% full-shelf reference baseline image for SSIM differencing.
    """
    if not pipeline_instance or pipeline_instance.latest_raw_frame is None:
        raise HTTPException(status_code=503, detail="Camera feed not available")

    frame = pipeline_instance.latest_raw_frame
    h, w = frame.shape[:2]

    # Fetch zone polygon
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT polygon_json, expected_capacity FROM zones WHERE zone_id = ?", (zone_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Zone not found")

    poly = json.loads(row["polygon_json"])
    capacity = row["expected_capacity"] or 10

    # Compute bounding rect for zone
    pts = []
    for p in poly:
        px = p["x"] if p["x"] > 1.0 else p["x"] * w
        py = p["y"] if p["y"] > 1.0 else p["y"] * h
        pts.append([px, py])
    pts_np = np.array(pts, dtype=np.int32)
    zx, zy, zw, zh = cv2.boundingRect(pts_np)
    
    zx = max(0, zx)
    zy = max(0, zy)
    zw = min(w - zx, zw)
    zh = min(h - zy, zh)

    if zw < 10 or zh < 10:
        raise HTTPException(status_code=400, detail="Invalid zone bounding area")

    zone_crop = frame[zy:zy+zh, zx:zx+zw].copy()
    file_path = BASELINES_DIR / f"{zone_id}.jpg"
    cv2.imwrite(str(file_path), zone_crop)

    # Register in Occupancy Engine
    pipeline_instance.occupancy_engine.set_zone_baseline(zone_id, zone_crop, capacity)

    # Persist path to database
    cursor.execute("UPDATE zones SET baseline_image_path = ? WHERE zone_id = ?", (str(file_path), zone_id))
    conn.commit()

    _, jpeg = cv2.imencode(".jpg", zone_crop)
    thumb_b64 = base64.b64encode(jpeg.tobytes()).decode("utf-8")

    return {
        "status": "success",
        "zone_id": zone_id,
        "baseline_path": str(file_path),
        "thumbnail_base64": f"data:image/jpeg;base64,{thumb_b64}",
        "message": f"Captured fresh live baseline reference for {zone_id}"
    }

@router.post("/calibrate", response_model=Dict[str, Any])
def calibrate_zones(zones: List[ZoneCreate]):
    """Save or update zone polygons and configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.time()

    for z in zones:
        poly_json = json.dumps([p.dict() for p in z.polygon])
        axis_start_json = json.dumps(z.axis_start_xy.dict()) if z.axis_start_xy else None
        axis_end_json = json.dumps(z.axis_end_xy.dict()) if z.axis_end_xy else None
        
        cursor.execute("""
            INSERT INTO zones (zone_id, camera_id, polygon_json, zone_type, label, target_sku_id, expected_capacity, axis_start_xy, axis_end_xy, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zone_id) DO UPDATE SET
                camera_id=excluded.camera_id,
                polygon_json=excluded.polygon_json,
                zone_type=excluded.zone_type,
                label=excluded.label,
                target_sku_id=excluded.target_sku_id,
                expected_capacity=excluded.expected_capacity,
                axis_start_xy=excluded.axis_start_xy,
                axis_end_xy=excluded.axis_end_xy;
        """, (z.zone_id, z.camera_id, poly_json, z.zone_type, z.label, z.target_sku_id, z.expected_capacity, axis_start_json, axis_end_json, now))
    conn.commit()

    return {"status": "success", "count": len(zones), "message": "Calibrated zones saved."}
