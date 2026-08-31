import cv2
import numpy as np
import time
from typing import List, Tuple, Dict, Any, Optional

from backend.app.config import settings

class FaceBlurPipeline:
    """
    Module 6: Privacy-Preserving Face Blur Pipeline
    - Multi-cascade face detection (Frontal Default, Frontal Alt, Profile Face)
    - Person detection head-region projection (guaranteed privacy coverage)
    - Applies Gaussian blur / pixelation before frames are streamed or persisted
    - Dynamic toggle support between Raw and Blurred video feed
    - Generates split-screen debug view for compliance demonstration
    """
    def __init__(self, config=settings.privacy_pipeline):
        self.config = config
        self.enabled = config.enabled
        self.downsample_scale = config.downsample_scale
        self.kernel_size = config.blur_kernel_size if config.blur_kernel_size % 2 == 1 else config.blur_kernel_size + 1
        self.sigma = config.blur_sigma

        # Load OpenCV Face Detector Cascades
        self._cascades = []
        cascade_files = [
            'haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_alt.xml',
            'haarcascade_frontalface_alt2.xml',
            'haarcascade_profileface.xml'
        ]
        for cfile in cascade_files:
            try:
                cpath = cv2.data.haarcascades + cfile
                clf = cv2.CascadeClassifier(cpath)
                if not clf.empty():
                    self._cascades.append(clf)
            except Exception:
                pass

        # Metrics
        self.total_frames_processed = 0
        self.last_face_count = 0
        self.last_blur_latency_ms = 0.0

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Multi-cascade face detection on downsampled frame for high speed and high recall.
        Returns list of (x, y, w, h) in original frame coordinates.
        """
        if frame is None or frame.size == 0 or not self._cascades:
            return []

        h, w = frame.shape[:2]
        scale = max(0.25, min(1.0, self.downsample_scale))

        small_w = max(32, int(w * scale))
        small_h = max(32, int(h * scale))
        small = cv2.resize(frame, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        raw_boxes = []
        for cascade in self._cascades:
            try:
                faces = cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.12,
                    minNeighbors=2, # Low minNeighbors for high-recall privacy safety
                    minSize=(int(14 * scale), int(14 * scale))
                )
                for (sx, sy, sw, sh) in faces:
                    x = int(sx / scale)
                    y = int(sy / scale)
                    bw = int(sw / scale)
                    bh = int(sh / scale)

                    # Expand bounding box by 20% margin for full face & hairline coverage
                    pad_x = int(bw * 0.20)
                    pad_y = int(bh * 0.20)
                    x1 = max(0, x - pad_x)
                    y1 = max(0, y - pad_y)
                    x2 = min(w, x + bw + pad_x)
                    y2 = min(h, y + bh + pad_y)

                    raw_boxes.append((x1, y1, x2 - x1, y2 - y1))
            except Exception:
                continue

        return self._merge_overlapping_boxes(raw_boxes)

    def _merge_overlapping_boxes(self, boxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Non-maximum box merging for overlapping detections."""
        if not boxes:
            return []

        merged = []
        used = [False] * len(boxes)

        for i, (x1, y1, w1, h1) in enumerate(boxes):
            if used[i]:
                continue
            cur_x1, cur_y1, cur_x2, cur_y2 = x1, y1, x1 + w1, y1 + h1
            used[i] = True

            for j, (x2, y2, w2, h2) in enumerate(boxes):
                if used[j]:
                    continue
                # Check overlap
                ox1 = max(cur_x1, x2)
                oy1 = max(cur_y1, y2)
                ox2 = min(cur_x2, x2 + w2)
                oy2 = min(cur_y2, y2 + h2)
                if ox2 > ox1 and oy2 > oy1:
                    # Merge bounding boxes
                    cur_x1 = min(cur_x1, x2)
                    cur_y1 = min(cur_y1, y2)
                    cur_x2 = max(cur_x2, x2 + w2)
                    cur_y2 = max(cur_y2, y2 + h2)
                    used[j] = True

            merged.append((cur_x1, cur_y1, cur_x2 - cur_x1, cur_y2 - cur_y1))

        return merged

    def apply_face_blur(
        self,
        frame: np.ndarray,
        person_detections: Optional[List[Dict[str, Any]]] = None,
        force_blur: bool = False
    ) -> Tuple[np.ndarray, int]:
        """
        Apply Gaussian blur to all detected face regions and person head crops.
        Returns:
            blurred_frame: Frame with face regions redacted
            face_count: Number of faces redacted
        """
        t0 = time.time()
        if frame is None or frame.size == 0:
            return frame, 0

        # If privacy blur is disabled and not forced for split-screen demo
        if not self.enabled and not force_blur:
            return frame.copy(), 0

        blurred = frame.copy()
        h, w = blurred.shape[:2]

        # 1. Detect faces via multi-cascade
        faces = self.detect_faces(frame)

        # 2. Also project head/face region of any person detections (guaranteed coverage)
        if person_detections:
            for p in person_detections:
                box = p.get("box", [])
                if len(box) == 4:
                    px1, py1, px2, py2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                    pw = px2 - px1
                    ph = py2 - py1
                    if pw > 10 and ph > 20:
                        # Top 28-32% of person bounding box is head/face
                        head_x1 = max(0, px1 - int(pw * 0.08))
                        head_y1 = max(0, py1 - int(ph * 0.05))
                        head_x2 = min(w, px2 + int(pw * 0.08))
                        head_y2 = min(h, py1 + int(ph * 0.32))
                        faces.append((head_x1, head_y1, head_x2 - head_x1, head_y2 - head_y1))

        # Merge boxes
        unique_faces = self._merge_overlapping_boxes(faces)

        # 3. Apply heavy Gaussian blur + subtle border to each face ROI
        for (fx, fy, fw, fh) in unique_faces:
            fx1, fy1 = max(0, fx), max(0, fy)
            fx2, fy2 = min(w, fx + fw), min(h, fy + fh)

            if fx2 > fx1 and fy2 > fy1:
                face_roi = blurred[fy1:fy2, fx1:fx2]
                if face_roi.size > 0:
                    k = self.kernel_size
                    # Ensure kernel size is odd and reasonable for ROI size
                    k_w = min(k, (fx2 - fx1) | 1)
                    k_h = min(k, (fy2 - fy1) | 1)
                    k_actual = min(k_w, k_h)
                    if k_actual < 3:
                        k_actual = 3

                    blurred_roi = cv2.GaussianBlur(face_roi, (k_actual, k_actual), self.sigma)
                    blurred[fy1:fy2, fx1:fx2] = blurred_roi

                    # Subtle privacy border outline
                    cv2.rectangle(blurred, (fx1, fy1), (fx2, fy2), (0, 255, 180), 1)

        self.last_face_count = len(unique_faces)
        self.last_blur_latency_ms = round((time.time() - t0) * 1000.0, 2)
        self.total_frames_processed += 1

        return blurred, len(unique_faces)

    def generate_split_screen_demo(
        self,
        raw_frame: np.ndarray,
        blurred_frame: Optional[np.ndarray] = None,
        person_detections: Optional[List[Dict[str, Any]]] = None
    ) -> np.ndarray:
        """
        Builds side-by-side split screen debug view:
        Left: Raw Unblurred In-Memory Frame
        Right: Edge-Blurred Redacted Output Stream
        """
        if raw_frame is None or raw_frame.size == 0:
            return raw_frame

        # Always generate guaranteed blurred version for split screen right side
        if blurred_frame is None:
            blurred_side_img, _ = self.apply_face_blur(raw_frame, person_detections=person_detections, force_blur=True)
        else:
            blurred_side_img = blurred_frame

        h, w = raw_frame.shape[:2]
        half_w = w // 2

        raw_side = cv2.resize(raw_frame, (half_w, h))
        blurred_side = cv2.resize(blurred_side_img, (half_w, h))

        # Combine side-by-side
        split = np.hstack([raw_side, blurred_side])

        # Vertical separator line
        cv2.line(split, (half_w, 0), (half_w, h), (0, 255, 255), 2)

        # Header Badges
        # Left Header (Raw)
        cv2.rectangle(split, (10, 10), (280, 42), (20, 24, 30), -1)
        cv2.putText(split, "RAW IN-MEMORY (INFERENCE ONLY)", (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (80, 180, 255), 1)

        # Right Header (Edge Redacted)
        cv2.rectangle(split, (half_w + 10, 10), (half_w + 330, 42), (20, 24, 30), -1)
        cv2.putText(split, "EDGE-BLURRED (PERSISTED / TRANSMITTED)", (half_w + 18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 180), 1)

        # Bottom Mandatory Compliance Caption Banner
        cv2.rectangle(split, (0, h - 38), (w, h), (15, 18, 22), -1)
        caption_text = "Privacy filtering occurs on the edge device before any frame is stored or transmitted."
        cv2.putText(split, caption_text, (max(10, int(w * 0.06)), h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (240, 240, 240), 1)

        return split

    def get_stats(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "faces_detected_count": self.last_face_count,
            "blur_latency_ms": self.last_blur_latency_ms,
            "total_frames_processed": self.total_frames_processed,
            "detection_method": "Multi-Cascade + Person Head Projection (CPU)",
            "blur_kernel": f"Gaussian ({self.kernel_size}x{self.kernel_size})",
            "caption": "Privacy filtering occurs on the edge device before any frame is stored or transmitted."
        }
