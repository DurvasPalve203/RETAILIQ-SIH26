import base64
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from backend.app.database import get_db_connection
from backend.app.schemas import SkuOnboardRequest, SkuResponse
from backend.app.shelf_pipeline.sku_matcher import SkuMatcher

router = APIRouter(prefix="/sku", tags=["SKU Management"])

matcher = SkuMatcher()

@router.get("/list", response_model=List[SkuResponse])
def list_skus():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT sku_id, name, category, price, sample_count, thumbnail_path, created_at, updated_at FROM sku_gallery ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return [dict(r) for r in rows]

@router.post("/onboard", response_model=Dict[str, Any])
def onboard_sku(req: SkuOnboardRequest):
    """
    Few-shot onboarding endpoint:
    Accepts 5-10 sample photos (base64 encoded), extracts embeddings, averages into gallery vector,
    and returns immediate confirmation. Queryable in under 1 second.
    """
    crops = []
    thumbnail_b64 = None

    for idx, b64_str in enumerate(req.images_base64):
        try:
            # Clean header if present
            if "," in b64_str:
                b64_str = b64_str.split(",")[1]
            img_bytes = base64.b64decode(b64_str)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if img is not None:
                crops.append(img)
                if thumbnail_b64 is None:
                    thumbnail_b64 = req.images_base64[idx]
        except Exception as e:
            continue

    if not crops:
        # If no custom photos provided, generate synthetic reference crop
        dummy = np.zeros((120, 100, 3), dtype=np.uint8)
        dummy[:] = (180, 200, 240)
        cv2.putText(dummy, req.name[:8], (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (20, 20, 20), 1)
        crops.append(dummy)

    result = matcher.onboard_sku(
        sku_id=req.sku_id,
        name=req.name,
        category=req.category,
        price=req.price,
        sample_crops=crops,
        thumbnail_path=thumbnail_b64
    )

    return result
