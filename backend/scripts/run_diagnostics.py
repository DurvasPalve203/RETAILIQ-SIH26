import sys
import os
import time
import cv2
import json
import sqlite3
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.config import settings
from backend.app.shelf_pipeline.detector import ShelfDetector
from backend.app.queue_pipeline.queue_engine import QueueDetectionEngine
from backend.app.footfall.dwell_engine import DwellAndFootfallEngine

def run_diag():
    print("=== Diagnostic Script Started ===")
    
    # 1. Capture Frame
    cam_url = settings.video_capture.source
    print(f"Connecting to {cam_url} ...")
    cap = cv2.VideoCapture(cam_url)
    if not cap.isOpened():
        print(f"FAILED to open {cam_url}")
        return
    
    ret, frame = cap.read()
    if not ret or frame is None:
        print("FAILED to read frame")
        return
        
    h, w = frame.shape[:2]
    print(f"Captured Frame: {w}x{h}")
    cap.release()
    
    # 2. Detector
    print("\n--- YOLO Person Detection ---")
    detector = ShelfDetector()
    t0 = time.time()
    person_dets = detector._detect_persons(frame)
    t1 = time.time()
    print(f"YOLO Inference Time: {(t1-t0)*1000:.1f} ms")
    print(f"Raw Person Detections from _detect_persons: {len(person_dets)}")
    for i, d in enumerate(person_dets):
        print(f" Det {i}: bbox {d['box']} conf {d['confidence']} class {d.get('class_name')}")
        
    # 3. Tracker
    print("\n--- Tracking (DwellEngine) ---")
    tracker = DwellAndFootfallEngine()
    t0 = time.time()
    tracked_persons, footfall_count = tracker.update(person_dets, frame)
    t1 = time.time()
    print(f"Tracker Time: {(t1-t0)*1000:.1f} ms")
    print(f"Tracked Persons: {len(tracked_persons)}")
    for i, t in enumerate(tracked_persons):
        print(f" Track {i}: id {t['track_id']} bbox {t['box']} centroid {t.get('centroid')}")
        
    # 4. Queue Engine
    print("\n--- Queue Engine ---")
    db_path = settings.database.db_path
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT zone_id, zone_name, geometry FROM zones WHERE zone_type='queue'")
    zones_db = c.fetchall()
    conn.close()
    
    queue_zones = []
    for row in zones_db:
        poly = json.loads(row[2])
        queue_zones.append({
            "zone_id": row[0],
            "zone_name": row[1],
            "polygon": poly
        })
        
    print(f"Loaded {len(queue_zones)} queue zones from DB.")
    for z in queue_zones:
        print(f" Zone {z['zone_name']} polygon: {z['polygon']}")
        
    engine = QueueDetectionEngine(queue_zones)
    t0 = time.time()
    queue_res = engine.process_frame(tracked_persons, frame)
    t1 = time.time()
    print(f"Queue Engine Time: {(t1-t0)*1000:.1f} ms")
    
    print("\nQueue Output:")
    print(json.dumps(queue_res, indent=2))
    
    print("=== Diagnostic Complete ===")

if __name__ == "__main__":
    run_diag()
