import time
import cv2
import numpy as np
from collections import deque
from typing import Dict, List, Optional, Any, Tuple
from skimage.metrics import structural_similarity as ssim

from backend.app.config import settings
from backend.app.database import get_db_connection

class ShelfOccupancyEngine:
    """
    Module 3.3: Dual-Signal Gap / Occupancy (Stock-Out) Detection Engine
    - Combines reference-image differencing (SSIM) + detection density
    - Confidence-weighted rolling window smoothing
    - Emits stock_out_event with granular severity (low/medium/high)
    - Emits restock_event when occupancy recovers
    - Handles staff cooldown suppression & camera occlusion suppression
    """
    def __init__(self, config=settings.occupancy_and_gap):
        self.config = config
        self.weight_ssim = config.weight_ssim
        self.weight_density = config.weight_detection_density
        self.window_size = config.rolling_window_frames
        
        # State tracking per zone
        self._occupancy_windows: Dict[str, deque] = {}
        self._zone_baseline_images: Dict[str, np.ndarray] = {}
        self._zone_baseline_capacities: Dict[str, int] = {}
        self._zone_states: Dict[str, Dict[str, Any]] = {}
        self._last_staff_presence: Dict[str, float] = {}

    def set_zone_baseline(self, zone_id: str, baseline_frame: np.ndarray, expected_capacity: int = 10):
        """Register or update reference full-shelf image for a zone."""
        self._zone_baseline_images[zone_id] = baseline_frame
        self._zone_baseline_capacities[zone_id] = max(1, expected_capacity)

    def record_staff_presence(self, zone_id: str):
        """Record staff activity in zone to activate cooldown suppression."""
        self._last_staff_presence[zone_id] = time.time()

    def is_in_staff_cooldown(self, zone_id: str) -> bool:
        """Check if zone is currently in cooldown window after staff interaction."""
        last_time = self._last_staff_presence.get(zone_id, 0.0)
        return (time.time() - last_time) < self.config.staff_cooldown_duration_sec

    def _compute_ssim_signal(self, current_crop: np.ndarray, baseline_crop: np.ndarray) -> float:
        """Compute structural similarity score between current shelf crop and baseline full shelf."""
        if current_crop is None or baseline_crop is None or current_crop.size == 0 or baseline_crop.size == 0:
            return 1.0

        h, w = baseline_crop.shape[:2]
        resized_curr = cv2.resize(current_crop, (w, h))

        gray_curr = cv2.cvtColor(resized_curr, cv2.COLOR_BGR2GRAY)
        gray_base = cv2.cvtColor(baseline_crop, cv2.COLOR_BGR2GRAY)

        # Structural Similarity Index
        score, _ = ssim(gray_curr, gray_base, full=True)
        # SSIM is in [-1, 1], normalize to [0, 1]
        return float(np.clip((score + 1.0) / 2.0, 0.0, 1.0))

    def evaluate_zone(
        self,
        zone_id: str,
        current_zone_crop: Optional[np.ndarray],
        detected_products_count: int,
        detected_gaps_count: int,
        is_camera_occluded: bool = False,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates occupancy score for a single zone, applies smoothing, checks thresholds,
        and determines if a stock_out_event or restock_event should be emitted.
        """
        now = timestamp if timestamp is not None else time.time()
        capacity = self._zone_baseline_capacities.get(zone_id, 10)
        
        # 1. Detection Density Signal (presence count / capacity)
        # Note: unknown products also count toward occupancy
        density_signal = min(1.0, max(0.0, detected_products_count / capacity))

        # 2. Reference Differencing Signal (SSIM vs baseline)
        baseline_crop = self._zone_baseline_images.get(zone_id)
        if baseline_crop is not None and current_zone_crop is not None:
            ssim_signal = self._compute_ssim_signal(current_zone_crop, baseline_crop)
        else:
            ssim_signal = density_signal

        # 3. Dual-Signal Confidence Weighted Combination
        raw_occupancy = (self.weight_density * density_signal) + (self.weight_ssim * ssim_signal)
        raw_occupancy = float(np.clip(raw_occupancy, 0.0, 1.0))

        # 4. Rolling Window Moving Average Smoothing
        if zone_id not in self._occupancy_windows:
            self._occupancy_windows[zone_id] = deque(maxlen=self.window_size)
            self._zone_states[zone_id] = {
                "status": "normal",
                "active_event_id": None,
                "below_thresh_start": None,
                "above_thresh_start": None,
                "current_severity": None,
                "occupancy_score": 1.0,
                "item_count": detected_products_count
            }

        self._occupancy_windows[zone_id].append(raw_occupancy)
        smoothed_occupancy = float(np.mean(self._occupancy_windows[zone_id]))

        # Retrieve zone state
        state = self._zone_states[zone_id]
        state["occupancy_score"] = round(smoothed_occupancy, 3)
        state["item_count"] = detected_products_count

        # Edge Case Checks: Occlusion and Staff Cooldown
        in_cooldown = self.is_in_staff_cooldown(zone_id)
        suppress_alerts = is_camera_occluded or in_cooldown

        event_to_emit = None

        # Determine Severity Level based on configured thresholds
        severity = None
        if smoothed_occupancy < self.config.depletion_threshold_high:
            severity = "high" # > 70% empty
        elif smoothed_occupancy < self.config.depletion_threshold_medium:
            severity = "medium" # > 45% empty
        elif smoothed_occupancy < self.config.depletion_threshold_low:
            severity = "low" # > 25% empty

        # State Machine Transitions
        if severity is not None and not suppress_alerts:
            # Below depletion threshold
            if state["below_thresh_start"] is None:
                state["below_thresh_start"] = now
            
            sustained_duration = now - state["below_thresh_start"]

            # If sustained gap over duration threshold -> Trigger stock_out_event
            if sustained_duration >= self.config.sustained_gap_duration_sec:
                if state["status"] != "depleted" or state["current_severity"] != severity:
                    event_id = f"evt-out-{zone_id}-{int(now)}" if state["active_event_id"] is None else state["active_event_id"]
                    event_to_emit = {
                        "event_id": event_id,
                        "zone_id": zone_id,
                        "type": "stock_out",
                        "severity": severity,
                        "confidence": round(1.0 - smoothed_occupancy, 2),
                        "ts_start": now if state["active_event_id"] is None else state.get("event_start", now),
                        "status": "open",
                        "reason": f"Sustained gap ({int((1 - smoothed_occupancy)*100)}% empty)"
                    }
                    state["status"] = "depleted"
                    state["active_event_id"] = event_id
                    state["event_start"] = event_to_emit["ts_start"]
                    state["current_severity"] = severity
                    state["above_thresh_start"] = None
        else:
            state["below_thresh_start"] = None

        # Restock Check: If previously in stock_out and now recovered above restock threshold
        if smoothed_occupancy >= self.config.restock_recovery_threshold:
            if state["status"] == "depleted" and state["active_event_id"]:
                if state["above_thresh_start"] is None:
                    state["above_thresh_start"] = now
                
                # If restock sustained for at least 1.5 seconds
                if now - state["above_thresh_start"] >= 1.5:
                    duration = now - state.get("event_start", now)
                    event_to_emit = {
                        "event_id": f"evt-res-{zone_id}-{int(now)}",
                        "zone_id": zone_id,
                        "type": "restock",
                        "severity": "info",
                        "confidence": round(smoothed_occupancy, 2),
                        "ts_start": state.get("event_start", now),
                        "ts_end": now,
                        "duration_seconds": round(duration, 1),
                        "closed_event_id": state["active_event_id"],
                        "status": "resolved",
                        "reason": "Restock detected: occupancy recovered"
                    }
                    state["status"] = "normal"
                    state["active_event_id"] = None
                    state["current_severity"] = None
                    state["above_thresh_start"] = None
            else:
                state["above_thresh_start"] = None

        return {
            "zone_id": zone_id,
            "occupancy_score": state["occupancy_score"],
            "item_count": detected_products_count,
            "status": state["status"],
            "severity": state["current_severity"],
            "suppressed": suppress_alerts,
            "in_staff_cooldown": in_cooldown,
            "is_occluded": is_camera_occluded,
            "event": event_to_emit
        }
