import numpy as np
import cv2
from backend.app.privacy.face_blur import FaceBlurPipeline

def test_face_blur():
    pipeline = FaceBlurPipeline()
    
    # Create test synthetic frame with simulated person head
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (180, 180, 180)
    
    # Draw head circle
    cv2.circle(frame, (320, 200), 40, (210, 180, 160), -1)
    cv2.circle(frame, (310, 190), 4, (40, 30, 20), -1)
    cv2.circle(frame, (330, 190), 4, (40, 30, 20), -1)

    person_dets = [{"box": [260, 140, 380, 440]}]
    blurred, face_count = pipeline.apply_face_blur(frame, person_detections=person_dets)

    assert blurred.shape == frame.shape
    assert face_count >= 1
    
    # Verify split-screen demo generator
    split = pipeline.generate_split_screen_demo(frame, blurred)
    assert split.shape == frame.shape

    stats = pipeline.get_stats()
    assert stats["enabled"] is True
    assert "Privacy filtering occurs on the edge device" in stats["caption"]

if __name__ == "__main__":
    test_face_blur()
    print("Privacy pipeline tests passed!")
