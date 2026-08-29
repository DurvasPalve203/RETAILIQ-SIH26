import time
from fastapi import APIRouter
from typing import Dict, Any, List
from pydantic import BaseModel

from backend.app.sync.mqtt_sync import SyncService
from backend.app.database import get_db_connection

router = APIRouter(prefix="/sync", tags=["Cloud / MQTT Sync"])

sync_service = SyncService()

class BatchPushRequest(BaseModel):
    events: List[Dict[str, Any]]

@router.get("/status")
def get_sync_status():
    return sync_service.get_sync_status()

@router.post("/push")
def push_batch_sync(req: BatchPushRequest):
    """Fallback REST batch sync endpoint for structured telemetry."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.time()
    for evt in req.events:
        sync_service.enqueue_event("rest_batch", evt)
    return {"status": "success", "queued_records": len(req.events)}
