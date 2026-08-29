import sqlite3
import json
import time
import os
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.config import settings

DB_PATH = Path(settings.database.db_path)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_local = threading.local()

def get_db_connection() -> sqlite3.Connection:
    """Get a thread-local SQLite connection with WAL mode enabled for high concurrency."""
    if not hasattr(_local, "connection") or _local.connection is None:
        conn = sqlite3.connect(
            str(DB_PATH),
            timeout=30.0,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging for non-blocking concurrent reads and fast writes
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        _local.connection = conn
    return _local.connection

def init_db():
    """Initialize the SQLite database with all tables specified in RetailIQ spec."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Zones Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS zones (
        zone_id TEXT PRIMARY KEY,
        camera_id TEXT NOT NULL,
        polygon_json TEXT NOT NULL,
        zone_type TEXT NOT NULL, -- 'shelf' | 'entrance' | 'aisle' | 'staff'
        label TEXT NOT NULL,
        target_sku_id TEXT,
        baseline_image_path TEXT,
        expected_capacity INTEGER DEFAULT 10,
        created_at REAL NOT NULL
    );
    """)

    # 2. SKU Gallery Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sku_gallery (
        sku_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        price REAL DEFAULT 3.99,
        embedding_vector TEXT NOT NULL, -- JSON array of floats
        sample_count INTEGER DEFAULT 1,
        thumbnail_path TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    """)

    # 3. Stock Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_events (
        event_id TEXT PRIMARY KEY,
        zone_id TEXT NOT NULL,
        sku_id_nullable TEXT,
        type TEXT NOT NULL, -- 'stock_out' | 'restock' | 'depletion_warning'
        severity TEXT NOT NULL, -- 'low' | 'medium' | 'high'
        confidence REAL NOT NULL,
        ts_start REAL NOT NULL,
        ts_end REAL,
        duration_seconds REAL DEFAULT 0.0,
        estimated_lost_sales REAL DEFAULT 0.0,
        status TEXT DEFAULT 'open', -- 'open' | 'resolved'
        FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
    );
    """)

    # 4. Dwell Records Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwell_records (
        record_id TEXT PRIMARY KEY,
        track_id INTEGER NOT NULL,
        zone_id TEXT NOT NULL,
        entry_ts REAL NOT NULL,
        exit_ts REAL NOT NULL,
        dwell_seconds REAL NOT NULL,
        FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
    );
    """)

    # 5. Predictions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id TEXT PRIMARY KEY,
        zone_id TEXT NOT NULL,
        sku_id_nullable TEXT,
        eta_minutes REAL NOT NULL,
        confidence REAL NOT NULL,
        generated_at REAL NOT NULL,
        FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
    );
    """)

    # 6. Active Learning Review Queue Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_queue (
        item_id TEXT PRIMARY KEY,
        crop_ref TEXT NOT NULL, -- path or base64 image ref
        predicted_sku_id TEXT,
        confidence REAL NOT NULL,
        status TEXT NOT NULL, -- 'pending' | 'corrected' | 'dismissed'
        corrected_sku_id TEXT,
        corrected_by TEXT,
        embedding_vector TEXT,
        ts REAL NOT NULL
    );
    """)

    # 7. Offline Sync Queue Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offline_sync_queue (
        queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
        payload_json TEXT NOT NULL,
        topic TEXT NOT NULL,
        status TEXT DEFAULT 'pending', -- 'pending' | 'synced' | 'failed'
        retry_count INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        synced_at REAL
    );
    """)

    # 8. System Config Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at REAL NOT NULL
    );
    """)

    # 9. Queue Zones Table (FR-Q02)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS queue_zones (
        zone_id TEXT PRIMARY KEY,
        camera_id TEXT NOT NULL,
        polygon_json TEXT NOT NULL,
        axis_start_xy TEXT NOT NULL, -- JSON {x, y}
        axis_end_xy TEXT NOT NULL,   -- JSON {x, y}
        created_at REAL NOT NULL,
        FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
    );
    """)

    # 10. Queue Tracks Table (FR-Q03, FR-Q04)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS queue_tracks (
        record_id TEXT PRIMARY KEY,
        track_id INTEGER NOT NULL,
        zone_id TEXT NOT NULL,
        ts REAL NOT NULL,
        projection_distance REAL NOT NULL,
        classification TEXT NOT NULL, -- 'in_queue' | 'browsing'
        pose_features_json TEXT,
        FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
    );
    """)

    # 11. Queue State Table (FR-Q05)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS queue_state (
        state_id TEXT PRIMARY KEY,
        zone_id TEXT NOT NULL,
        ts REAL NOT NULL,
        queue_length INTEGER NOT NULL,
        growth_rate REAL NOT NULL,
        FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
    );
    """)

    # 12. Service Completions Table (FR-Q06)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS service_completions (
        completion_id TEXT PRIMARY KEY,
        zone_id TEXT NOT NULL,
        track_id INTEGER,
        ts REAL NOT NULL,
        service_duration_seconds REAL NOT NULL,
        FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
    );
    """)

    # 13. Queue Predictions Table (FR-Q06)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS queue_predictions (
        prediction_id TEXT PRIMARY KEY,
        zone_id TEXT NOT NULL,
        ts REAL NOT NULL,
        estimated_wait_seconds REAL NOT NULL,
        method TEXT NOT NULL, -- 'rule' | 'lstm'
        confidence REAL NOT NULL,
        FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
    );
    """)

    # 14. Multi-Level Alerts Table (Section D)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY,
        source_module TEXT NOT NULL, -- 'shelf' | 'queue' | 'system'
        zone_id TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        severity TEXT NOT NULL, -- 'CRITICAL' | 'HIGH' | 'LOW'
        state TEXT NOT NULL,    -- 'NEW' | 'ACKNOWLEDGED' | 'ESCALATED' | 'RESOLVED'
        created_at REAL NOT NULL,
        acknowledged_at REAL,
        resolved_at REAL,
        escalate_count INTEGER DEFAULT 0,
        details_json TEXT
    );
    """)

    # 15. Alert Deliveries Table (Section D.3)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_deliveries (
        delivery_id TEXT PRIMARY KEY,
        alert_id TEXT NOT NULL,
        channel TEXT NOT NULL, -- 'dashboard' | 'mqtt' | 'buzzer' | 'led' | 'sms'
        status TEXT NOT NULL,  -- 'sent' | 'failed' | 'suppressed'
        sent_at REAL NOT NULL,
        payload_json TEXT,
        FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
    );
    """)

    # Extend zones table if column axis_start_xy missing
    try:
        cursor.execute("ALTER TABLE zones ADD COLUMN axis_start_xy TEXT;")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE zones ADD COLUMN axis_end_xy TEXT;")
    except sqlite3.OperationalError:
        pass

    conn.commit()

# Run initialization upon module import
init_db()
