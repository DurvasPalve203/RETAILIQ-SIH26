import numpy as np
import cv2
from backend.app.capture.frame_normalizer import FrameNormalizer
from backend.app.capture.synthetic_stream import SyntheticShelfStream
from backend.app.capture.stream_capture import normalize_camera_source

def test_frame_normalizer():
    normalizer = FrameNormalizer(low_light_threshold=40.0)
    
    # 1. Test normal frame
    frame = np.ones((720, 1280, 3), dtype=np.uint8) * 120
    norm_frame, metrics = normalizer.normalize(frame)
    assert norm_frame.shape == (720, 1280, 3)
    assert metrics["is_low_light"] is False
    assert metrics["is_occluded"] is False

    # 2. Test low light frame
    dark_frame = np.ones((720, 1280, 3), dtype=np.uint8) * 20
    _, dark_metrics = normalizer.normalize(dark_frame)
    assert dark_metrics["is_low_light"] is True

def test_synthetic_stream():
    stream = SyntheticShelfStream(width=640, height=360, target_fps=8)
    ret, frame, meta = stream.read()
    assert ret is True
    assert frame.shape == (360, 640, 3)
    assert "ground_truth_boxes" in meta
    assert len(meta["ground_truth_boxes"]) > 0

def test_normalize_camera_source():
    src, is_syn = normalize_camera_source("synthetic")
    assert is_syn is True
    assert src == "synthetic"

    src_ip, is_syn = normalize_camera_source("192.168.1.14:8080")
    assert is_syn is False
    assert src_ip == "http://192.168.1.14:8080/video"

    src_idx, is_syn = normalize_camera_source("0")
    assert is_syn is False
    assert src_idx == 0

if __name__ == "__main__":
    test_frame_normalizer()
    test_synthetic_stream()
    test_normalize_camera_source()
    print("Capture tests passed!")
