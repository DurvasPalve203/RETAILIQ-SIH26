import time
import json
import cv2
import threading
import logging
import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Callable

from backend.app.config import settings
from backend.app.database import get_db_connection
from backend.app.capture.stream_capture import VideoCaptureService
from backend.app.shelf_pipeline.detector import ShelfDetector
from backend.app.shelf_pipeline.embedding_encoder import ProductEmbeddingEncoder
from backend.app.shelf_pipeline.sku_matcher import SkuMatcher
from backend.app.shelf_pipeline.occupancy_engine import ShelfOccupancyEngine
from backend.app.footfall.dwell_engine import DwellAndFootfallEngine
from backend.app.intelligence.depletion_predictor import DepletionPredictor
from backend.app.intelligence.merchandising_insights import MerchandisingInsightsEngine
from backend.app.intelligence.rule_engine import AlertRuleEngine
from backend.app.active_learning.review_queue_manager import ActiveLearningManager
from backend.app.sync.mqtt_sync import SyncService

logger = logging.getLogger("retailiq.coordinator")

class PipelineCoordinator:
    """
    Main orchestrator connecting Video Capture -> Shelf & Person Detection -> Tracking ->
    Occupancy & Depletion Prediction -> Active Learning -> Database -> WebSocket Broadcast.
    """
    def __init__(self):
        self.capture_service = VideoCaptureService()
        self.detector = ShelfDetector()
        self.encoder = ProductEmbeddingEncoder()
        self.sku_matcher = SkuMatcher(encoder=self.encoder)
        self.occupancy_engine = ShelfOccupancyEngine()
        self.dwell_engine = DwellAndFootfallEngine()
        self.depletion_predictor = DepletionPredictor()
        self.insights_engine = MerchandisingInsightsEngine()
        self.rule_engine = AlertRuleEngine()
        self.active_learning = ActiveLearningManager(sku_matcher=self.sku_matcher)
        self.sync_service = SyncService()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._websocket_broadcaster: Optional[Callable[[Dict[str, Any]], Any]] = None
        
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_state: Dict[str, Any] = {}
        self.inference_fps = 0.0
        self.start_time = time.time()
        self._frame_count = 0
        self._fps_time = time.time()

    def set_websocket_broadcaster(self, broadcaster: Callable[[Dict[str, Any]], Any]):
        self._websocket_broadcaster = broadcaster

    def get_configured_zones(self) -> List[Dict[str, Any]]:
        """Fetch active zones from SQLite."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT zone_id, camera_id, polygon_json, zone_type, label, target_sku_id, expected_capacity FROM zones")
        rows = cursor.fetchall()
        zones = []
        for r in rows:
            zones.append({
                "zone_id": r["zone_id"],
                "camera_id": r["camera_id"],
                "polygon": json.loads(r["polygon_json"]),
                "zone_type": r["zone_type"],
                "label": r["label"],
                "target_sku_id": r["target_sku_id"],
                "expected_capacity": r["expected_capacity"] or 10
            })
        return zones

    def start(self):
        if self._running:
            return
        self._running = True
        self.capture_service.start()
        self.sync_service.start()
        self._thread = threading.Thread(target=self._pipeline_loop, daemon=True, name="PipelineCoordinatorThread")
        self._thread.start()
        logger.info("Pipeline coordinator started.")

    def stop(self):
        self._running = False
        self.capture_service.stop()
        self.sync_service.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Pipeline coordinator stopped.")

    def _pipeline_loop(self):
        while self._running:
            frame_payload = self.capture_service.get_latest_frame(timeout=0.3)
            if frame_payload is None:
                time.sleep(0.02)
                continue

            loop_start = time.time()
            frame = frame_payload["frame"]
            raw_frame = frame_payload["raw_frame"]
            norm_metrics = frame_payload["norm_metrics"]
            is_occluded = norm_metrics["is_occluded"]
            h, w = frame.shape[:2]

            # 1. Fetch Zones
            zones = self.get_configured_zones()

            # 2. Run Shelf Zone & Person Detection
            meta = frame_payload.get("metadata", {})
            det_results = self.detector.detect_and_filter(raw_frame, zones, synthetic_meta=meta)
            products_by_zone = det_results["products_by_zone"]
            gaps_by_zone = det_results["gaps_by_zone"]
            person_detections = det_results["person_detections"]

            # 3. Footfall & Dwell Tracking (ByteTrack)
            tracking_results = self.dwell_engine.update(person_detections, zones, w, h)

            # Check for staff presence to activate cooldown if staff is in shelf zone
            for t in tracking_results["tracks"]:
                for z in zones:
                    if z["zone_type"] == "staff":
                        # If person in staff zone, notify occupancy engine
                        self.occupancy_engine.record_staff_presence(z["zone_id"])

            # 4. Open-set recognition & SKU Matching on product crops
            for zid, prod_list in products_by_zone.items():
                for p in prod_list:
                    crop = p.get("crop")
                    if crop is not None and crop.size > 0:
                        matched_sku, sim, is_confident, details = self.sku_matcher.match_crop(crop)
                        p["matched_sku"] = matched_sku
                        p["similarity"] = sim
                        
                        # Active Learning triage: if low confidence, enqueue for human review
                        if not is_confident and crop.size > 400:
                            self.active_learning.enqueue_low_confidence(crop, matched_sku, sim)

            # 5. Dual-Signal Shelf Occupancy & Gap Detection
            zone_statuses = []
            active_stockouts = []
            predictions = []

            for z in zones:
                zid = z["zone_id"]
                ztype = z["zone_type"]
                if ztype != "shelf":
                    continue

                prod_count = len(products_by_zone.get(zid, []))
                gap_count = len(gaps_by_zone.get(zid, []))
                
                # Shelf zone evaluation
                eval_res = self.occupancy_engine.evaluate_zone(
                    zone_id=zid,
                    current_zone_crop=None,
                    detected_products_count=prod_count,
                    detected_gaps_count=gap_count,
                    is_camera_occluded=is_occluded
                )

                # Persist stock event if emitted
                if eval_res["event"]:
                    evt = eval_res["event"]
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    if evt["type"] == "stock_out":
                        cursor.execute("""
                            INSERT INTO stock_events (event_id, zone_id, sku_id_nullable, type, severity, confidence, ts_start, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'open')
                            ON CONFLICT(event_id) DO NOTHING;
                        """, (evt["event_id"], zid, z.get("target_sku_id"), evt["type"], evt["severity"], evt["confidence"], evt["ts_start"]))
                        conn.commit()
                        self.sync_service.enqueue_event("stock_events", evt)
                    
                    elif evt["type"] == "restock":
                        cursor.execute("""
                            UPDATE stock_events
                            SET ts_end = ?, duration_seconds = ?, status = 'resolved'
                            WHERE event_id = ?;
                        """, (evt["ts_end"], evt["duration_seconds"], evt["closed_event_id"]))
                        conn.commit()
                        self.sync_service.enqueue_event("restock_events", evt)

                # Time-to-stockout prediction
                pred = self.depletion_predictor.predict_eta(zid, eval_res["occupancy_score"], z.get("target_sku_id"))
                if pred:
                    pred["zone_label"] = z["label"]
                    predictions.append(pred)

                if eval_res["status"] == "depleted":
                    active_stockouts.append({
                        "zone_id": zid,
                        "zone_label": z["label"],
                        "severity": eval_res["severity"] or "medium",
                        "occupancy": eval_res["occupancy_score"],
                        "ts_start": eval_res.get("event", {}).get("ts_start", time.time())
                    })

                zone_statuses.append({
                    "zone_id": zid,
                    "label": z["label"],
                    "zone_type": ztype,
                    "occupancy_score": eval_res["occupancy_score"],
                    "status": eval_res["status"],
                    "severity": eval_res["severity"],
                    "item_count": prod_count,
                    "target_sku_id": z.get("target_sku_id"),
                    "prediction": pred
                })

            # 6. Alert & Rule Prioritization
            ranked_alerts = self.rule_engine.process_and_rank_alerts(active_stockouts, predictions, is_occluded)

            # 7. Render Annotated Live Video Frame for Dashboard Feed
            annotated = self._render_live_annotations(frame, zones, det_results, tracking_results, zone_statuses, norm_metrics)
            self.latest_annotated_frame = annotated

            # 8. Compile System State
            now = time.time()
            self._frame_count += 1
            if now - self._fps_time >= 1.5:
                self.inference_fps = round(self._frame_count / (now - self._fps_time), 1)
                self._frame_count = 0
                self._fps_time = now

            self.latest_state = {
                "timestamp": now,
                "fps": self.inference_fps,
                "is_occluded": is_occluded,
                "is_low_light": norm_metrics["is_low_light"],
                "zone_statuses": zone_statuses,
                "active_alerts": ranked_alerts,
                "predictions": predictions,
                "footfall_today": tracking_results["total_footfall_today"],
                "active_tracks_count": tracking_results["active_tracks_count"]
            }

            # 9. Broadcast live frame state via WebSocket
            if self._websocket_broadcaster:
                try:
                    self._websocket_broadcaster(self.latest_state)
                except Exception as e:
                    pass

    def _render_live_annotations(self, frame: np.ndarray, zones: List[Dict[str, Any]], det_results: Dict[str, Any], tracking_results: Dict[str, Any], zone_statuses: List[Dict[str, Any]], norm_metrics: Dict[str, Any]) -> np.ndarray:
        vis = frame.copy()
        h, w = vis.shape[:2]

        # Draw Zones
        status_colors = {
            "normal": (50, 205, 50),     # Green
            "depleted": (40, 40, 230),    # Red
        }

        zone_status_map = {zs["zone_id"]: zs for zs in zone_statuses}

        for z in zones:
            poly = z.get("polygon", [])
            if not poly:
                continue
            
            pts = []
            for p in poly:
                px = int(p["x"] if p["x"] > 1.0 else p["x"] * w)
                py = int(p["y"] if p["y"] > 1.0 else p["y"] * h)
                pts.append([px, py])
            
            pts_np = np.array(pts, dtype=np.int32)
            zid = z["zone_id"]
            zstat = zone_status_map.get(zid, {})
            status = zstat.get("status", "normal")
            color = status_colors.get(status, (200, 200, 200))
            if z["zone_type"] == "entrance":
                color = (240, 160, 40) # Cyan-blue for entrance

            # Draw polygon overlay
            overlay = vis.copy()
            cv2.fillPoly(overlay, [pts_np], color)
            cv2.addWeighted(overlay, 0.15, vis, 0.85, 0, vis)
            cv2.polylines(vis, [pts_np], True, color, 2)

            # Zone Label & Occupancy Badge
            first_pt = pts[0]
            occ_pct = int(zstat.get("occupancy_score", 1.0) * 100)
            badge_txt = f"{z['label']}: {occ_pct}%" if z["zone_type"] == "shelf" else f"{z['label']}"
            cv2.rectangle(vis, (first_pt[0], first_pt[1] - 22), (first_pt[0] + len(badge_txt)*9 + 10, first_pt[1]), (25, 25, 25), -1)
            cv2.putText(vis, badge_txt, (first_pt[0] + 5, first_pt[1] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # Draw Person Tracks & Centroids
        for tr in tracking_results["tracks"]:
            box = tr["box"]
            tid = tr["track_id"]
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 200, 0), 2)
            cv2.rectangle(vis, (x1, y1 - 20), (x1 + 75, y1), (255, 200, 0), -1)
            cv2.putText(vis, f"ID #{tid}", (x1 + 4, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1)

        # Draw System HUD on Frame Header
        cv2.rectangle(vis, (0, 0), (w, 34), (20, 24, 30), -1)
        fps_str = f"RetailIQ Edge | FPS: {self.inference_fps} | Today Footfall: {tracking_results['total_footfall_today']}"
        cv2.putText(vis, fps_str, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 240, 180), 1)

        if norm_metrics["is_occluded"]:
            cv2.putText(vis, "[WARNING: CAMERA OCCLUSION DETECTED]", (w - 420, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 50, 255), 2)
        elif norm_metrics["is_low_light"]:
            cv2.putText(vis, "[LOW LIGHT WARNING]", (w - 240, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 200, 255), 1)

        return vis
