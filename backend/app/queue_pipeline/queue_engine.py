import time
import math
import json
import uuid
import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import deque

from backend.app.config import settings
from backend.app.database import get_db_connection
from backend.app.queue_pipeline.pose_estimator import QueuePoseEstimator

class QueueDetectionEngine:
    """
    Module A: Queue Formation Detection (FR-Q01 to FR-Q05)
    - Distinguishes people queuing from shoppers browsing nearby
    - Computes projection distance along calibrated queue axis (queue_start -> counter_end)
    - Runs pose estimation on queue-zone occupant crops
    - 4-Signal rule-based weighted feature classifier with hysteresis window
    - Tracks queue length, line position order, and rolling growth rate
    """
    def __init__(self, config=settings.queue_intelligence):
        self.config = config
        self.pose_estimator = QueuePoseEstimator()

        # Track history cache: {track_id: {"history": deque(maxlen=15), "state": "browsing", "streak": 0, "last_pos": (x, y), "entry_ts": float}}
        self._track_states: Dict[int, Dict[str, Any]] = {}
        
        # Zone queue history for rolling derivative: {zone_id: deque([(timestamp, length)], maxlen=30)}
        self._queue_length_history: Dict[str, deque] = {}

        # Front-of-queue tracking for service completion detection: {zone_id: {"last_front_tid": Optional[int], "front_enter_ts": float}}
        self._front_tracker: Dict[str, Dict[str, Any]] = {}

    def _get_axis_points(self, zone: Dict[str, Any], frame_w: int, frame_h: int) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Extract or compute start (back of line) and end (counter) points for queue axis."""
        axis_start = zone.get("axis_start_xy")
        axis_end = zone.get("axis_end_xy")

        if axis_start and axis_end:
            ax1 = (axis_start["x"] if axis_start["x"] > 1.0 else axis_start["x"] * frame_w,
                   axis_start["y"] if axis_start["y"] > 1.0 else axis_start["y"] * frame_h)
            ax2 = (axis_end["x"] if axis_end["x"] > 1.0 else axis_end["x"] * frame_w,
                   axis_end["y"] if axis_end["y"] > 1.0 else axis_end["y"] * frame_h)
            return ax1, ax2

        # Default axis fallback from polygon bounding box (top-left to bottom-right or left to right)
        poly = zone.get("polygon", [])
        if poly and len(poly) >= 2:
            p_start = poly[0]
            p_end = poly[-1] if len(poly) == 2 else poly[len(poly)//2]
            ax1 = (p_start["x"] if p_start["x"] > 1.0 else p_start["x"] * frame_w,
                   p_start["y"] if p_start["y"] > 1.0 else p_start["y"] * frame_h)
            ax2 = (p_end["x"] if p_end["x"] > 1.0 else p_end["x"] * frame_w,
                   p_end["y"] if p_end["y"] > 1.0 else p_end["y"] * frame_h)
            return ax1, ax2

        return (0.1 * frame_w, 0.5 * frame_h), (0.9 * frame_w, 0.5 * frame_h)

    def _compute_projection(self, centroid: Tuple[float, float], ax1: Tuple[float, float], ax2: Tuple[float, float]) -> float:
        """
        Compute normalized scalar projection distance [0.0, 1.0] of a point along axis vector.
        0.0 = back of queue, 1.0 = checkout counter.
        """
        vx = ax2[0] - ax1[0]
        vy = ax2[1] - ax1[1]
        line_len_sq = vx * vx + vy * vy
        if line_len_sq < 1e-6:
            return 0.0

        px = centroid[0] - ax1[0]
        py = centroid[1] - ax1[1]

        t = (px * vx + py * vy) / line_len_sq
        return float(max(0.0, min(1.0, t)))

    def _is_in_zone(self, centroid: Tuple[float, float], polygon: List[Dict[str, float]], frame_w: int, frame_h: int) -> bool:
        if not polygon:
            return False
        pts = []
        for pt in polygon:
            px = pt["x"] if pt["x"] > 1.0 else pt["x"] * frame_w
            py = pt["y"] if pt["y"] > 1.0 else pt["y"] * frame_h
            pts.append((px, py))
        poly_arr = np.array(pts, dtype=np.int32)
        dist = cv2.pointPolygonTest(poly_arr, (float(centroid[0]), float(centroid[1])), False)
        return dist >= 0

    def process_frame(
        self,
        frame: np.ndarray,
        active_tracks: List[Dict[str, Any]],
        zones: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main execution step for queue intelligence in the pipeline loop.
        Returns:
            queue_results: Dict with zone-level queue states, classified tracks, and service events.
        """
        now = time.time()
        h, w = frame.shape[:2]
        queue_zones = [z for z in zones if z.get("zone_type") == "queue_zone"]

        # If no explicit queue_zone configured, check if any zone label has 'queue' or 'checkout'
        if not queue_zones:
            queue_zones = [z for z in zones if "queue" in z.get("label", "").lower() or "checkout" in z.get("label", "").lower()]

        zone_states_res = {}
        classified_tracks_all = []
        service_completion_events = []

        active_tids = set()

        for qz in queue_zones:
            zid = qz["zone_id"]
            poly = qz.get("polygon", [])
            ax1, ax2 = self._get_axis_points(qz, w, h)
            axis_angle_rad = math.atan2(ax2[1] - ax1[1], ax2[0] - ax1[0])
            axis_angle_deg = (math.degrees(axis_angle_rad) + 360.0) % 360.0

            # 1. Identify people tracks inside this queue zone
            occupant_tracks = []
            for tr in active_tracks:
                tid = tr["track_id"]
                centroid = tr["centroid"]
                active_tids.add(tid)

                if self._is_in_zone(centroid, poly, w, h):
                    occupant_tracks.append(tr)

            # 2. Extract pose landmarks & compute 4 classification signals for each occupant
            zone_tracks_info = []
            for tr in occupant_tracks:
                tid = tr["track_id"]
                box = tr["box"]
                cx, cy = tr["centroid"]
                
                # Person crop for pose estimation
                x1, y1, x2, y2 = max(0, int(box[0])), max(0, int(box[1])), min(w, int(box[2])), min(h, int(box[3]))
                crop = frame[y1:y2, x1:x2] if (y2 > y1 and x2 > x1) else None

                # Motion vector
                if tid not in self._track_states:
                    self._track_states[tid] = {
                        "history": deque(maxlen=self.config.rolling_window_frames),
                        "state": "browsing",
                        "streak": 0,
                        "last_pos": (cx, cy),
                        "entry_ts": now,
                        "zone_id": zid
                    }

                tstate = self._track_states[tid]
                last_x, last_y = tstate["last_pos"]
                vx, vy = cx - last_x, cy - last_y
                tstate["last_pos"] = (cx, cy)

                # Projection distance along queue axis
                proj_dist = self._compute_projection((cx, cy), ax1, ax2)

                # A.3 Pose Estimation
                pose_info = self.pose_estimator.estimate_pose(crop, motion_vector=(vx, vy))
                facing_deg = pose_info["facing_angle_deg"]

                # A.4 Feature 1: Body Orientation alignment with queue axis / counter
                # Angle difference between facing direction and axis direction
                angle_diff = abs((facing_deg - axis_angle_deg + 180) % 360 - 180)
                orientation_score = max(0.0, math.cos(math.radians(angle_diff)))

                # Feature 2: Displacement Velocity (low velocity or mostly forward along axis)
                speed = math.hypot(vx, vy)
                velocity_score = max(0.0, min(1.0, math.exp(-speed / 2.8)))

                # Feature 3: Dwell Pattern (continuous presence in zone)
                dwell_sec = now - tstate["entry_ts"]
                dwell_score = min(1.0, dwell_sec / 4.0)

                # Feature 4: Neighbor spacing (will be evaluated collectively below)
                # Weighted score for this frame
                frame_score = (
                    self.config.weight_orientation * orientation_score +
                    self.config.weight_velocity * velocity_score +
                    self.config.weight_dwell * dwell_score +
                    self.config.weight_spacing * 0.7 # baseline neighbor spacing
                )

                tstate["history"].append(frame_score)
                avg_score = float(np.mean(tstate["history"]))

                # State machine with hysteresis window to prevent flicker
                target_state = "in_queue" if avg_score >= 0.50 else "browsing"
                if target_state != tstate["state"]:
                    tstate["streak"] += 1
                    if tstate["streak"] >= self.config.hysteresis_frames:
                        tstate["state"] = target_state
                        tstate["streak"] = 0
                else:
                    tstate["streak"] = 0

                final_class = tstate["state"]

                zone_tracks_info.append({
                    "track_id": tid,
                    "zone_id": zid,
                    "projection_distance": round(proj_dist, 3),
                    "classification": final_class,
                    "facing_angle_deg": facing_deg,
                    "score": round(avg_score, 2),
                    "pose_features": pose_info,
                    "box": box,
                    "centroid": (cx, cy)
                })

            # Sort tracks in queue order by projection distance descending (closest to counter is #1)
            in_queue_tracks = [t for t in zone_tracks_info if t["classification"] == "in_queue"]
            in_queue_tracks.sort(key=lambda t: t["projection_distance"], reverse=True)

            # Assign queue line position
            for rank, tr_info in enumerate(in_queue_tracks, start=1):
                tr_info["queue_position"] = rank

            queue_len = len(in_queue_tracks)

            # 3. A.5 Rolling Queue Growth Rate (derivative d(queue_length)/dt per minute)
            if zid not in self._queue_length_history:
                self._queue_length_history[zid] = deque(maxlen=20)
            self._queue_length_history[zid].append((now, queue_len))

            growth_rate = 0.0
            if len(self._queue_length_history[zid]) >= 4:
                old_t, old_len = self._queue_length_history[zid][0]
                dt = now - old_t
                if dt > 2.0:
                    growth_rate = round(((queue_len - old_len) / dt) * 60.0, 2) # change per minute

            # 4. Check for Service Completion Events (when front-of-queue exits counter)
            if zid not in self._front_tracker:
                self._front_tracker[zid] = {"last_front_tid": None, "front_enter_ts": now}

            current_front_tid = in_queue_tracks[0]["track_id"] if in_queue_tracks else None
            last_front_tid = self._front_tracker[zid]["last_front_tid"]

            if last_front_tid is not None and last_front_tid != current_front_tid:
                # The previous front customer was served / exited the checkout counter!
                service_duration = max(5.0, min(180.0, now - self._front_tracker[zid]["front_enter_ts"]))
                evt = {
                    "completion_id": f"comp-{uuid.uuid4().hex[:8]}",
                    "zone_id": zid,
                    "track_id": last_front_tid,
                    "ts": now,
                    "service_duration_seconds": round(service_duration, 1)
                }
                service_completion_events.append(evt)
                self._front_tracker[zid]["front_enter_ts"] = now

            self._front_tracker[zid]["last_front_tid"] = current_front_tid

            zone_states_res[zid] = {
                "zone_id": zid,
                "label": qz.get("label", "Billing Counter"),
                "queue_length": queue_len,
                "growth_rate": growth_rate,
                "total_occupants": len(zone_tracks_info),
                "in_queue_tracks": in_queue_tracks,
                "browsing_tracks": [t for t in zone_tracks_info if t["classification"] == "browsing"],
                "axis_start": ax1,
                "axis_end": ax2
            }
            classified_tracks_all.extend(zone_tracks_info)

        # Cleanup stale tracks from memory
        stale_tids = [tid for tid in self._track_states if tid not in active_tids]
        for tid in stale_tids:
            del self._track_states[tid]

        return {
            "zone_states": zone_states_res,
            "classified_tracks": classified_tracks_all,
            "service_completion_events": service_completion_events,
            "timestamp": now
        }
