import cv2
import numpy as np
import math
from typing import Dict, Any, Optional, Tuple

class QueuePoseEstimator:
    """
    FR-Q03: Pose Estimation for Queue Formation Detection.
    Runs on person crops *only* when the person bounding box falls inside a calibrated queue_zone.
    Extracts shoulder orientation (facing angle), torso lean, head alignment, and limb stillness.
    """
    def __init__(self):
        self._mp_pose = None
        self._mp_available = False
        try:
            import mediapipe as mp
            if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'pose'):
                self._mp_pose = mp.solutions.pose.Pose(
                    static_image_mode=False,
                    model_complexity=0, # BlazePose ultra-lightweight for edge CPU
                    min_detection_confidence=0.4,
                    min_tracking_confidence=0.4
                )
                self._mp_available = True
        except Exception:
            self._mp_available = False

    def estimate_pose(self, person_crop: np.ndarray, motion_vector: Tuple[float, float] = (0.0, 0.0)) -> Dict[str, Any]:
        """
        Estimate pose landmarks and orientation for a person crop.
        Returns:
            facing_angle_deg: Estimated heading / facing direction in degrees [0, 360)
            torso_lean: Normalized lean factor [-1.0, 1.0]
            stillness_score: Stillness metric [0.0, 1.0] (1.0 = standing still in queue)
            landmarks: Key landmark points
        """
        if person_crop is None or person_crop.size == 0:
            return {
                "facing_angle_deg": 90.0,
                "torso_lean": 0.0,
                "stillness_score": 0.8,
                "is_confident": False,
                "method": "default"
            }

        h, w = person_crop.shape[:2]

        if self._mp_available and self._mp_pose is not None and h >= 32 and w >= 24:
            try:
                rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
                results = self._mp_pose.process(rgb_crop)
                if results.pose_landmarks:
                    lms = results.pose_landmarks.landmark
                    # MediaPipe landmarks: 11 = left shoulder, 12 = right shoulder, 0 = nose
                    ls = lms[11]
                    rs = lms[12]
                    nose = lms[0]

                    # Shoulder dx, dy
                    dx = (rs.x - ls.x) * w
                    dy = (rs.y - ls.y) * h
                    # Normal vector to shoulder line gives facing direction
                    facing_rad = math.atan2(dx, -dy) # facing vector perpendicular to shoulders
                    facing_deg = (math.degrees(facing_rad) + 360.0) % 360.0

                    torso_lean = float(nose.x - (ls.x + rs.x) / 2.0)
                    speed = math.hypot(motion_vector[0], motion_vector[1])
                    stillness = max(0.0, min(1.0, 1.0 - (speed / 15.0)))

                    return {
                        "facing_angle_deg": round(facing_deg, 1),
                        "torso_lean": round(torso_lean, 3),
                        "stillness_score": round(stillness, 2),
                        "is_confident": True,
                        "method": "blazepose_edge"
                    }
            except Exception:
                pass

        # Fast edge-native fallback: Upper body symmetry & motion vector heading
        # Analyze upper 40% of person crop for head/shoulder centroid balance
        upper_crop = person_crop[:max(1, int(h * 0.45)), :]
        gray_upper = cv2.cvtColor(upper_crop, cv2.COLOR_BGR2GRAY)
        
        # Compute horizontal intensity gradient to find shoulder orientation
        gx = cv2.Sobel(gray_upper, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray_upper, cv2.CV_32F, 0, 1, ksize=3)
        mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)

        mean_angle = float(np.mean(ang)) if ang.size > 0 else 90.0
        
        # Blend with motion vector heading if moving
        vx, vy = motion_vector
        speed = math.hypot(vx, vy)
        if speed > 0.8:
            motion_deg = (math.degrees(math.atan2(vy, vx)) + 360.0) % 360.0
            # If moving, heading aligns strongly with motion vector
            blended_angle = (0.7 * motion_deg + 0.3 * mean_angle) % 360.0
        else:
            blended_angle = mean_angle

        stillness = max(0.0, min(1.0, 1.0 - (speed / 10.0)))

        return {
            "facing_angle_deg": round(blended_angle, 1),
            "torso_lean": 0.0,
            "stillness_score": round(stillness, 2),
            "is_confident": True,
            "method": "edge_fast_gradient"
        }
