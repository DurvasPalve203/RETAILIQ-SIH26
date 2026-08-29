import cv2
import numpy as np
import time
import math
import random
from typing import Dict, List, Tuple, Any

class SyntheticShelfStream:
    """
    Generates realistic, procedural shelf & aisle video frames for offline execution,
    benchmarking, testing, and judge demonstrations without requiring external cameras.
    """
    def __init__(self, width: int = 1280, height: int = 720, target_fps: int = 8):
        self.width = width
        self.height = height
        self.target_fps = target_fps
        self.start_time = time.time()
        self.frame_count = 0
        
        # Shelf Zones State: item counts & positions
        # Zone 1: Dairy Shelf Top (Milk cartons)
        # Zone 2: Dairy Shelf Bottom (Yogurt tubs)
        # Zone 3: Beverage Rack (Cold Brew Cans)
        self.shelf_state = {
            "zone-shelf-01": {"sku": "SKU-MILK-01", "name": "Organic Whole Milk", "capacity": 8, "current": 8, "color": (230, 240, 255), "accent": (40, 100, 220)},
            "zone-shelf-02": {"sku": "SKU-YOGURT-02", "name": "Greek Vanilla Yogurt", "capacity": 10, "current": 9, "color": (220, 255, 230), "accent": (40, 180, 80)},
            "zone-shelf-03": {"sku": "SKU-COLDBREW-03", "name": "Nitro Cold Brew Coffee", "capacity": 8, "current": 7, "color": (200, 210, 230), "accent": (160, 80, 40)},
        }
        
        # Simulating shoppers walking in store
        self.customers = [
            {"id": 101, "x": 100.0, "y": 550.0, "vx": 2.2, "vy": 0.0, "dwell_target": "zone-shelf-01", "dwell_remaining": 0, "color": (180, 100, 80)},
            {"id": 102, "x": 1200.0, "y": 560.0, "vx": -1.8, "vy": 0.0, "dwell_target": "zone-shelf-02", "dwell_remaining": 0, "color": (80, 140, 200)},
        ]
        
        self.is_occluded_sim = False
        self.low_light_sim = False
        self._last_depletion_time = time.time()

    def set_depletion(self, zone_id: str, count: int):
        """Manually trigger item depletion for a zone."""
        if zone_id in self.shelf_state:
            self.shelf_state[zone_id]["current"] = max(0, min(self.shelf_state[zone_id]["capacity"], count))

    def restock(self, zone_id: str):
        """Restock a zone back to full capacity."""
        if zone_id in self.shelf_state:
            self.shelf_state[zone_id]["current"] = self.shelf_state[zone_id]["capacity"]

    def toggle_occlusion(self, enabled: bool):
        self.is_occluded_sim = enabled

    def toggle_low_light(self, enabled: bool):
        self.low_light_sim = enabled

    def read(self) -> Tuple[bool, np.ndarray, Dict[str, Any]]:
        self.frame_count += 1
        now = time.time()
        
        # Auto-depletion cycle for dynamic demonstration every 25 seconds
        if now - self._last_depletion_time > 18.0:
            # Gradually deplete milk or cold brew
            target = "zone-shelf-01" if random.random() > 0.5 else "zone-shelf-03"
            if self.shelf_state[target]["current"] > 1:
                self.shelf_state[target]["current"] -= 1
            elif self.shelf_state[target]["current"] == 1:
                self.shelf_state[target]["current"] = self.shelf_state[target]["capacity"] # simulate restock
            self._last_depletion_time = now

        # Base Store Background (Modern Retail Aisle Rendering)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Background wall & floor gradient
        for y in range(self.height):
            if y < 450:
                # Store wall / lighting
                val = int(220 - (y / 450) * 40)
                frame[y, :] = (val, val + 5, val + 10)
            else:
                # Polished retail tile floor
                val = int(170 + ((y - 450) / 270) * 40)
                frame[y, :] = (val - 10, val, val + 5)

        # Draw tile grid lines on floor
        for x in range(0, self.width, 100):
            cv2.line(frame, (x, 450), (int(x * 1.3) - 150, self.height), (150, 155, 160), 1)
        for y in range(450, self.height, 50):
            cv2.line(frame, (0, y), (self.width, y), (160, 165, 170), 1)

        # Draw Shelf Structure
        # Shelf Bay: x: 120 to 1160, y: 100 to 450
        cv2.rectangle(frame, (100, 80), (1180, 460), (70, 75, 80), -1) # Outer metallic frame
        cv2.rectangle(frame, (110, 90), (1170, 450), (45, 48, 52), -1) # Inner shelf backing

        # 3 Shelf Tiers
        tiers = [
            {"y_shelf": 200, "zone": "zone-shelf-01", "name": "Tier 1: Milk Products"},
            {"y_shelf": 320, "zone": "zone-shelf-02", "name": "Tier 2: Yogurt & Dairy"},
            {"y_shelf": 440, "zone": "zone-shelf-03", "name": "Tier 3: Beverages"},
        ]

        active_bounding_boxes = [] # [{"box": [x1, y1, x2, y2], "class": "product", "sku": "...", "conf": 0.95}]

        for tier in tiers:
            y_shelf = tier["y_shelf"]
            zone_id = tier["zone"]
            state = self.shelf_state[zone_id]
            
            # Metal shelf bar
            cv2.rectangle(frame, (110, y_shelf - 5), (1170, y_shelf + 8), (140, 145, 150), -1)
            cv2.rectangle(frame, (110, y_shelf + 8), (1170, y_shelf + 15), (90, 95, 100), -1) # Price tag strip
            
            # Price tags on shelf strip
            for tag_x in range(160, 1100, 120):
                cv2.rectangle(frame, (tag_x, y_shelf + 9), (tag_x + 60, y_shelf + 14), (240, 240, 240), -1)

            # Draw Items based on current stock count
            capacity = state["capacity"]
            current_count = state["current"]
            slot_width = (1120 - 150) / capacity
            
            for i in range(capacity):
                item_x = int(150 + i * slot_width)
                item_w = int(slot_width * 0.78)
                item_h = int(y_shelf - 30 - (y_shelf - 100)) # item height
                item_y = y_shelf - 5 - item_h

                if i < current_count:
                    # Item Present
                    # Draw 3D Box
                    c = state["color"]
                    acc = state["accent"]
                    cv2.rectangle(frame, (item_x, item_y), (item_x + item_w, y_shelf - 5), c, -1)
                    cv2.rectangle(frame, (item_x, item_y), (item_x + item_w, y_shelf - 5), acc, 2)
                    # Item brand banner
                    cv2.rectangle(frame, (item_x + 4, item_y + 12), (item_x + item_w - 4, item_y + 32), acc, -1)
                    cv2.putText(frame, state["sku"][-4:], (item_x + 6, item_y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

                    # Register bounding box for detector ground-truth / synthetic vision
                    active_bounding_boxes.append({
                        "box": [item_x, item_y, item_x + item_w, y_shelf - 5],
                        "class": "product",
                        "sku": state["sku"],
                        "confidence": 0.94 + round(random.uniform(-0.03, 0.04), 2)
                    })
                else:
                    # Empty Shelf Gap!
                    gap_box = [item_x, item_y, item_x + item_w, y_shelf - 5]
                    # Slight shelf backing shadow
                    cv2.rectangle(frame, (item_x, item_y), (item_x + item_w, y_shelf - 5), (35, 38, 42), -1)
                    active_bounding_boxes.append({
                        "box": gap_box,
                        "class": "empty_shelf_gap",
                        "sku": None,
                        "confidence": 0.91 + round(random.uniform(-0.04, 0.04), 2)
                    })

        # Update & Render Customer Pedestrians
        for cust in self.customers:
            # Move customer
            if cust["dwell_remaining"] > 0:
                cust["dwell_remaining"] -= 1
            else:
                cust["x"] += cust["vx"]
                if cust["x"] > 1150 or cust["x"] < 120:
                    cust["vx"] = -cust["vx"]
                    # Maybe dwell at next shelf
                    if random.random() > 0.4:
                        cust["dwell_remaining"] = random.randint(15, 35)

            cx = int(cust["x"])
            cy = int(cust["y"])
            cw = 75
            ch = 160
            
            # Person Bounding Box: [x1, y1, x2, y2]
            px1, py1, px2, py2 = cx - cw // 2, cy - ch, cx + cw // 2, cy
            
            # Draw stylized customer figure
            # Head
            cv2.circle(frame, (cx, py1 + 25), 18, (210, 180, 160), -1)
            # Torso
            cv2.rectangle(frame, (px1 + 10, py1 + 45), (px2 - 10, py1 + 110), cust["color"], -1)
            # Legs
            cv2.rectangle(frame, (px1 + 14, py1 + 110), (cx - 3, py2), (50, 50, 60), -1)
            cv2.rectangle(frame, (cx + 3, py1 + 110), (px2 - 14, py2), (50, 50, 60), -1)

            active_bounding_boxes.append({
                "box": [px1, py1, px2, py2],
                "class": "person",
                "track_id": cust["id"],
                "confidence": 0.92 + round(random.uniform(-0.02, 0.05), 2)
            })

        # Apply Sim Lighting / Occlusion
        if self.low_light_sim:
            frame = cv2.convertScaleAbs(frame, alpha=0.3, beta=-20)

        if self.is_occluded_sim:
            # Large black or dark grey obstruction right in front of camera lens
            cv2.rectangle(frame, (0, 0), (self.width, self.height), (12, 12, 14), -1)
            cv2.putText(frame, "CAMERA OCCLUSION EVENT (BLOCKED LENS)", (int(self.width * 0.25), int(self.height * 0.5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 80, 220), 2)

        meta = {
            "frame_id": self.frame_count,
            "timestamp": now,
            "ground_truth_boxes": active_bounding_boxes,
            "shelf_state": {k: v["current"] for k, v in self.shelf_state.items()}
        }

        return True, frame, meta
