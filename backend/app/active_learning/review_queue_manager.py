import time
import uuid
import base64
import cv2
import json
import numpy as np
from typing import List, Dict, Optional, Any
from backend.app.config import settings
from backend.app.database import get_db_connection
from backend.app.shelf_pipeline.sku_matcher import SkuMatcher

class ActiveLearningManager:
    """
    Module 6: Active Learning / Human-in-the-Loop Correction
    - Manages the low-confidence triage review queue
    - Operationalizes few-shot onboarding by instantly updating SKU embeddings upon staff confirmation
    - No model retraining needed for continuous operational accuracy gains
    """
    def __init__(self, sku_matcher: SkuMatcher, config=settings.active_learning):
        self.sku_matcher = sku_matcher
        self.config = config

    def enqueue_low_confidence(self, crop: np.ndarray, predicted_sku_id: Optional[str], confidence: float) -> Optional[str]:
        """Add low confidence recognition crop to review queue."""
        if crop is None or crop.size == 0:
            return None

        # Check queue size
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM review_queue WHERE status = 'pending'")
        count = cursor.fetchone()["cnt"]
        if count >= self.config.max_queue_items:
            return None

        # Encode crop as JPEG base64 string
        _, buffer = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
        b64_crop = base64.b64encode(buffer).decode("utf-8")
        crop_ref = f"data:image/jpeg;base64,{b64_crop}"

        # Get embedding vector
        emb = self.sku_matcher.encoder.encode_crop(crop)
        emb_json = json.dumps(emb.tolist())

        item_id = f"rev-{uuid.uuid4().hex[:8]}"
        now = time.time()

        cursor.execute("""
            INSERT INTO review_queue (item_id, crop_ref, predicted_sku_id, confidence, status, embedding_vector, ts)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """, (item_id, crop_ref, predicted_sku_id, round(confidence, 2), emb_json, now))
        conn.commit()

        return item_id

    def get_pending_reviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch pending items in review queue for staff tablet screen."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT item_id, crop_ref, predicted_sku_id, confidence, status, ts
            FROM review_queue
            WHERE status = 'pending'
            ORDER BY ts DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    def submit_correction(
        self,
        item_id: str,
        corrected_sku_id: str,
        corrected_by: str = "staff_tablet",
        create_as_new_sku: bool = False,
        new_sku_name: Optional[str] = None,
        new_sku_category: str = "General"
    ) -> Dict[str, Any]:
        """
        Processes human verification or correction:
        1. Marks item as 'corrected' in review queue
        2. Updates or creates SKU gallery entry immediately
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT item_id, crop_ref, embedding_vector FROM review_queue WHERE item_id = ?", (item_id,))
        item = cursor.fetchone()
        if not item:
            raise ValueError(f"Review item {item_id} not found.")

        emb_vector = np.array(json.loads(item["embedding_vector"]), dtype=np.float32)
        now = time.time()

        if create_as_new_sku:
            target_sku_id = corrected_sku_id or f"SKU-NEW-{int(now)%10000}"
            sku_name = new_sku_name or f"New Product ({target_sku_id})"
            
            # Insert new SKU into gallery
            cursor.execute("""
                INSERT INTO sku_gallery (sku_id, name, category, price, embedding_vector, sample_count, thumbnail_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            """, (target_sku_id, sku_name, new_sku_category, 4.99, json.dumps(emb_vector.tolist()), item["crop_ref"], now, now))
            corrected_sku_id = target_sku_id
        else:
            # Update existing SKU embedding with verified crop vector
            cursor.execute("SELECT embedding_vector, sample_count FROM sku_gallery WHERE sku_id = ?", (corrected_sku_id,))
            sku_row = cursor.fetchone()
            if sku_row:
                current_vec = np.array(json.loads(sku_row["embedding_vector"]), dtype=np.float32)
                # Exponential moving average update (alpha = 0.25)
                updated_vec = 0.75 * current_vec + 0.25 * emb_vector
                norm = np.linalg.norm(updated_vec)
                if norm > 1e-6:
                    updated_vec = updated_vec / norm
                cursor.execute("""
                    UPDATE sku_gallery
                    SET embedding_vector = ?, sample_count = sample_count + 1, updated_at = ?
                    WHERE sku_id = ?
                """, (json.dumps(updated_vec.tolist()), now, corrected_sku_id))

        # Mark review queue item as corrected
        cursor.execute("""
            UPDATE review_queue
            SET status = 'corrected', corrected_sku_id = ?, corrected_by = ?
            WHERE item_id = ?
        """, (corrected_sku_id, corrected_by, item_id))
        conn.commit()

        # Refresh in-memory gallery cache
        self.sku_matcher.refresh_gallery_cache()

        return {
            "item_id": item_id,
            "status": "corrected",
            "corrected_sku_id": corrected_sku_id,
            "gallery_updated": True
        }
