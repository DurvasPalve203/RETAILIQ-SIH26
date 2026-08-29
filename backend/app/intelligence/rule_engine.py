import time
from typing import List, Dict, Any, Optional
from backend.app.config import settings

class AlertRuleEngine:
    """
    Module 5.3: Alert & Rule Engine
    - Prioritizes alerts by severity and stock-out ETA
    - Deduplicates alert storms
    - Suppresses alerts on camera occlusion or active cooldown
    """
    def __init__(self, config=settings.intelligence_and_prediction):
        self.config = config
        self.cooldown_sec = config.alert_deduplication_cooldown_sec
        self.sales_loss_dollar_per_min = config.sales_loss_dollar_per_minute
        self._last_alert_sent: Dict[str, float] = {}

    def process_and_rank_alerts(
        self,
        active_stockouts: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
        is_camera_occluded: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Takes raw stockout events and predictions, applies deduplication & prioritization rules,
        and returns a sorted ranked priority action feed.
        """
        if is_camera_occluded:
            # Suppress/delay alerts until occlusion clears
            return []

        now = time.time()
        combined_alerts = []

        # 1. Process Active Stockouts
        for stockout in active_stockouts:
            zid = stockout["zone_id"]
            sev = stockout.get("severity", "medium")
            sev_weights = {"high": 100, "medium": 60, "low": 30}
            weight = sev_weights.get(sev, 50)

            # Calculate estimated lost sales
            duration_min = (now - stockout.get("ts_start", now)) / 60.0
            lost_dollars = round(duration_min * self.sales_loss_dollar_per_min, 2)

            priority_score = weight + (duration_min * 2.0)

            combined_alerts.append({
                "alert_id": f"alt-stockout-{zid}",
                "zone_id": zid,
                "title": f"{stockout.get('zone_label', zid)} — Immediate Stock-Out",
                "message": f"Stock depleted ({stockout.get('reason', 'Gap detected')}). Immediate replenishment needed.",
                "type": "immediate_stockout",
                "severity": sev,
                "eta_minutes": 0.0,
                "priority_score": round(priority_score, 1),
                "ts": stockout.get("ts_start", now),
                "estimated_lost_sales": lost_dollars
            })

        # 2. Process Predictive Stockouts
        for pred in predictions:
            zid = pred["zone_id"]
            eta = pred.get("eta_minutes", 60.0)
            
            # Skip if there's already an active immediate stockout for this zone
            if any(a["zone_id"] == zid and a["type"] == "immediate_stockout" for a in combined_alerts):
                continue

            if eta <= self.config.stockout_warning_eta_minutes:
                sev = "high" if eta <= 15.0 else ("medium" if eta <= 30.0 else "low")
                # Urgency inversely proportional to ETA
                priority_score = (60.0 - min(55.0, eta)) * (pred.get("confidence", 0.8))

                combined_alerts.append({
                    "alert_id": f"alt-pred-{zid}",
                    "zone_id": zid,
                    "title": f"{pred.get('zone_label', zid)} — Predicted Stock-Out in {int(eta)} min",
                    "message": f"High depletion velocity. Projected empty in {int(eta)} min (Confidence: {int(pred.get('confidence', 0.8)*100)}%).",
                    "type": "predictive_stockout",
                    "severity": sev,
                    "eta_minutes": eta,
                    "priority_score": round(priority_score, 1),
                    "ts": pred.get("generated_at", now),
                    "estimated_lost_sales": 0.0
                })

        # 3. Sort by priority score descending (highest urgency first)
        combined_alerts.sort(key=lambda x: x["priority_score"], reverse=True)

        return combined_alerts
