import time
from typing import List, Dict, Any
from backend.app.database import get_db_connection

class MerchandisingInsightsEngine:
    """
    Module 5.2: Footfall x Shelf Depletion Correlation Engine
    Correlates footfall/dwell time with shelf depletion rates to classify zones into a 2x2 merchandising matrix.
    """
    def generate_insights(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Retrieve all configured shelf zones
        cursor.execute("SELECT zone_id, label, zone_type, target_sku_id, expected_capacity FROM zones WHERE zone_type = 'shelf'")
        zones = cursor.fetchall()
        if not zones:
            return []

        now = time.time()
        one_day_ago = now - 86400.0

        insights = []

        for z in zones:
            zid = z["zone_id"]
            label = z["label"]
            target_sku = z["target_sku_id"]

            # Aggregate footfall visits & dwell time in last 24h
            cursor.execute("""
                SELECT COUNT(*) as visit_count, COALESCE(AVG(dwell_seconds), 0.0) as avg_dwell
                FROM dwell_records
                WHERE zone_id = ? AND entry_ts >= ?
            """, (zid, one_day_ago))
            dwell_data = cursor.fetchone()
            visits = dwell_data["visit_count"] if dwell_data else 0
            avg_dwell = round(dwell_data["avg_dwell"], 1) if dwell_data else 0.0

            # Aggregate stock events / depletions
            cursor.execute("""
                SELECT COUNT(*) as stockout_count, COALESCE(SUM(duration_seconds), 0.0) as total_out_sec
                FROM stock_events
                WHERE zone_id = ? AND ts_start >= ?
            """, (zid, one_day_ago))
            stock_data = cursor.fetchone()
            stockouts = stock_data["stockout_count"] if stock_data else 0

            # Calculate depletion index (simulated / historical normalized rate)
            # e.g., base hourly depletion rate
            depletion_rate_pct = min(100.0, max(5.0, (stockouts * 25.0) + (visits * 2.2)))

            # Classification into 2x2 Matrix
            # Thresholds: Traffic high if visits >= 8; Depletion high if depletion_rate_pct >= 35%
            is_high_traffic = visits >= 8
            is_high_depletion = depletion_rate_pct >= 35.0

            if is_high_traffic and is_high_depletion:
                classification = "high_traffic_high_depletion"
                tag = "Healthy Fast-Mover"
                recommendation = "Optimal velocity. Maintain automated replenishment alerts and ensure backroom safety stock."
            elif is_high_traffic and not is_high_depletion:
                classification = "high_traffic_low_depletion"
                tag = "Placement/Price Friction"
                recommendation = "High shopper dwell but low purchase conversion. Check product pricing, unappealing packaging, or misplaced tag."
            elif not is_high_traffic and not is_high_depletion:
                classification = "low_traffic_low_depletion"
                tag = "Deprioritize / Dead Stock"
                recommendation = "Low engagement and low sales velocity. Consider repositioning to eye level or bundling with high-traffic anchors."
            else:
                classification = "low_traffic_high_depletion"
                tag = "Investigate Shrink / Theft"
                recommendation = "High inventory drop without corresponding customer footfall. Flag for loss prevention review (potential shrinkage or unrecorded transfers)."

            insights.append({
                "zone_id": zid,
                "label": label,
                "target_sku_id": target_sku,
                "footfall_count": visits,
                "avg_dwell_seconds": avg_dwell,
                "depletion_rate_pct_per_hour": round(depletion_rate_pct, 1),
                "classification": classification,
                "tag": tag,
                "action_recommendation": recommendation
            })

        return insights
