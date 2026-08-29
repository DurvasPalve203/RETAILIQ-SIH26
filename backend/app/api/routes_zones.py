import time
import json
import base64
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from backend.app.database import get_db_connection
from backend.app.schemas import ZoneCreate, ZoneResponse

router = APIRouter(prefix="/zones", tags=["Zones"])

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
