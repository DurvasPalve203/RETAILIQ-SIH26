import numpy as np
import cv2
from backend.app.shelf_pipeline.embedding_encoder import ProductEmbeddingEncoder
from backend.app.shelf_pipeline.sku_matcher import SkuMatcher
from backend.app.shelf_pipeline.occupancy_engine import ShelfOccupancyEngine

def test_embedding_and_matching():
    encoder = ProductEmbeddingEncoder(embedding_dim=128)
    crop_a = np.zeros((100, 100, 3), dtype=np.uint8)
    crop_a[:] = (200, 50, 50)
    
    vec_a = encoder.encode_crop(crop_a)
    assert vec_a.shape == (128,)
    # Verify L2 norm is ~1.0
    norm = np.linalg.norm(vec_a)
    assert np.isclose(norm, 1.0, atol=1e-3)

    matcher = SkuMatcher(encoder=encoder)
    matcher.onboard_sku("TEST-SKU-01", "Test Product", "Snacks", 2.99, [crop_a])
    
    # Matching same crop should yield high similarity >= 0.9
    sku_id, sim, is_confident, _ = matcher.match_crop(crop_a)
    assert sku_id == "TEST-SKU-01"
    assert is_confident is True
    assert sim >= 0.90

def test_occupancy_engine():
    import time
    engine = ShelfOccupancyEngine()
    engine.set_zone_baseline("zone-test", baseline_frame=None, expected_capacity=10)
    t = time.time()

    # 1. Test full shelf
    res_full = engine.evaluate_zone("zone-test", None, detected_products_count=10, detected_gaps_count=0, timestamp=t)
    assert res_full["status"] == "normal"
    assert res_full["occupancy_score"] > 0.8

    # 2. Test empty shelf trigger (sustained for 4 seconds)
    for i in range(15):
        t += 0.5
        res_empty = engine.evaluate_zone("zone-test", None, detected_products_count=0, detected_gaps_count=10, timestamp=t)
    
    assert res_empty["status"] == "depleted"
    assert res_empty["severity"] == "high"

if __name__ == "__main__":
    test_embedding_and_matching()
    test_occupancy_engine()
    print("Shelf pipeline tests passed!")
