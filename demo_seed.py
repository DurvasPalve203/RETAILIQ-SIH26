import json
import time
import cv2
import numpy as np
from backend.app.database import get_db_connection, init_db
from backend.app.shelf_pipeline.sku_matcher import SkuMatcher

def seed_database():
    """Seeds the SQLite database with initial calibrated zones, SKU gallery, and baseline products."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    now = time.time()

    print("Seeding RetailIQ database...")

    # 1. Seed Calibrated Zones
    # Shelf 1 (Top: Milk), Shelf 2 (Middle: Yogurt), Shelf 3 (Bottom: Cold Brew), Entrance Zone, Staff Zone
    zones = [
        {
            "zone_id": "zone-shelf-01",
            "camera_id": "cam-01",
            "polygon": [
                {"x": 0.08, "y": 0.12},
                {"x": 0.92, "y": 0.12},
                {"x": 0.92, "y": 0.30},
                {"x": 0.08, "y": 0.30}
            ],
            "zone_type": "shelf",
            "label": "Zone 1 — Organic Whole Milk",
            "target_sku_id": "SKU-MILK-01",
            "expected_capacity": 8
        },
        {
            "zone_id": "zone-shelf-02",
            "camera_id": "cam-01",
            "polygon": [
                {"x": 0.08, "y": 0.30},
                {"x": 0.92, "y": 0.30},
                {"x": 0.92, "y": 0.46},
                {"x": 0.08, "y": 0.46}
            ],
            "zone_type": "shelf",
            "label": "Zone 2 — Greek Vanilla Yogurt",
            "target_sku_id": "SKU-YOGURT-02",
            "expected_capacity": 10
        },
        {
            "zone_id": "zone-shelf-03",
            "camera_id": "cam-01",
            "polygon": [
                {"x": 0.08, "y": 0.46},
                {"x": 0.92, "y": 0.46},
                {"x": 0.92, "y": 0.64},
                {"x": 0.08, "y": 0.64}
            ],
            "zone_type": "shelf",
            "label": "Zone 3 — Nitro Cold Brew Coffee",
            "target_sku_id": "SKU-COLDBREW-03",
            "expected_capacity": 8
        },
        {
            "zone_id": "zone-entrance-01",
            "camera_id": "cam-01",
            "polygon": [
                {"x": 0.02, "y": 0.68},
                {"x": 0.25, "y": 0.68},
                {"x": 0.25, "y": 0.98},
                {"x": 0.02, "y": 0.98}
            ],
            "zone_type": "entrance",
            "label": "Store Main Entrance",
            "target_sku_id": None,
            "expected_capacity": 20
        },
        {
            "zone_id": "zone-queue-01",
            "camera_id": "cam-01",
            "polygon": [
                {"x": 0.22, "y": 0.70},
                {"x": 0.74, "y": 0.70},
                {"x": 0.74, "y": 0.96},
                {"x": 0.22, "y": 0.96}
            ],
            "zone_type": "queue_zone",
            "label": "POS Express Billing Counter Queue",
            "target_sku_id": None,
            "expected_capacity": 6,
            "axis_start_xy": {"x": 0.28, "y": 0.86}, # Back of queue
            "axis_end_xy": {"x": 0.70, "y": 0.86}    # Front billing counter
        },
        {
            "zone_id": "zone-staff-01",
            "camera_id": "cam-01",
            "polygon": [
                {"x": 0.85, "y": 0.68},
                {"x": 0.98, "y": 0.68},
                {"x": 0.98, "y": 0.98},
                {"x": 0.85, "y": 0.98}
            ],
            "zone_type": "staff",
            "label": "Staff Counter & Inventory Door",
            "target_sku_id": None,
            "expected_capacity": 2,
            "axis_start_xy": None,
            "axis_end_xy": None
        }
    ]

    for z in zones:
        axis_start_json = json.dumps(z.get("axis_start_xy")) if z.get("axis_start_xy") else None
        axis_end_json = json.dumps(z.get("axis_end_xy")) if z.get("axis_end_xy") else None
        cursor.execute("""
            INSERT INTO zones (zone_id, camera_id, polygon_json, zone_type, label, target_sku_id, expected_capacity, axis_start_xy, axis_end_xy, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zone_id) DO UPDATE SET
                polygon_json=excluded.polygon_json,
                zone_type=excluded.zone_type,
                label=excluded.label,
                target_sku_id=excluded.target_sku_id,
                expected_capacity=excluded.expected_capacity,
                axis_start_xy=excluded.axis_start_xy,
                axis_end_xy=excluded.axis_end_xy;
        """, (z["zone_id"], z["camera_id"], json.dumps(z["polygon"]), z["zone_type"], z["label"], z["target_sku_id"], z["expected_capacity"], axis_start_json, axis_end_json, now))

        if z["zone_type"] == "queue_zone":
            cursor.execute("""
                INSERT INTO queue_zones (zone_id, camera_id, polygon_json, axis_start_xy, axis_end_xy, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(zone_id) DO UPDATE SET
                    polygon_json=excluded.polygon_json,
                    axis_start_xy=excluded.axis_start_xy,
                    axis_end_xy=excluded.axis_end_xy;
            """, (z["zone_id"], z["camera_id"], json.dumps(z["polygon"]), axis_start_json, axis_end_json, now))

    # 2. Seed SKU Gallery with few-shot embeddings
    matcher = SkuMatcher()
    
    # Generate sample crops for default SKUs
    skus = [
        ("SKU-MILK-01", "Organic Whole Milk 1-Gallon", "Dairy & Eggs", 4.49, (230, 240, 255)),
        ("SKU-YOGURT-02", "Greek Vanilla Yogurt Tub 32oz", "Dairy & Eggs", 5.29, (220, 255, 230)),
        ("SKU-COLDBREW-03", "Nitro Cold Brew Coffee Can 12oz", "Beverages", 3.99, (200, 210, 230)),
        ("SKU-ALMOND-04", "Unsweetened Almond Milk 64oz", "Plant-Based", 3.79, (245, 235, 220)),
        ("SKU-OAT-05", "Barista Blend Oat Milk", "Plant-Based", 4.99, (235, 245, 240)),
    ]

    for sku_id, name, cat, price, base_color in skus:
        # Create 5 synthetic crops with slight color variations for few-shot onboarding
        crops = []
        for i in range(5):
            crop = np.zeros((140, 100, 3), dtype=np.uint8)
            col = tuple(max(0, min(255, c + (i * 5 - 10))) for c in base_color)
            crop[:] = col
            cv2.rectangle(crop, (5, 5), (95, 135), (80, 80, 80), 2)
            cv2.putText(crop, sku_id[-4:], (15, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 20, 20), 1)
            crops.append(crop)

        matcher.onboard_sku(
            sku_id=sku_id,
            name=name,
            category=cat,
            price=price,
            sample_crops=crops
        )

    # 3. Seed sample historical stock events for ROI calculation
    sample_events = [
        ("evt-seed-101", "zone-shelf-01", "SKU-MILK-01", "stock_out", "high", 0.95, now - 14400, now - 13200, 1200.0, 50.0, "resolved"),
        ("evt-seed-102", "zone-shelf-03", "SKU-COLDBREW-03", "stock_out", "medium", 0.88, now - 8600, now - 7700, 900.0, 37.5, "resolved"),
        ("evt-seed-103", "zone-shelf-02", "SKU-YOGURT-02", "stock_out", "low", 0.78, now - 4200, now - 3600, 600.0, 25.0, "resolved"),
    ]
    for e in sample_events:
        cursor.execute("""
            INSERT INTO stock_events (event_id, zone_id, sku_id_nullable, type, severity, confidence, ts_start, ts_end, duration_seconds, estimated_lost_sales, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO NOTHING;
        """, e)

    # 4. Seed sample dwell records
    for i in range(1, 24):
        cursor.execute("""
            INSERT INTO dwell_records (record_id, track_id, zone_id, entry_ts, exit_ts, dwell_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(record_id) DO NOTHING;
        """, (f"dwl-seed-{i}", 100 + i, "zone-shelf-01" if i % 2 == 0 else "zone-shelf-02", now - (i * 300), now - (i * 300) + 14, 14.0 + (i % 8)))

    # 5. Seed historical checkout service completions for wait time rolling average
    sample_services = [
        ("svc-seed-01", "zone-queue-01", 195, now - 1800, 42.0),
        ("svc-seed-02", "zone-queue-01", 196, now - 1450, 48.0),
        ("svc-seed-03", "zone-queue-01", 197, now - 1100, 36.0),
        ("svc-seed-04", "zone-queue-01", 198, now - 720, 45.0),
        ("svc-seed-05", "zone-queue-01", 199, now - 350, 39.0),
    ]
    for s in sample_services:
        cursor.execute("""
            INSERT INTO service_completions (completion_id, zone_id, track_id, ts, service_duration_seconds)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(completion_id) DO NOTHING;
        """, s)

    conn.commit()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
