import json
import time
import base64
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from backend.app.database import get_db_connection
from backend.app.config import settings
from backend.app.shelf_pipeline.embedding_encoder import ProductEmbeddingEncoder

class SkuMatcher:
    """
    Module 3.2: Open-set product recognition & few-shot SKU gallery management
    - Real-time cosine similarity kNN against SQLite gallery
    - Instant few-shot SKU onboarding without retraining
    - Confidence threshold triage
    """
    def __init__(self, encoder: Optional[ProductEmbeddingEncoder] = None, threshold: float = settings.detection_and_recognition.sku_similarity_threshold):
        self.encoder = encoder or ProductEmbeddingEncoder()
        self.threshold = threshold
        self._gallery_cache: Dict[str, Dict[str, Any]] = {}
        self.refresh_gallery_cache()

    def refresh_gallery_cache(self):
        """Load/refresh in-memory gallery cache from SQLite."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT sku_id, name, category, price, embedding_vector, sample_count FROM sku_gallery")
        rows = cursor.fetchall()
        
        cache = {}
        for r in rows:
            cache[r["sku_id"]] = {
                "sku_id": r["sku_id"],
                "name": r["name"],
                "category": r["category"],
                "price": r["price"],
                "embedding": np.array(json.loads(r["embedding_vector"]), dtype=np.float32),
                "sample_count": r["sample_count"]
            }
        self._gallery_cache = cache

    def onboard_sku(self, sku_id: str, name: str, category: str, price: float, sample_crops: List[np.ndarray], thumbnail_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Few-shot onboarding workflow:
        1. Encodes sample crops into normalized embeddings
        2. Averages them into a reference vector
        3. Persists immediately into SQLite sku_gallery
        4. Instantly queryable within milliseconds
        """
        now = time.time()
        embedding_vec = self.encoder.encode_multiple(sample_crops)
        vec_json = json.dumps(embedding_vec.tolist())
        sample_count = len(sample_crops)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sku_gallery (sku_id, name, category, price, embedding_vector, sample_count, thumbnail_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku_id) DO UPDATE SET
                name=excluded.name,
                category=excluded.category,
                price=excluded.price,
                embedding_vector=excluded.embedding_vector,
                sample_count=excluded.sample_count,
                thumbnail_path=excluded.thumbnail_path,
                updated_at=excluded.updated_at;
        """, (sku_id, name, category, price, vec_json, sample_count, thumbnail_path, now, now))
        conn.commit()

        self.refresh_gallery_cache()
        return {
            "sku_id": sku_id,
            "name": name,
            "sample_count": sample_count,
            "status": "ready"
        }

    def update_sku_embedding_online(self, sku_id: str, new_crop: np.ndarray, alpha: float = 0.2):
        """Online active learning update: incrementally update SKU vector with verified human correction."""
        if sku_id not in self._gallery_cache:
            return
        
        current_vec = self._gallery_cache[sku_id]["embedding"]
        new_vec = self.encoder.encode_crop(new_crop)
        
        # Exponential moving average update
        updated = (1.0 - alpha) * current_vec + alpha * new_vec
        norm = np.linalg.norm(updated)
        if norm > 1e-6:
            updated = updated / norm

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sku_gallery 
            SET embedding_vector = ?, sample_count = sample_count + 1, updated_at = ?
            WHERE sku_id = ?
        """, (json.dumps(updated.tolist()), time.time(), sku_id))
        conn.commit()
        self.refresh_gallery_cache()

    def match_crop(self, crop: np.ndarray) -> Tuple[Optional[str], float, bool, Dict[str, Any]]:
        """
        Compare crop embedding against gallery using cosine similarity.
        Returns: (matched_sku_id, similarity_score, is_confident, sku_details)
        """
        if not self._gallery_cache:
            return None, 0.0, False, {}

        crop_vec = self.encoder.encode_crop(crop)
        
        best_sku = None
        best_sim = -1.0
        best_details = {}

        for sku_id, data in self._gallery_cache.items():
            ref_vec = data["embedding"]
            # Cosine similarity for unit vectors is simply dot product
            sim = float(np.dot(crop_vec, ref_vec))
            if sim > best_sim:
                best_sim = sim
                best_sku = sku_id
                best_details = data

        is_confident = best_sim >= self.threshold
        matched_sku = best_sku if is_confident else None

        return matched_sku, round(max(0.0, best_sim), 3), is_confident, best_details
