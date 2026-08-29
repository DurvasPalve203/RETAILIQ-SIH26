import sys
import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import init_db
from backend.app.pipeline_coordinator import PipelineCoordinator
from backend.app.api.routes_zones import router as zones_router
from backend.app.api.routes_sku import router as sku_router
from backend.app.api.routes_events import router as events_router, manager as ws_manager
from backend.app.api.routes_dashboard import router as dashboard_router
from backend.app.api.routes_review import router as review_router
from backend.app.api.routes_sync import router as sync_router
from backend.app.api.routes_video import router as video_router, set_pipeline_instance
from backend.app.api.routes_health import router as health_router
from demo_seed import seed_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("retailiq.main")

# Global pipeline instance
pipeline = PipelineCoordinator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing RetailIQ Edge System...")
    init_db()
    seed_database()
    
    set_pipeline_instance(pipeline)
    
    # Setup async loop broadcaster from thread
    loop = asyncio.get_running_loop()
    def broadcast_sync(state):
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(state), loop)

    pipeline.set_websocket_broadcaster(broadcast_sync)
    pipeline.start()
    logger.info("RetailIQ Edge System running successfully.")

    yield

    # Shutdown
    logger.info("Shutting down RetailIQ Edge System...")
    pipeline.stop()

app = FastAPI(
    title="RetailIQ Edge API",
    description="Edge-Native Retail Computer Vision & Predictive Shelf Intelligence System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local frontend and LAN edge access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.get("/")
def root():
    return {
        "system": "RetailIQ Edge Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "status": "online"
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
