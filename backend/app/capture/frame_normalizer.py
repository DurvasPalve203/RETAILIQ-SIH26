import cv2
import numpy as np
from typing import Tuple, Dict, Any

class FrameNormalizer:
    """
    Handles frame preprocessing, illumination normalization, low-light detection,
    and camera occlusion detection via frame-difference spike analysis.
    """
    def __init__(self, low_light_threshold: float = 45.0, occlusion_diff_threshold: float = 65.0, occlusion_area_ratio: float = 0.35):
        self.low_light_threshold = low_light_threshold
        self.occlusion_diff_threshold = occlusion_diff_threshold
        self.occlusion_area_ratio = occlusion_area_ratio
        self._prev_gray_frame: np.ndarray | None = None
        self._occlusion_active: bool = False
        self._consecutive_occlusion_frames: int = 0

    def normalize(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Normalize frame lighting, check for low light, and compute occlusion metrics.
        Returns:
            normalized_frame: lighting normalized BGR frame
            metrics: dict with {is_low_light, is_occluded, mean_luma, diff_ratio}
        """
        if frame is None or frame.size == 0:
            return frame, {"is_low_light": False, "is_occluded": False, "mean_luma": 0.0, "diff_ratio": 0.0}

        # Convert to LAB color space for robust CLAHE illumination balancing
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        # Calculate mean luminance
        mean_luma = float(np.mean(l_channel))
        is_low_light = mean_luma < self.low_light_threshold

        # Apply Contrast Limited Adaptive Histogram Equalization to L-channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        
        # Merge back and convert to BGR
        merged_lab = cv2.merge((cl, a_channel, b_channel))
        normalized_frame = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

        # Occlusion Detection via Frame Difference
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        is_occluded = False
        diff_ratio = 0.0

        if self._prev_gray_frame is not None and self._prev_gray_frame.shape == gray.shape:
            frame_diff = cv2.absdiff(self._prev_gray_frame, gray)
            _, thresh = cv2.threshold(frame_diff, int(self.occlusion_diff_threshold), 255, cv2.THRESH_BINARY)
            changed_pixels = np.count_nonzero(thresh)
            total_pixels = thresh.size
            diff_ratio = changed_pixels / total_pixels

            # If sudden large difference (> 35% of frame pixels change drastically) or persistent near-black blockage
            if diff_ratio > self.occlusion_area_ratio or (mean_luma < 15.0 and self._prev_gray_frame is not None):
                self._consecutive_occlusion_frames += 1
                if self._consecutive_occlusion_frames >= 2:
                    is_occluded = True
            else:
                self._consecutive_occlusion_frames = max(0, self._consecutive_occlusion_frames - 1)
                is_occluded = False

        self._prev_gray_frame = gray
        self._occlusion_active = is_occluded

        metrics = {
            "is_low_light": is_low_light,
            "is_occluded": is_occluded,
            "mean_luma": round(mean_luma, 2),
            "diff_ratio": round(diff_ratio, 3)
        }

        return normalized_frame, metrics
