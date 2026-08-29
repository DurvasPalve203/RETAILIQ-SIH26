import time
import uuid
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from backend.app.config import settings
from backend.app.database import get_db_connection
from backend.app.footfall.byte_track import ByteTracker, STrack

class DwellAndFootfallEngine:
    """
    Module 4: Footfall & Dwell Tracking Engine
    - Computes zone dwell time for tracked individuals
    - Records entrance zone footfall metrics
    - Handles staff zone exclusions
    - Finalizes dwell records to SQLite database
    """
    def __init__(self, config=settings.tracking_and_footfall):
        self.config = config
        self.tracker = ByteTracker(
            track_high_thresh=config.track_high_threshold,
            track_low_thresh=config.track_low_threshold,
            match_thresh=config.match_threshold,
            max_time_lost=config.track_buffer_frames
        )
        
        # State: active track zone visits {track_id: {zone_id: {"entry_ts": float, "last_ts": float, "frame_count": int}}}
        self._active_visits: Dict[int, Dict[str, Dict[str, Any]]] = {}
        # Track IDs that crossed entrance today
        self._entrance_crossings_today = set()
        self._last_day_bucket = time.strftime("%Y-%m-%d")

    def _is_in_zone(self, centroid: Tuple[float, float], zone_polygon: List[Dict[str, float]], frame_w: int, frame_h: int) -> bool:
        if not zone_polygon:
            return False
        pts = []
        for pt in zone_polygon:
            px = pt["x"] if pt["x"] > 1.0 else pt["x"] * frame_w
            py = pt["y"] if pt["y"] > 1.0 else pt["y"] * frame_h
            pts.append((px, py))
        
        poly_arr = np.array(pts, dtype=np.int32)
        dist = cv2.pointPolygonTest(poly_arr, (float(centroid[0]), float(centroid[1])), False)
        return dist >= 0

    def update(self, person_detections: List[Dict[str, Any]], zones: List[Dict[str, Any]], frame_w: int, frame_h: int) -> Dict[str, Any]:
        """
        Process person detections, update ByteTrack, compute dwell times, and persist finalized records.
        """
        now = time.time()
        
        # Day rollover check for footfall set
        today = time.strftime("%Y-%m-%d")
        if today != self._last_day_bucket:
            self._entrance_crossings_today.clear()
            self._last_day_bucket = today

        # 1. Update ByteTrack
        active_tracks: List[STrack] = self.tracker.update(person_detections)
        active_track_ids = {t.track_id for t in active_tracks}

        finalized_dwell_records = []
        new_footfall_count = 0
        current_zone_occupants = {z["zone_id"]: 0 for z in zones}

        # 2. Match active track centroids to calibrated zones
        for track in active_tracks:
            tid = track.track_id
            centroid = track.centroid

            if tid not in self._active_visits:
                self._active_visits[tid] = {}

            # Test against each zone
            for zone in zones:
                zid = zone["zone_id"]
                ztype = zone.get("zone_type", "shelf")
                poly = zone.get("polygon", [])

                in_zone = self._is_in_zone(centroid, poly, frame_w, frame_h)
                
                if in_zone:
                    current_zone_occupants[zid] += 1

                    if zid not in self._active_visits[tid]:
                        # First entry into zone
                        self._active_visits[tid][zid] = {
                            "entry_ts": now,
                            "last_ts": now,
                            "frame_count": 1,
                            "zone_type": ztype
                        }
                        
                        # Entrance zone footfall registration
                        if ztype == "entrance" and tid not in self._entrance_crossings_today:
                            self._entrance_crossings_today.add(tid)
                            new_footfall_count += 1
                    else:
                        # Continue visit
                        self._active_visits[tid][zid]["last_ts"] = now
                        self._active_visits[tid][zid]["frame_count"] += 1
                else:
                    # Not in zone - check if previously in zone and now exited
                    if zid in self._active_visits[tid]:
                        visit = self._active_visits[tid].pop(zid)
                        dwell_sec = visit["last_ts"] - visit["entry_ts"]
                        
                        if dwell_sec >= self.config.min_dwell_seconds:
                            record = self._persist_dwell_record(tid, zid, visit["entry_ts"], visit["last_ts"], dwell_sec)
                            finalized_dwell_records.append(record)

        # 3. Finalize visits for tracks that disappeared/terminated
        stale_tids = [tid for tid in self._active_visits if tid not in active_track_ids]
        for tid in stale_tids:
            for zid, visit in list(self._active_visits[tid].items()):
                dwell_sec = visit["last_ts"] - visit["entry_ts"]
                if dwell_sec >= self.config.min_dwell_seconds:
                    record = self._persist_dwell_record(tid, zid, visit["entry_ts"], visit["last_ts"], dwell_sec)
                    finalized_dwell_records.append(record)
            del self._active_visits[tid]

        return {
            "active_tracks_count": len(active_tracks),
            "tracks": [{"track_id": t.track_id, "centroid": t.centroid, "box": t.tlbr.tolist()} for t in active_tracks],
            "total_footfall_today": len(self._entrance_crossings_today),
            "new_footfall_in_frame": new_footfall_count,
            "zone_occupants": current_zone_occupants,
            "finalized_dwells": finalized_dwell_records
        }

    def _persist_dwell_record(self, track_id: int, zone_id: str, entry_ts: float, exit_ts: float, dwell_seconds: float) -> Dict[str, Any]:
        """Persist finalized dwell record to SQLite."""
        record_id = f"dwl-{uuid.uuid4().hex[:10]}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dwell_records (record_id, track_id, zone_id, entry_ts, exit_ts, dwell_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (record_id, track_id, zone_id, entry_ts, exit_ts, round(dwell_seconds, 2)))
        conn.commit()

        return {
            "record_id": record_id,
            "track_id": track_id,
            "zone_id": zone_id,
            "entry_ts": entry_ts,
            "exit_ts": exit_ts,
            "dwell_seconds": round(dwell_seconds, 2)
        }
