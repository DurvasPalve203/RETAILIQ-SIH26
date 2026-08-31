import cv2
import numpy as np
import time
from typing import List, Dict, Any, Tuple, Optional
from backend.app.config import settings

class ShelfDetector:
    """
    Module 3.1 & Module 5: Real-Time Shelf Zone & Person Detection
    - Real-time CPU HOG People Detector + Haar Upper-body Cascade for genuine person detection & ByteTrack
    - Visual saliency & edge clustering product detection inside calibrated shelf zones
    - Point-in-polygon assignment for shelf, queue, entrance, and staff zones
    - Crops product bounding boxes for downstream open-set recognition
    """
    def __init__(self, confidence_thresh: float = settings.detection_and_recognition.detector_confidence_threshold):
        self.confidence_thresh = confidence_thresh
        
        # Initialize HOG People Detector
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        # Load Upper Body and Full Body Cascades for robust person detection
        self._body_cascades = []
        for cname in ['haarcascade_upperbody.xml', 'haarcascade_fullbody.xml']:
            try:
                cpath = cv2.data.haarcascades + cname
                clf = cv2.CascadeClassifier(cpath)
                if not clf.empty():
                    self._body_cascades.append(clf)
            except Exception:
                pass

    def is_point_in_polygon(self, point: Tuple[float, float], polygon: List[Dict[str, float]], frame_w: int, frame_h: int) -> bool:
        """Point-in-polygon test using OpenCV."""
        if not polygon:
            return False
        pts = []
        for p in polygon:
            px = p["x"] if p["x"] > 1.0 else p["x"] * frame_w
            py = p["y"] if p["y"] > 1.0 else p["y"] * frame_h
            pts.append([px, py])
        pts_np = np.array(pts, dtype=np.int32)
        dist = cv2.pointPolygonTest(pts_np, (float(point[0]), float(point[1])), False)
        return dist >= 0

    def _detect_persons(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Runs HOG people detector + Upper Body cascade on frame.
        Optimized for real-time edge CPU performance.
        """
        h, w = frame.shape[:2]
        scale = 0.5
        small_w = max(64, int(w * scale))
        small_h = max(64, int(h * scale))
        small = cv2.resize(frame, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        person_boxes = []

        # 1. HOG People Detector
        try:
            rects, weights = self.hog.detectMultiScale(
                small,
                winStride=(8, 8),
                padding=(8, 8),
                scale=1.05,
                hitThreshold=0.0
            )
            for i, (rx, ry, rw, rh) in enumerate(rects):
                weight = float(weights[i]) if i < len(weights) else 0.7
                if weight > -0.2: # permissive threshold for high recall
                    x1 = max(0, int(rx / scale))
                    y1 = max(0, int(ry / scale))
                    x2 = min(w, int((rx + rw) / scale))
                    y2 = min(h, int((ry + rh) / scale))
                    if (x2 - x1) > 20 and (y2 - y1) > 40:
                        person_boxes.append({
                            "box": [x1, y1, x2, y2],
                            "confidence": min(0.98, max(0.60, 0.75 + weight * 0.1)),
                            "class": "person"
                        })
        except Exception:
            pass

        # 2. Upper body cascade (especially good for shoppers in checkout queues)
        for cascade in self._body_cascades:
            try:
                bodies = cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.15,
                    minNeighbors=2,
                    minSize=(int(30 * scale), int(45 * scale))
                )
                for (bx, by, bw, bh) in bodies:
                    x1 = max(0, int(bx / scale))
                    y1 = max(0, int(by / scale))
                    x2 = min(w, int((bx + bw) / scale))
                    # Expand height downwards for estimated full body
                    y2 = min(h, int((by + bh * 1.8) / scale))
                    person_boxes.append({
                        "box": [x1, y1, x2, y2],
                        "confidence": 0.80,
                        "class": "person"
                    })
            except Exception:
                pass

        # Merge overlapping person detections
        merged = []
        used = [False] * len(person_boxes)
        for i, det1 in enumerate(person_boxes):
            if used[i]:
                continue
            b1 = det1["box"]
            cur_x1, cur_y1, cur_x2, cur_y2 = b1
            cur_conf = det1["confidence"]
            used[i] = True

            for j, det2 in enumerate(person_boxes):
                if used[j]:
                    continue
                b2 = det2["box"]
                # Overlap test
                ox1 = max(cur_x1, b2[0])
                oy1 = max(cur_y1, b2[1])
                ox2 = min(cur_x2, b2[2])
                oy2 = min(cur_y2, b2[3])
                if ox2 > ox1 and oy2 > oy1:
                    cur_x1 = min(cur_x1, b2[0])
                    cur_y1 = min(cur_y1, b2[1])
                    cur_x2 = max(cur_x2, b2[2])
                    cur_y2 = max(cur_y2, b2[3])
                    cur_conf = max(cur_conf, det2["confidence"])
                    used[j] = True

            merged.append({
                "box": [cur_x1, cur_y1, cur_x2, cur_y2],
                "confidence": cur_conf,
                "class": "person"
            })

        return merged

    def detect_and_filter(self, frame: np.ndarray, zones: List[Dict[str, Any]], synthetic_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run detection and assign detections to specific calibrated zones.
        Returns:
            products_by_zone: dict {zone_id: [detection_objects]}
            gaps_by_zone: dict {zone_id: [gap_objects]}
            person_detections: list of person bounding boxes for ByteTrack
            all_detections: flat list of all boxes
        """
        h, w = frame.shape[:2]
        raw_detections = []

        # If synthetic stream provided ground-truth boxes, use them
        if synthetic_meta and "ground_truth_boxes" in synthetic_meta:
            for b in synthetic_meta["ground_truth_boxes"]:
                raw_detections.append(b)
        else:
            # 1. Real Person Detection on Live Camera Frames
            person_dets = self._detect_persons(frame)
            raw_detections.extend(person_dets)

            # 2. Real Product Detection inside Shelf Zones
            shelf_zones = [z for z in zones if z.get("zone_type") == "shelf"]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            for sz in shelf_zones:
                poly = sz.get("polygon", [])
                if not poly:
                    continue
                
                # Get polygon bounding box
                pts = []
                for p in poly:
                    px = p["x"] if p["x"] > 1.0 else p["x"] * w
                    py = p["y"] if p["y"] > 1.0 else p["y"] * h
                    pts.append([px, py])
                pts_np = np.array(pts, dtype=np.int32)
                zx, zy, zw, zh = cv2.boundingRect(pts_np)
                
                zx = max(0, zx)
                zy = max(0, zy)
                zw = min(w - zx, zw)
                zh = min(h - zy, zh)
                
                if zw < 20 or zh < 20:
                    continue

                zone_roi_gray = gray[zy:zy+zh, zx:zx+zw]
                
                # Adaptive threshold for product edge region proposals
                thresh = cv2.adaptiveThreshold(zone_roi_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 3)
                # Morphological closing to group item contours
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                
                contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                expected_cap = sz.get("expected_capacity", 8)
                min_prod_w = max(15, zw // (expected_cap * 3))
                max_prod_w = int(zw * 0.45)
                min_prod_h = int(zh * 0.25)
                max_prod_h = int(zh * 0.98)
                
                for cnt in contours:
                    cx, cy, cw, ch = cv2.boundingRect(cnt)
                    if min_prod_w <= cw <= max_prod_w and min_prod_h <= ch <= max_prod_h:
                        abs_x1 = zx + cx
                        abs_y1 = zy + cy
                        abs_x2 = abs_x1 + cw
                        abs_y2 = abs_y1 + ch
                        raw_detections.append({
                            "box": [abs_x1, abs_y1, abs_x2, abs_y2],
                            "class": "product",
                            "confidence": 0.82,
                            "zone_id": sz["zone_id"]
                        })

        products_by_zone = {z["zone_id"]: [] for z in zones}
        gaps_by_zone = {z["zone_id"]: [] for z in zones}
        person_detections = []
        all_detections = []

        for det in raw_detections:
            box = det["box"]
            x1, y1, x2, y2 = box
            cls_name = det.get("class", "product")
            conf = det.get("confidence", 0.8)

            if conf < self.confidence_thresh:
                continue

            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            centroid = (cx, cy)

            if cls_name == "person":
                person_detections.append({
                    "box": box,
                    "centroid": centroid,
                    "confidence": conf,
                    "track_id": det.get("track_id")
                })
                all_detections.append(det)
                continue

            # Check which zone polygon contains this box centroid (or if pre-assigned)
            matched_zone_id = det.get("zone_id")
            if not matched_zone_id:
                for zone in zones:
                    poly = zone.get("polygon", [])
                    if self.is_point_in_polygon(centroid, poly, w, h):
                        matched_zone_id = zone["zone_id"]
                        break

            if matched_zone_id and matched_zone_id in products_by_zone:
                # Crop product image from frame for recognition
                crop = frame[max(0, int(y1)):min(h, int(y2)), max(0, int(x1)):min(w, int(x2))]
                det_obj = {
                    "box": box,
                    "centroid": centroid,
                    "confidence": conf,
                    "zone_id": matched_zone_id,
                    "crop": crop,
                    "sku": det.get("sku")
                }
                
                if cls_name == "product":
                    products_by_zone[matched_zone_id].append(det_obj)
                elif cls_name == "empty_shelf_gap":
                    gaps_by_zone[matched_zone_id].append(det_obj)

                all_detections.append(det_obj)

        return {
            "products_by_zone": products_by_zone,
            "gaps_by_zone": gaps_by_zone,
            "person_detections": person_detections,
            "all_detections": all_detections
        }
