import sys
import time
import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.database import init_db, get_db_connection
from backend.app.pipeline_coordinator import PipelineCoordinator
from backend.app.api.routes_zones import router as zones_router, set_pipeline_instance_zones
from backend.app.api.routes_sku import router as sku_router
from backend.app.api.routes_events import router as events_router, manager as ws_manager
from backend.app.api.routes_dashboard import router as dashboard_router
from backend.app.api.routes_review import router as review_router
from backend.app.api.routes_sync import router as sync_router
from backend.app.api.routes_video import router as video_router, set_pipeline_instance
from backend.app.api.routes_health import router as health_router, set_pipeline_instance_health
from backend.app.api.routes_queue import router as queue_router, set_pipeline_instance_queue
from backend.app.api.routes_alerts import router as alerts_router, set_alert_manager_instance
from backend.app.services.security_service import rate_limiter
from demo_seed import seed_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("retailiq.main")

# Global pipeline instance
pipeline = PipelineCoordinator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation & initialization
    logger.info(f"Initializing RetailIQ Edge System (Profile: {settings.env})...")
    init_db()
    
    # Check if database needs initial seeding (only on empty DB or if seed_on_startup is explicitly true)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM zones;")
        zone_count = cursor.fetchone()["count"]
        if zone_count == 0 or settings.database.seed_on_startup:
            logger.info("Seeding database with baseline calibration schemas...")
            seed_database()
    except Exception as e:
        logger.warning(f"Database seed check encountered: {e}")
    
    set_pipeline_instance(pipeline)
    set_pipeline_instance_zones(pipeline)
    set_pipeline_instance_queue(pipeline)
    set_pipeline_instance_health(pipeline)
    set_alert_manager_instance(pipeline.alert_manager)
    
    # Setup async loop broadcaster from coordinator thread
    loop = asyncio.get_running_loop()
    def broadcast_sync(state):
        try:
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(state), loop)
        except Exception:
            pass

    pipeline.set_websocket_broadcaster(broadcast_sync)
    pipeline.start()
    logger.info(f"RetailIQ Edge System running successfully on {settings.edge_device.store_name}.")

    yield

    # Safe Shutdown
    logger.info("Gracefully shutting down RetailIQ Edge System...")
    pipeline.stop()
    logger.info("RetailIQ Edge System stopped cleanly.")

app = FastAPI(
    title="RetailIQ Edge API",
    description="Edge-Native Retail Computer Vision & Predictive Shelf Intelligence System",
    version="1.0.0",
    lifespan=lifespan
)

# Rate Limiting & Access Audit Middleware
@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # Exclude video feeds and websockets from rate limiting
    path = request.url.path
    if not path.startswith("/video/feed") and not path.startswith("/events"):
        if not rate_limiter.check_rate_limit(client_ip):
            return Response(
                content='{"detail":"Rate limit exceeded. Try again in 60s."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
    
    t0 = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - t0) * 1000, 2)
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response

# CORS configuration
allowed_origins = settings.security.cors_origins or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(zones_router)
app.include_router(sku_router)
app.include_router(events_router)
app.include_router(dashboard_router)
app.include_router(review_router)
app.include_router(sync_router)
app.include_router(video_router)
app.include_router(health_router)
app.include_router(queue_router)
app.include_router(alerts_router)

@app.get("/")
def root():
    return {
        "system": "RetailIQ Edge Engine",
        "version": "1.0.0",
        "env": settings.env,
        "store": settings.edge_device.store_name,
        "docs": "/docs",
        "health": "/health",
        "readiness": "/health/ready",
        "liveness": "/health/live",
        "status": "online"
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
