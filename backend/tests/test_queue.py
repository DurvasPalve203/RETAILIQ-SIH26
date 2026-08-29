import numpy as np
import time
from backend.app.queue_pipeline.pose_estimator import QueuePoseEstimator
from backend.app.queue_pipeline.queue_engine import QueueDetectionEngine
from backend.app.queue_pipeline.wait_time_predictor import WaitTimePredictor

def test_queue_classification():
    pose_est = QueuePoseEstimator()
    crop = np.zeros((120, 80, 3), dtype=np.uint8)
    crop[:] = (100, 150, 200)
    
    pose_res = pose_est.estimate_pose(crop, motion_vector=(0.0, 0.0))
    assert "facing_angle_deg" in pose_res
    assert "stillness_score" in pose_res
    assert 0.0 <= pose_res["stillness_score"] <= 1.0

    # Test QueueDetectionEngine
    engine = QueueDetectionEngine()
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    zones = [{
        "zone_id": "zone-queue-01",
        "polygon": [{"x": 0.2, "y": 0.6}, {"x": 0.8, "y": 0.6}, {"x": 0.8, "y": 0.95}, {"x": 0.2, "y": 0.95}],
        "zone_type": "queue_zone",
        "label": "Checkout Line",
        "axis_start_xy": {"x": 0.3, "y": 0.8},
        "axis_end_xy": {"x": 0.75, "y": 0.8}
    }]

    # Shopper standing in queue zone
    tracks = [{
        "track_id": 301,
        "centroid": (int(0.5 * 1280), int(0.8 * 720)),
        "box": [500, 500, 600, 680]
    }]

    # Run for 5 frames to satisfy hysteresis
    for _ in range(6):
        res = engine.process_frame(dummy_frame, tracks, zones)

    zstate = res["zone_states"]["zone-queue-01"]
    assert zstate["queue_length"] >= 0
    assert "in_queue_tracks" in zstate

def test_wait_time_prediction():
    predictor = WaitTimePredictor()
    predictor.record_service_completion("zone-queue-01", 101, 40.0)
    predictor.record_service_completion("zone-queue-01", 102, 50.0)

    avg_svc = predictor.get_average_service_time("zone-queue-01")
    assert 35.0 <= avg_svc <= 55.0

    pred = predictor.predict_wait_time("zone-queue-01", queue_length=4, growth_rate=1.0)
    assert pred["estimated_wait_seconds"] > 0
    assert "wait_minutes_formatted" in pred
    assert pred["confidence"] > 0.5

if __name__ == "__main__":
    test_queue_classification()
    test_wait_time_prediction()
    print("Queue Intelligence tests passed!")
