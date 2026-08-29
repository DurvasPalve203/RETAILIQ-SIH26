import time
from fastapi import APIRouter
from typing import List, Dict, Any, Optional

from backend.app.database import get_db_connection
from backend.app.schemas import QueueStateResponse, QueuePredictionResponse

router = APIRouter(prefix="/queue", tags=["Queue Intelligence & Wait-Time Prediction"])

pipeline_instance = None

def set_pipeline_instance_queue(p):
    global pipeline_instance
    pipeline_instance = p

@router.get("/state")
def get_current_queue_state():
    """Get real-time queue states, track counts, and line rosters across all checkout zones."""
    if not pipeline_instance:
        return {"queue_zones": {}}
    return {
        "timestamp": time.time(),
        "queue_states": pipeline_instance.latest_queue_states,
        "predictions": pipeline_instance.latest_queue_predictions
    }

@router.get("/predictions", response_model=List[QueuePredictionResponse])
def get_queue_predictions():
    """Get active wait-time predictions for checkout counters."""
    if not pipeline_instance:
        return []
    
    preds = pipeline_instance.latest_queue_predictions
    res = []
    for p in preds:
        res.append(QueuePredictionResponse(
            prediction_id=p["prediction_id"],
            zone_id=p["zone_id"],
            zone_label=p.get("zone_label"),
            estimated_wait_seconds=p["estimated_wait_seconds"],
            wait_minutes_formatted=p["wait_minutes_formatted"],
            average_service_time_sec=p["average_service_time_sec"],
            method=p.get("method", "rule"),
            confidence=p.get("confidence", 0.85),
            generated_at=p["generated_at"]
        ))
    return res

@router.get("/history")
def get_service_history(limit: int = 30):
    """Retrieve recent empirical checkout service duration history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.completion_id, s.zone_id, z.label as zone_label, s.track_id, s.ts, s.service_duration_seconds
        FROM service_completions s
        LEFT JOIN zones z ON s.zone_id = z.zone_id
        ORDER BY s.ts DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    return [dict(r) for r in rows]
