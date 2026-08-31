import time
import json
import logging
from collections import defaultdict
from fastapi import Request, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from backend.app.config import settings
from backend.app.database import get_db_connection

logger = logging.getLogger("retailiq.security")

API_KEY_NAME = "X-Admin-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

class RateLimiter:
    """
    In-memory sliding window rate limiter per client IP.
    """
    def __init__(self, requests_per_minute: int = 120):
        self.requests_per_minute = requests_per_minute
        self.window_sec = 60.0
        self._clients = defaultdict(list)

    def check_rate_limit(self, client_ip: str) -> bool:
        now = time.time()
        # Filter timestamps outside window
        timestamps = [ts for ts in self._clients[client_ip] if now - ts < self.window_sec]
        if len(timestamps) >= self.requests_per_minute:
            self._clients[client_ip] = timestamps
            return False
        timestamps.append(now)
        self._clients[client_ip] = timestamps
        return True

rate_limiter = RateLimiter(requests_per_minute=settings.security.rate_limit_per_minute)

async def verify_admin_api_key(api_key: str = Security(api_key_header)):
    """
    FastAPI dependency to protect administrative endpoints.
    In development or if API key is not set, allows requests through.
    """
    expected_key = settings.security.admin_api_key
    if not expected_key or settings.env == "development":
        return True
    
    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing Admin API Key (X-Admin-API-Key header required)."
        )
    return True

def record_audit_log(action: str, actor: str, resource: str = "", details: dict = None, ip: str = "127.0.0.1"):
    """Persist administrative actions in SQLite audit_logs table."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (action, actor, resource, details_json, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (action, actor, resource, json.dumps(details or {}), ip, time.time()))
        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to record audit log: {e}")
