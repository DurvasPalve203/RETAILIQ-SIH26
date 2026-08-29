import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Set

from backend.app.database import get_db_connection

logger = logging.getLogger("retailiq.events")
router = APIRouter(prefix="/events", tags=["Live Events Stream"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        if not self.active_connections:
            return
        dead_sockets = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead_sockets.add(conn)
        
        for dead in dead_sockets:
            self.active_connections.discard(dead)

manager = ConnectionManager()

@router.websocket("/live")
async def websocket_live_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep socket alive and accept ping/commands
            data = await websocket.receive_text()
            # Client can send ping or manual restock commands
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)

@router.get("/recent")
def get_recent_events(limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.event_id, e.zone_id, z.label as zone_label, e.sku_id_nullable, s.name as sku_name,
               e.type, e.severity, e.confidence, e.ts_start, e.ts_end, e.duration_seconds, e.status
        FROM stock_events e
        LEFT JOIN zones z ON e.zone_id = z.zone_id
        LEFT JOIN sku_gallery s ON e.sku_id_nullable = s.sku_id
        ORDER BY e.ts_start DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    return [dict(r) for r in rows]
