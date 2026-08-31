import os
import time
import json
import cv2
import threading
import logging
import asyncio
from pathlib import Path
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
from backend.app.active_learning.review_queue_manager import ActiveLearningManager
from backend.app.sync.mqtt_sync import SyncService
from backend.app.queue_pipeline.queue_engine import QueueDetectionEngine
from backend.app.queue_pipeline.wait_time_predictor import WaitTimePredictor
from backend.app.privacy.face_blur import FaceBlurPipeline
from backend.app.alerts.alert_manager import AlertManager
from backend.app.services.metrics_service import metrics_service

logger = logging.getLogger("retailiq.coordinator")

class PipelineCoordinator:
    """
    Main production orchestrator connecting Video Capture -> Shelf & Person Detection -> Tracking ->
    Queue Formation & Pose Classification -> Wait-Time Prediction -> Privacy-Preserving Face Blur ->
    Multi-Level Alert Manager -> Database -> WebSocket Broadcast.
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
        self.active_learning = ActiveLearningManager(sku_matcher=self.sku_matcher)
        self.sync_service = SyncService()

        # Additions from Feature Addendum
        self.queue_engine = QueueDetectionEngine()
        self.wait_predictor = WaitTimePredictor()
        self.face_blur = FaceBlurPipeline()
        self.alert_manager = AlertManager()

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._websocket_broadcaster: Optional[Callable[[Dict[str, Any]], Any]] = None
        
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_privacy_split_frame: Optional[np.ndarray] = None
        self.latest_raw_frame: Optional[np.ndarray] = None
        
        self.latest_state: Dict[str, Any] = {}
        self.latest_queue_states: Dict[str, Any] = {}
        self.latest_queue_predictions: List[Dict[str, Any]] = []
        
        self.inference_fps = 0.0
        self.start_time = time.time()
        self._frame_count = 0
        self._fps_time = time.time()
        
        self._load_zone_baselines()

    def _load_zone_baselines(self):
        """Load stored baseline reference images into the occupancy engine."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT zone_id, baseline_image_path, expected_capacity FROM zones WHERE baseline_image_path IS NOT NULL")
            rows = cursor.fetchall()
            for r in rows:
                zid = r["zone_id"]
                bpath = r["baseline_image_path"]
                cap = r["expected_capacity"] or 10
                if bpath and os.path.exists(bpath):
                    img = cv2.imread(bpath)
                    if img is not None:
                        self.occupancy_engine.set_zone_baseline(zid, img, cap)
                        logger.info(f"Loaded baseline image for zone: {zid}")
        except Exception as e:
            logger.warning(f"Could not load stored zone baselines: {e}")

    def set_websocket_broadcaster(self, broadcaster: Callable[[Dict[str, Any]], Any]):
        self._websocket_broadcaster = broadcaster

    def get_configured_zones(self) -> List[Dict[str, Any]]:
        """Fetch active zones from SQLite including queue axis coordinates."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT zone_id, camera_id, polygon_json, zone_type, label, target_sku_id, expected_capacity, axis_start_xy, axis_end_xy FROM zones")
            rows = cursor.fetchall()
            zones = []
            for r in rows:
                axis_start = json.loads(r["axis_start_xy"]) if r["axis_start_xy"] else None
                axis_end = json.loads(r["axis_end_xy"]) if r["axis_end_xy"] else None
                zones.append({
                    "zone_id": r["zone_id"],
                    "camera_id": r["camera_id"],
                    "polygon": json.loads(r["polygon_json"]),
                    "zone_type": r["zone_type"],
                    "label": r["label"],
                    "target_sku_id": r["target_sku_id"],
                    "expected_capacity": r["expected_capacity"] or 10,
                    "axis_start_xy": axis_start,
                    "axis_end_xy": axis_end
                })
            return zones
        except Exception as e:
            logger.error(f"Error loading zones from DB: {e}")
            return []

    def _extract_zone_crop(self, frame: np.ndarray, polygon: List[Dict[str, float]]) -> Optional[np.ndarray]:
        """Extract rectangular crop corresponding to zone polygon."""
        if frame is None or not polygon:
            return None
        h, w = frame.shape[:2]
        pts = []
        for p in polygon:
            px = p["x"] if p["x"] > 1.0 else p["x"] * w
            py = p["y"] if p["y"] > 1.0 else p["y"] * h
            pts.append([px, py])
        pts_np = np.array(pts, dtype=np.int32)
        zx, zy, zw, zh = cv2.boundingRect(pts_np)
        zx = max(0, zx)
        zy = max(0, zy)
        zw = min(w - zx, zw)
        zh = min(h - zy, zh)
        if zw > 10 and zh > 10:
            return frame[zy:zy+zh, zx:zx+zw].copy()
        return None

    def start(self):
        if self._running:
            return
        self._running = True
        self.capture_service.start()
        self.sync_service.start()
        self.alert_manager.start()
        self._thread = threading.Thread(target=self._pipeline_loop, daemon=True, name="PipelineCoordinatorThread")
        self._thread.start()
        logger.info("Pipeline coordinator started with Queue Intelligence & Privacy Pipeline.")

    def stop(self):
        self._running = False
        self.capture_service.stop()
        self.sync_service.stop()
        self.alert_manager.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Pipeline coordinator stopped.")

    def _pipeline_loop(self):
        while self._running:
            try:
                frame_payload = self.capture_service.get_latest_frame(timeout=0.3)
                if frame_payload is None:
                    time.sleep(0.02)
                    continue

                loop_start = time.time()
                frame = frame_payload["frame"]
                raw_frame = frame_payload["raw_frame"]
                norm_metrics = frame_payload["norm_metrics"]
                is_occluded = norm_metrics["is_occluded"]
                is_camera_disc = frame_payload.get("is_camera_disconnected", False)
                h, w = frame.shape[:2]

                # 1. Fetch Configured Zones
                zones = self.get_configured_zones()

                # 2. Run Shelf Zone & Person Detection
                meta = frame_payload.get("metadata", {})
                det_results = self.detector.detect_and_filter(raw_frame, zones, synthetic_meta=meta)
                products_by_zone = det_results["products_by_zone"]
                gaps_by_zone = det_results["gaps_by_zone"]
                person_detections = det_results["person_detections"]

                # 3. Footfall & Dwell Tracking (ByteTrack)
                tracking_results = self.dwell_engine.update(person_detections, zones, w, h)
                active_tracks = tracking_results["tracks"]

                # Staff presence cooldown check
                for t in active_tracks:
                    for z in zones:
                        if z["zone_type"] == "staff":
                            self.occupancy_engine.record_staff_presence(z["zone_id"])

                # 4. Open-set recognition & SKU Matching on product crops
                for zid, prod_list in products_by_zone.items():
                    for p in prod_list:
                        crop = p.get("crop")
                        if crop is not None and crop.size > 0:
                            matched_sku, sim, is_confident, details = self.sku_matcher.match_crop(crop)
                            p["matched_sku"] = matched_sku
                            p["similarity"] = sim
                            
                            # Active Learning triage for low-confidence detections
                            if not is_confident and crop.size > 400:
                                self.active_learning.enqueue_low_confidence(crop, matched_sku, sim)

                # 5. Dual-Signal Shelf Occupancy & Gap Detection
                zone_statuses = []
                shelf_predictions = []

                for z in zones:
                    zid = z["zone_id"]
                    ztype = z["zone_type"]
                    if ztype != "shelf":
                        continue

                    prod_count = len(products_by_zone.get(zid, []))
                    gap_count = len(gaps_by_zone.get(zid, []))
                    
                    # Extract actual zone crop for SSIM reference differencing
                    zone_crop = self._extract_zone_crop(raw_frame, z.get("polygon", []))
                    
                    eval_res = self.occupancy_engine.evaluate_zone(
                        zone_id=zid,
                        current_zone_crop=zone_crop,
                        detected_products_count=prod_count,
                        detected_gaps_count=gap_count,
                        is_camera_occluded=is_occluded
                    )

                    # Persist stock event if emitted & dispatch to Alert Manager
                    if eval_res["event"]:
                        evt = eval_res["event"]
                        try:
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
                                
                                # Emit raw stock_out event to central AlertManager
                                self.alert_manager.process_raw_event(
                                    source_module="shelf",
                                    event_type="immediate_stockout",
                                    data={
                                        "zone_id": zid,
                                        "zone_label": z["label"],
                                        "severity": evt["severity"],
                                        "is_top_sku": True,
                                        "estimated_lost_sales": 15.0
                                    }
                                )
                            
                            elif evt["type"] == "restock":
                                cursor.execute("""
                                    UPDATE stock_events
                                    SET ts_end = ?, duration_seconds = ?, status = 'resolved'
                                    WHERE event_id = ?;
                                """, (evt["ts_end"], evt["duration_seconds"], evt["closed_event_id"]))
                                conn.commit()
                                self.sync_service.enqueue_event("restock_events", evt)
                                
                                # Auto-resolve alert in AlertManager
                                self.alert_manager.resolve_alert(f"alt-sh-{zid}-imme", reason="Restock detected")
                        except Exception as dbe:
                            logger.warning(f"Database error during stock event write: {dbe}")

                    # Shelf Depletion ETA prediction
                    pred = self.depletion_predictor.predict_eta(zid, eval_res["occupancy_score"], z.get("target_sku_id"))
                    if pred:
                        pred["zone_label"] = z["label"]
                        shelf_predictions.append(pred)

                        if pred["eta_minutes"] <= settings.intelligence_and_prediction.stockout_warning_eta_minutes:
                            self.alert_manager.process_raw_event(
                                source_module="shelf",
                                event_type="predictive_stockout",
                                data={
                                    "zone_id": zid,
                                    "zone_label": z["label"],
                                    "eta_minutes": pred["eta_minutes"],
                                    "confidence": pred["confidence"]
                                }
                            )

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

                # 6. Queue Formation Detection & Wait-Time Prediction
                queue_results = self.queue_engine.process_frame(raw_frame, active_tracks, zones)
                self.latest_queue_states = queue_results["zone_states"]

                # Handle service completions
                for comp_evt in queue_results["service_completion_events"]:
                    self.wait_predictor.record_service_completion(
                        zone_id=comp_evt["zone_id"],
                        track_id=comp_evt.get("track_id"),
                        duration_sec=comp_evt["service_duration_seconds"]
                    )

                # Generate Wait-Time Predictions for each queue zone
                queue_predictions = []
                for zid, qstate in self.latest_queue_states.items():
                    q_pred = self.wait_predictor.predict_wait_time(
                        zone_id=zid,
                        queue_length=qstate["queue_length"],
                        growth_rate=qstate["growth_rate"],
                        zone_label=qstate["label"]
                    )
                    queue_predictions.append(q_pred)

                    # Route queue event to AlertManager
                    if q_pred["estimated_wait_seconds"] >= 240.0 or qstate["queue_length"] >= 3:
                        event_type = "queue_critical_wait" if q_pred["is_critical"] else "queue_buildup"
                        self.alert_manager.process_raw_event(
                            source_module="queue",
                            event_type=event_type,
                            data={
                                "zone_id": zid,
                                "zone_label": qstate["label"],
                                "queue_length": qstate["queue_length"],
                                "growth_rate": qstate["growth_rate"],
                                "estimated_wait_seconds": q_pred["estimated_wait_seconds"],
                                "wait_minutes_formatted": q_pred["wait_minutes_formatted"]
                            }
                        )
                    elif qstate["queue_length"] <= 1:
                        self.alert_manager.resolve_alert(f"alt-qu-{zid}-queu", reason="Queue shortened")

                self.latest_queue_predictions = queue_predictions

                # 7. Render Base Annotated Live Video Frame
                annotated_raw = self._render_live_annotations(
                    frame, zones, det_results, tracking_results, zone_statuses, queue_results, queue_predictions, norm_metrics, is_camera_disc
                )
                self.latest_raw_frame = annotated_raw

                # 8. Apply Privacy-Preserving Face Blur
                blurred_frame, face_count = self.face_blur.apply_face_blur(annotated_raw, person_detections=person_detections)
                self.latest_annotated_frame = blurred_frame

                # Generate Split-Screen Privacy Demo View
                self.latest_privacy_split_frame = self.face_blur.generate_split_screen_demo(
                    annotated_raw, blurred_frame, person_detections=person_detections
                )

                # 9. Compile System State & Record Telemetry
                now = time.time()
                self._frame_count += 1
                if now - self._fps_time >= 1.5:
                    self.inference_fps = round(self._frame_count / (now - self._fps_time), 1)
                    self._frame_count = 0
                    self._fps_time = now

                active_ranked_alerts = self.alert_manager.get_ranked_active_alerts()
                hw_status = self.alert_manager.get_hardware_status()
                privacy_stats = self.face_blur.get_stats()
                cap_status = self.capture_service.get_status()

                # Track metrics
                latency_ms = (now - loop_start) * 1000
                metrics_service.record_loop_latency(latency_ms)
                metrics_service.set_fps(cap_status.get("fps_actual", 0.0), self.inference_fps)

                self.latest_state = {
                    "timestamp": now,
                    "fps": self.inference_fps,
                    "is_occluded": is_occluded,
                    "is_low_light": norm_metrics["is_low_light"],
                    "camera_status": cap_status,
                    "is_synthetic": self.capture_service.is_synthetic(),
                    "zone_statuses": zone_statuses,
                    "active_alerts": active_ranked_alerts,
                    "predictions": shelf_predictions,
                    "queue_predictions": queue_predictions,
                    "queue_states": self.latest_queue_states,
                    "footfall_today": tracking_results["total_footfall_today"],
                    "active_tracks_count": tracking_results["active_tracks_count"],
                    "hardware_status": hw_status,
                    "privacy_stats": privacy_stats
                }

                # 10. Broadcast via WebSocket
                if self._websocket_broadcaster:
                    try:
                        self._websocket_broadcaster(self.latest_state)
                    except Exception:
                        pass

            except Exception as loop_err:
                logger.error(f"Error in pipeline loop: {loop_err}", exc_info=True)
                metrics_service.record_pipeline_error(str(loop_err))
                time.sleep(0.1)

    def _render_live_annotations(
        self,
        frame: np.ndarray,
        zones: List[Dict[str, Any]],
        det_results: Dict[str, Any],
        tracking_results: Dict[str, Any],
        zone_statuses: List[Dict[str, Any]],
        queue_results: Dict[str, Any],
        queue_predictions: List[Dict[str, Any]],
        norm_metrics: Dict[str, Any],
        is_camera_disc: bool = False
    ) -> np.ndarray:
        vis = frame.copy()
        h, w = vis.shape[:2]

        if is_camera_disc:
            return vis

        status_colors = {
            "normal": (50, 205, 50),
            "depleted": (40, 40, 230),
        }
        zone_status_map = {zs["zone_id"]: zs for zs in zone_statuses}
        queue_states = queue_results.get("zone_states", {})

        # Draw Zone Polygons
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
            ztype = z.get("zone_type", "shelf")

            if ztype == "queue_zone":
                color = (255, 180, 20)
                badge_txt = f"{z['label']}: {queue_states.get(zid, {}).get('queue_length', 0)} in line"
            elif ztype == "entrance":
                color = (240, 160, 40)
                badge_txt = z['label']
            elif ztype == "staff":
                color = (180, 120, 240)
                badge_txt = z['label']
            else:
                zstat = zone_status_map.get(zid, {})
                status = zstat.get("status", "normal")
                color = status_colors.get(status, (200, 200, 200))
                occ_pct = int(zstat.get("occupancy_score", 1.0) * 100)
                badge_txt = f"{z['label']}: {occ_pct}%"

            # Draw polygon overlay
            overlay = vis.copy()
            cv2.fillPoly(overlay, [pts_np], color)
            cv2.addWeighted(overlay, 0.15, vis, 0.85, 0, vis)
            cv2.polylines(vis, [pts_np], True, color, 2)

            # Zone Label
            first_pt = pts[0]
            cv2.rectangle(vis, (first_pt[0], max(0, first_pt[1] - 22)), (first_pt[0] + len(badge_txt)*8 + 14, max(22, first_pt[1])), (25, 25, 25), -1)
            cv2.putText(vis, badge_txt, (first_pt[0] + 5, max(16, first_pt[1] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

            # Draw Queue Axis if queue_zone
            if ztype == "queue_zone" and z.get("axis_start_xy") and z.get("axis_end_xy"):
                ax_start = z["axis_start_xy"]
                ax_end = z["axis_end_xy"]
                sx = int(ax_start["x"] if ax_start["x"] > 1.0 else ax_start["x"] * w)
                sy = int(ax_start["y"] if ax_start["y"] > 1.0 else ax_start["y"] * h)
                ex = int(ax_end["x"] if ax_end["x"] > 1.0 else ax_end["x"] * w)
                ey = int(ax_end["y"] if ax_end["y"] > 1.0 else ax_end["y"] * h)

                cv2.arrowedLine(vis, (sx, sy), (ex, ey), (0, 255, 255), 2, tipLength=0.08)
                cv2.circle(vis, (sx, sy), 5, (0, 200, 255), -1)
                cv2.putText(vis, "Start", (sx - 15, sy + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
                cv2.putText(vis, "Counter", (ex - 20, ey + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)

        # Draw Person Tracks with Queue Classification Tags
        classified_map = {t["track_id"]: t for t in queue_results.get("classified_tracks", [])}

        for tr in tracking_results["tracks"]:
            box = tr["box"]
            tid = tr["track_id"]
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            
            q_info = classified_map.get(tid)
            if q_info and q_info["classification"] == "in_queue":
                tag = f"Queue #{q_info.get('queue_position', 1)}"
                tag_col = (0, 220, 255)
            elif q_info and q_info["classification"] == "browsing":
                tag = "Browsing"
                tag_col = (100, 220, 100)
            else:
                tag = f"Person #{tid}"
                tag_col = (255, 200, 0)

            cv2.rectangle(vis, (x1, y1), (x2, y2), tag_col, 2)
            cv2.rectangle(vis, (x1, max(0, y1 - 20)), (x1 + len(tag)*8 + 12, max(20, y1)), tag_col, -1)
            cv2.putText(vis, tag, (x1 + 4, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (20, 20, 20), 1)

        # Draw System HUD on Frame Header
        cv2.rectangle(vis, (0, 0), (w, 34), (18, 22, 28), -1)
        wait_str = queue_predictions[0]["wait_minutes_formatted"] if queue_predictions else "0s"
        
        mode_badge = "SIMULATED" if self.capture_service.is_synthetic() else "LIVE CAMERA"
        fps_str = f"RetailIQ Edge | [{mode_badge}] | FPS: {self.inference_fps} | Queue Wait: {wait_str} | Footfall: {tracking_results['total_footfall_today']}"
        cv2.putText(vis, fps_str, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 240, 180), 1)

        # Privacy Protection Edge Badge
        if self.face_blur.enabled:
            cv2.putText(vis, "[PRIVACY BLUR ACTIVE]", (w - 230, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        else:
            cv2.putText(vis, "[RAW PREVIEW (BLUR OFF)]", (w - 250, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 180, 255), 1)

        if norm_metrics["is_occluded"]:
            cv2.putText(vis, "[OCCLUSION WARNING]", (w - 440, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (50, 50, 255), 2)

        return vis
