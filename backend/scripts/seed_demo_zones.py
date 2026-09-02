import sqlite3
import json
import os
import time
from pathlib import Path

def seed_demo_zones():
    db_path = Path(__file__).resolve().parent.parent / "data" / "retailiq.db"
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    # Tight corridor polygon (x: 0.65 to 0.90)
    poly = [
        {"x": 0.65, "y": 0.30},
        {"x": 0.90, "y": 0.30},
        {"x": 0.90, "y": 0.95},
        {"x": 0.65, "y": 0.95}
    ]
    
    # Axis points towards the counter (Y=0.35)
    axis_start = {"x": 0.77, "y": 0.90}
    axis_end = {"x": 0.77, "y": 0.35}
    
    now_ts = time.time()
    
    # We use INSERT OR REPLACE to ensure the zone_type and label are correctly enforced
    # even if the database is reset.
    c.execute("""
        INSERT OR REPLACE INTO zones (
            zone_id, camera_id, zone_type, label, polygon_json, axis_start_xy, axis_end_xy, created_at
        ) VALUES (
            'zone-queue-01', 
            'cam_01', 
            'queue_zone', 
            'Cash Counter Queue', 
            ?, ?, ?, ?
        )
    """, (json.dumps(poly), json.dumps(axis_start), json.dumps(axis_end), now_ts))
    
    conn.commit()
    conn.close()
    print("Strict Cash-Counter Queue ROI successfully seeded into SQLite.")

if __name__ == "__main__":
    seed_demo_zones()
