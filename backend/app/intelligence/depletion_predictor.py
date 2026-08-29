import time
import uuid
import numpy as np
from collections import deque
from typing import Dict, List, Optional, Any, Tuple
from backend.app.config import settings
from backend.app.database import get_db_connection

class DepletionPredictor:
    """
    Module 5.1: Depletion-Rate & Time-To-Stock-Out Prediction
    - Deliberately explainable rolling linear regression / exponential smoothing
    - Combines occupancy velocity + zone footfall intensity + restock cadence
    - Emits rolling predicted_stockout records: {zone_id, eta_minutes, confidence}
    """
    def __init__(self, config=settings.intelligence_and_prediction):
        self.config = config
        self.lookback_minutes = config.eta_prediction_lookback_minutes
        self.warning_eta_threshold = config.stockout_warning_eta_minutes
        
        # Rolling occupancy history per zone: deque of (timestamp, occupancy_score)
        self._history: Dict[str, deque] = {}
        # Footfall intensity per zone: deque of timestamps of visits
        self._zone_footfalls: Dict[str, deque] = {}
        # Last predicted ETA cache
        self._last_predictions: Dict[str, Dict[str, Any]] = {}

    def record_occupancy_point(self, zone_id: str, occupancy_score: float, timestamp: Optional[float] = None):
        ts = timestamp or time.time()
        if zone_id not in self._history:
            self._history[zone_id] = deque(maxlen=60) # keep recent 60 evaluation frames
        self._history[zone_id].append((ts, occupancy_score))

    def record_zone_footfall(self, zone_id: str, timestamp: Optional[float] = None):
        ts = timestamp or time.time()
        if zone_id not in self._zone_footfalls:
            self._zone_footfalls[zone_id] = deque(maxlen=100)
        self._zone_footfalls[zone_id].append(ts)

    def predict_eta(self, zone_id: str, current_occupancy: float, target_sku_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Calculate depletion slope (dOcc/dt) and project forward to calculate ETA in minutes
        until occupancy crosses 0.15 (empty threshold).
        """
        now = time.time()
        self.record_occupancy_point(zone_id, current_occupancy, now)

        history = self._history.get(zone_id)
        if not history or len(history) < 5:
            return None

        # Extract timestamps and scores
        times = np.array([p[0] for p in history])
        scores = np.array([p[1] for p in history])

        # Normalize time to minutes relative to start of window
        t_rel_min = (times - times[0]) / 60.0
        
        # Fit 1D polynomial (linear regression: score = slope * t + intercept)
        if np.max(t_rel_min) - np.min(t_rel_min) < 0.05:
            # Need at least a few seconds of data
            return None

        slope, intercept = np.polyfit(t_rel_min, scores, 1) # slope in d(occupancy)/minute

        # Calculate footfall boost factor
        recent_footfalls = [t for t in self._zone_footfalls.get(zone_id, []) if (now - t) < 300] # last 5 min
        footfall_rate_per_min = len(recent_footfalls) / 5.0
        
        # If footfall is high, accelerate depletion slope slightly if already negative
        adjusted_slope = slope
        if slope < -0.001 and footfall_rate_per_min > 0.5:
            adjusted_slope *= (1.0 + min(1.0, footfall_rate_per_min * 0.15))

        # Check if depleting
        empty_thresh = 0.15
        if adjusted_slope < -0.002 and current_occupancy > empty_thresh:
            # Time to empty = (empty_threshold - current_occupancy) / adjusted_slope
            eta_minutes = float((empty_thresh - current_occupancy) / adjusted_slope)
            eta_minutes = max(1.0, round(eta_minutes, 1))

            # Confidence based on linear fit correlation (R^2)
            fitted = slope * t_rel_min + intercept
            ss_tot = np.sum((scores - np.mean(scores)) ** 2)
            ss_res = np.sum((scores - fitted) ** 2)
            r2 = 1.0 - (ss_res / (ss_tot + 1e-6))
            confidence = float(np.clip(r2, 0.45, 0.96))

            pred_record = {
                "prediction_id": f"pred-{uuid.uuid4().hex[:8]}",
                "zone_id": zone_id,
                "sku_id_nullable": target_sku_id,
                "eta_minutes": eta_minutes,
                "confidence": round(confidence, 2),
                "generated_at": now,
                "depletion_rate_per_hour": round(abs(adjusted_slope) * 60.0 * 100, 1) # % per hour
            }

            self._last_predictions[zone_id] = pred_record

            # Persist to database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO predictions (prediction_id, zone_id, sku_id_nullable, eta_minutes, confidence, generated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (pred_record["prediction_id"], zone_id, target_sku_id, eta_minutes, confidence, now))
            conn.commit()

            return pred_record
        else:
            # Steady or recovering
            self._last_predictions.pop(zone_id, None)
            return None

    def get_latest_prediction(self, zone_id: str) -> Optional[Dict[str, Any]]:
        return self._last_predictions.get(zone_id)
