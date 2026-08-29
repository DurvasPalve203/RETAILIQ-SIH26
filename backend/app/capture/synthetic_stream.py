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
        
        # Simulating aisle browsing shoppers
        self.customers = [
            {"id": 101, "x": 100.0, "y": 550.0, "vx": 2.2, "vy": 0.0, "dwell_target": "zone-shelf-01", "dwell_remaining": 0, "color": (180, 100, 80)},
            {"id": 102, "x": 1200.0, "y": 560.0, "vx": -1.8, "vy": 0.0, "dwell_target": "zone-shelf-02", "dwell_remaining": 0, "color": (80, 140, 200)},
        ]

        # Queue line shoppers (standing along axis x: 380 to 880, y: 620, facing counter at x: 920)
        self.queue_shoppers = [
            {"id": 201, "x": 860.0, "y": 620.0, "target_x": 860.0, "color": (120, 160, 220), "facing_angle": 0.0},  # Front #1
            {"id": 202, "x": 720.0, "y": 620.0, "target_x": 720.0, "color": (190, 110, 90), "facing_angle": 0.0},   # #2
            {"id": 203, "x": 580.0, "y": 620.0, "target_x": 580.0, "color": (90, 170, 130), "facing_angle": 0.0},   # #3
        ]
        self._next_shopper_id = 204
        self._last_service_time = time.time()
        
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

    def add_queue_shopper(self):
        """Add a new shopper to the back of the queue line."""
        back_x = 420.0 if not self.queue_shoppers else min(350.0, self.queue_shoppers[-1]["x"] - 110.0)
        self.queue_shoppers.append({
            "id": self._next_shopper_id,
            "x": max(150.0, back_x),
            "y": 620.0,
            "target_x": max(150.0, back_x),
            "color": (random.randint(60, 210), random.randint(60, 210), random.randint(60, 210)),
            "facing_angle": 0.0
        })
        self._next_shopper_id += 1

    def serve_checkout_customer(self):
        """Simulate front customer checkout completion."""
        if self.queue_shoppers:
            # Front shopper leaves checkout
            self.queue_shoppers.pop(0)
            # Shift remaining shoppers forward towards counter
            target_positions = [860.0, 720.0, 580.0, 440.0, 300.0, 180.0]
            for idx, q in enumerate(self.queue_shoppers):
                if idx < len(target_positions):
                    q["target_x"] = target_positions[idx]

    def trigger_queue_surge(self, count: int = 4):
        """Trigger rapid queue buildup for demonstration."""
        for _ in range(count):
            self.add_queue_shopper()

    def toggle_occlusion(self, enabled: bool):
        self.is_occluded_sim = enabled

    def toggle_low_light(self, enabled: bool):
        self.low_light_sim = enabled

    def read(self) -> Tuple[bool, np.ndarray, Dict[str, Any]]:
        self.frame_count += 1
        now = time.time()
        
        # Auto-depletion cycle for dynamic demonstration every 25 seconds
        if now - self._last_depletion_time > 22.0:
            target = "zone-shelf-01" if random.random() > 0.5 else "zone-shelf-03"
            if self.shelf_state[target]["current"] > 1:
                self.shelf_state[target]["current"] -= 1
            elif self.shelf_state[target]["current"] == 1:
                self.shelf_state[target]["current"] = self.shelf_state[target]["capacity"]
            self._last_depletion_time = now

        # Auto-service cycle: every 35s, serve front customer and maybe add new customer
        if now - self._last_service_time > 35.0:
            if len(self.queue_shoppers) >= 2:
                self.serve_checkout_customer()
            else:
                self.add_queue_shopper()
            self._last_service_time = now

        # Base Store Background (Modern Retail Aisle & Checkout Zone)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Background wall & floor gradient
        for y in range(self.height):
            if y < 450:
                val = int(220 - (y / 450) * 40)
                frame[y, :] = (val, val + 5, val + 10)
            else:
                val = int(170 + ((y - 450) / 270) * 40)
                frame[y, :] = (val - 10, val, val + 5)

        # Draw tile grid lines on floor
        for x in range(0, self.width, 100):
            cv2.line(frame, (x, 450), (int(x * 1.3) - 150, self.height), (150, 155, 160), 1)
        for y in range(450, self.height, 50):
            cv2.line(frame, (0, y), (self.width, y), (160, 165, 170), 1)

        # Draw Shelf Structure (Left/Top side)
        cv2.rectangle(frame, (100, 80), (780, 460), (70, 75, 80), -1)
        cv2.rectangle(frame, (110, 90), (770, 450), (45, 48, 52), -1)

        # Draw Checkout Billing Counter Structure (Right side: x: 860 to 1220, y: 280 to 480)
        cv2.rectangle(frame, (880, 260), (1220, 470), (55, 60, 68), -1) # Counter base
        cv2.rectangle(frame, (860, 250), (1240, 280), (140, 145, 150), -1) # Counter top surface
        # POS Monitor & Barcode Scanner
        cv2.rectangle(frame, (960, 190), (1050, 250), (25, 28, 32), -1)
        cv2.rectangle(frame, (965, 195), (1045, 245), (0, 180, 220), -1) # POS screen glowing
        cv2.rectangle(frame, (995, 250), (1015, 260), (40, 40, 40), -1) # Stand
        cv2.putText(frame, "POS #1", (975, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, "CHECKOUT & BILLING POINT", (900, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        # Draw Queue Guide Stanchions & Floor Stanchion Rope
        cv2.circle(frame, (380, 620), 8, (160, 140, 40), -1)
        cv2.circle(frame, (620, 620), 8, (160, 140, 40), -1)
        cv2.circle(frame, (860, 620), 8, (160, 140, 40), -1)
        # Stanchion line
        cv2.line(frame, (380, 620), (860, 620), (180, 160, 60), 2)
        cv2.putText(frame, "QUEUE LANE -> BILLING", (480, 655), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 130, 140), 1)

        # 3 Shelf Tiers
        tiers = [
            {"y_shelf": 200, "zone": "zone-shelf-01", "name": "Tier 1: Milk Products"},
            {"y_shelf": 320, "zone": "zone-shelf-02", "name": "Tier 2: Yogurt & Dairy"},
            {"y_shelf": 440, "zone": "zone-shelf-03", "name": "Tier 3: Beverages"},
        ]

        active_bounding_boxes = []

        for tier in tiers:
            y_shelf = tier["y_shelf"]
            zone_id = tier["zone"]
            state = self.shelf_state[zone_id]
            
            # Metal shelf bar
            cv2.rectangle(frame, (110, y_shelf - 5), (770, y_shelf + 8), (140, 145, 150), -1)
            cv2.rectangle(frame, (110, y_shelf + 8), (770, y_shelf + 15), (90, 95, 100), -1)
            
            # Price tags
            for tag_x in range(150, 720, 100):
                cv2.rectangle(frame, (tag_x, y_shelf + 9), (tag_x + 50, y_shelf + 14), (240, 240, 240), -1)

            # Draw Items
            capacity = state["capacity"]
            current_count = state["current"]
            slot_width = (720 - 150) / capacity
            
            for i in range(capacity):
                item_x = int(140 + i * slot_width)
                item_w = int(slot_width * 0.78)
                item_h = int(y_shelf - 30 - (y_shelf - 100))
                item_y = y_shelf - 5 - item_h

                if i < current_count:
                    c = state["color"]
                    acc = state["accent"]
                    cv2.rectangle(frame, (item_x, item_y), (item_x + item_w, y_shelf - 5), c, -1)
                    cv2.rectangle(frame, (item_x, item_y), (item_x + item_w, y_shelf - 5), acc, 2)
                    cv2.rectangle(frame, (item_x + 4, item_y + 12), (item_x + item_w - 4, item_y + 30), acc, -1)
                    cv2.putText(frame, state["sku"][-4:], (item_x + 5, item_y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1)

                    active_bounding_boxes.append({
                        "box": [item_x, item_y, item_x + item_w, y_shelf - 5],
                        "class": "product",
                        "sku": state["sku"],
                        "confidence": 0.94 + round(random.uniform(-0.03, 0.04), 2)
                    })
                else:
                    gap_box = [item_x, item_y, item_x + item_w, y_shelf - 5]
                    cv2.rectangle(frame, (item_x, item_y), (item_x + item_w, y_shelf - 5), (35, 38, 42), -1)
                    active_bounding_boxes.append({
                        "box": gap_box,
                        "class": "empty_shelf_gap",
                        "sku": None,
                        "confidence": 0.91 + round(random.uniform(-0.04, 0.04), 2)
                    })

        # Update & Render Aisle Shoppers (Browsing behavior)
        for cust in self.customers:
            if cust["dwell_remaining"] > 0:
                cust["dwell_remaining"] -= 1
            else:
                cust["x"] += cust["vx"]
                if cust["x"] > 740 or cust["x"] < 80:
                    cust["vx"] = -cust["vx"]
                    if random.random() > 0.4:
                        cust["dwell_remaining"] = random.randint(15, 35)

            cx, cy = int(cust["x"]), int(cust["y"])
            cw, ch = 65, 145
            px1, py1, px2, py2 = cx - cw // 2, cy - ch, cx + cw // 2, cy
            
            # Head & Face
            cv2.circle(frame, (cx, py1 + 22), 16, (210, 180, 160), -1)
            # Eyes/mouth for face detection
            cv2.circle(frame, (cx - 5, py1 + 20), 2, (40, 30, 20), -1)
            cv2.circle(frame, (cx + 5, py1 + 20), 2, (40, 30, 20), -1)
            # Torso
            cv2.rectangle(frame, (px1 + 8, py1 + 40), (px2 - 8, py1 + 100), cust["color"], -1)
            # Legs
            cv2.rectangle(frame, (px1 + 12, py1 + 100), (cx - 2, py2), (50, 50, 60), -1)
            cv2.rectangle(frame, (cx + 2, py1 + 100), (px2 - 12, py2), (50, 50, 60), -1)

            active_bounding_boxes.append({
                "box": [px1, py1, px2, py2],
                "class": "person",
                "track_id": cust["id"],
                "confidence": 0.93
            })

        # Update & Render Queue Shoppers (Queue behavior: lined up facing right towards counter)
        for q in self.queue_shoppers:
            # Smoothly move towards target forward position
            if abs(q["x"] - q["target_x"]) > 1.0:
                q["x"] += 1.8 if q["target_x"] > q["x"] else -1.8

            cx, cy = int(q["x"]), int(q["y"])
            cw, ch = 65, 145
            px1, py1, px2, py2 = cx - cw // 2, cy - ch, cx + cw // 2, cy

            # Head & Face (facing right towards counter)
            cv2.circle(frame, (cx, py1 + 22), 16, (215, 185, 165), -1)
            # Facial profile facing right
            cv2.circle(frame, (cx + 6, py1 + 20), 2, (40, 30, 20), -1)
            # Torso (upright posture facing counter)
            cv2.rectangle(frame, (px1 + 8, py1 + 40), (px2 - 8, py1 + 100), q["color"], -1)
            # Legs
            cv2.rectangle(frame, (px1 + 12, py1 + 100), (cx - 2, py2), (45, 45, 55), -1)
            cv2.rectangle(frame, (cx + 2, py1 + 100), (px2 - 12, py2), (45, 45, 55), -1)

            active_bounding_boxes.append({
                "box": [px1, py1, px2, py2],
                "class": "person",
                "track_id": q["id"],
                "confidence": 0.94
            })

        # Apply Sim Lighting / Occlusion
        if self.low_light_sim:
            frame = cv2.convertScaleAbs(frame, alpha=0.3, beta=-20)

        if self.is_occluded_sim:
            cv2.rectangle(frame, (0, 0), (self.width, self.height), (12, 12, 14), -1)
            cv2.putText(frame, "CAMERA OCCLUSION EVENT (BLOCKED LENS)", (int(self.width * 0.25), int(self.height * 0.5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 80, 220), 2)

        meta = {
            "frame_id": self.frame_count,
            "timestamp": now,
            "ground_truth_boxes": active_bounding_boxes,
            "shelf_state": {k: v["current"] for k, v in self.shelf_state.items()},
            "queue_shopper_count": len(self.queue_shoppers)
        }

        return True, frame, meta

