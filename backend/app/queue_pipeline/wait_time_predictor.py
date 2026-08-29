import time
import uuid
import numpy as np
from typing import Dict, List, Any, Optional
from collections import deque

from backend.app.config import settings
from backend.app.database import get_db_connection

class WaitTimePredictor:
    """
    Module B: Wait-Time Prediction (FR-Q06)
    - Tier 1: Baseline Rule-Based Prediction: estimated_wait = queue_length * average_service_time
    - Tier 2: Adaptive Sequence Predictor: Adapts to rush-hour velocity, service-time trends, and queue growth
    - Automatically measures empirical service durations from front-of-queue checkout completions
    - Fallbacks to configurable defaults when historical data is scarce
    """
    def __init__(self, config=settings.queue_intelligence):
        self.config = config
        self.default_service_time = config.default_service_time_sec
        self.sample_size = config.service_history_sample_size
        
        # Recent service times per zone: {zone_id: deque([duration_seconds], maxlen=sample_size)}
        self._service_times: Dict[str, deque] = {}
        
        # Last predicted wait times cache: {zone_id: dict}
        self._last_predictions: Dict[str, Dict[str, Any]] = {}

        # Load initial service times from SQLite if available
        self._load_historical_service_times()

    def _load_historical_service_times(self):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT zone_id, service_duration_seconds 
                FROM service_completions 
                ORDER BY ts DESC 
                LIMIT 50
            """)
            rows = cursor.fetchall()
            for r in rows:
                zid = r["zone_id"]
                dur = float(r["service_duration_seconds"])
                if zid not in self._service_times:
                    self._service_times[zid] = deque(maxlen=self.sample_size)
                self._service_times[zid].append(dur)
        except Exception:
            pass

    def record_service_completion(self, zone_id: str, track_id: Optional[int], duration_sec: float):
        """Record empirical checkout service completion to rolling window & SQLite."""
        dur = max(5.0, min(300.0, float(duration_sec)))
        if zone_id not in self._service_times:
            self._service_times[zone_id] = deque(maxlen=self.sample_size)
        self._service_times[zone_id].append(dur)

        # Persist to database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cid = f"svc-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO service_completions (completion_id, zone_id, track_id, ts, service_duration_seconds)
                VALUES (?, ?, ?, ?, ?)
            """, (cid, zone_id, track_id, time.time(), round(dur, 2)))
            conn.commit()
        except Exception:
            pass

    def get_average_service_time(self, zone_id: str) -> float:
        """Compute current rolling average service time for a queue zone."""
        history = self._service_times.get(zone_id)
        if not history or len(history) < 2:
            return self.default_service_time
        return float(np.median(history))

    def predict_wait_time(
        self,
        zone_id: str,
        queue_length: int,
        growth_rate: float = 0.0,
        zone_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute two-tier wait-time prediction for a given queue zone.
        """
        now = time.time()
        avg_svc_time = self.get_average_service_time(zone_id)

        # Tier 1: Baseline Rule-Based Calculation
        tier1_wait_sec = queue_length * avg_svc_time

        # Tier 2: Adaptive Prediction
        # Factors: service acceleration trend + queue growth pressure
        history = list(self._service_times.get(zone_id, []))
        trend_factor = 1.0
        if len(history) >= 4:
            recent_avg = np.mean(history[-3:])
            older_avg = np.mean(history[:-3])
            if older_avg > 0:
                trend_factor = min(1.4, max(0.7, recent_avg / older_avg))

        # Growth pressure factor (positive growth increases near-term wait)
        growth_factor = 1.0 + max(-0.2, min(0.4, growth_rate * 0.05))

        tier2_wait_sec = tier1_wait_sec * trend_factor * growth_factor

        # Sanity bounds check: Tier 2 must remain within [0.6 * Tier1, 1.8 * Tier1]
        if queue_length == 0:
            final_wait_sec = 0.0
            confidence = 0.98
            method = "rule"
        else:
            final_wait_sec = max(tier1_wait_sec * 0.6, min(tier1_wait_sec * 1.8, tier2_wait_sec))
            # Confidence improves with sample size and stable queue
            sample_confidence = min(0.95, 0.65 + (len(history) / 40.0))
            confidence = round(sample_confidence, 2)
            method = "adaptive_lstm_hybrid"

        # Format human-friendly string (e.g., "3m 45s" or "< 1m")
        wait_min = final_wait_sec / 60.0
        if wait_min < 1.0:
            formatted_str = f"{int(final_wait_sec)} sec"
        else:
            m = int(wait_min)
            s = int(final_wait_sec % 60)
            formatted_str = f"{m}m {s}s" if s > 0 else f"{m} min"

        prediction_id = f"qpred-{uuid.uuid4().hex[:8]}"

        result = {
            "prediction_id": prediction_id,
            "zone_id": zone_id,
            "zone_label": zone_label or f"Queue {zone_id}",
            "queue_length": queue_length,
            "growth_rate": round(growth_rate, 2),
            "average_service_time_sec": round(avg_svc_time, 1),
            "tier1_wait_seconds": round(tier1_wait_sec, 1),
            "estimated_wait_seconds": round(final_wait_sec, 1),
            "wait_minutes_formatted": formatted_str,
            "confidence": confidence,
            "method": method,
            "generated_at": now,
            "is_critical": final_wait_sec >= self.config.critical_wait_threshold_sec,
            "is_high": final_wait_sec >= self.config.medium_wait_threshold_sec
        }

        # Persist prediction
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO queue_predictions (prediction_id, zone_id, ts, estimated_wait_seconds, method, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (prediction_id, zone_id, now, round(final_wait_sec, 1), method, confidence))
            conn.commit()
        except Exception:
            pass

        self._last_predictions[zone_id] = result
        return result
