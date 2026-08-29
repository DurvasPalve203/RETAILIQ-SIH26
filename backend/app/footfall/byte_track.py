import numpy as np
from typing import List, Dict, Tuple, Optional, Any

class TrackState:
    New = 0
    Tracked = 1
    Lost = 2
    Removed = 3

class STrack:
    _count = 0

    def __init__(self, tlbr: np.ndarray, score: float):
        STrack._count += 1
        self.track_id = STrack._count
        self.tlbr = np.asarray(tlbr, dtype=np.float32)
        self.score = float(score)
        self.state = TrackState.New
        self.is_activated = False
        self.frame_id = 0
        self.tracklet_len = 0
        self.start_frame = 0
        self.time_since_update = 0

    @property
    def tlwh(self):
        ret = np.asarray(self.tlbr).copy()
        ret[2] -= ret[0]
        ret[3] -= ret[1]
        return ret

    @property
    def centroid(self) -> Tuple[float, float]:
        return ((self.tlbr[0] + self.tlbr[2]) / 2.0, (self.tlbr[1] + self.tlbr[3]) / 2.0)

    def activate(self, frame_id: int):
        self.state = TrackState.Tracked
        self.is_activated = True
        self.frame_id = frame_id
        self.start_frame = frame_id
        self.tracklet_len = 0
        self.time_since_update = 0

    def re_activate(self, new_track: 'STrack', frame_id: int, new_id: bool = False):
        self.tlbr = new_track.tlbr
        self.score = new_track.score
        self.state = TrackState.Tracked
        self.is_activated = True
        self.frame_id = frame_id
        self.tracklet_len += 1
        self.time_since_update = 0
        if new_id:
            STrack._count += 1
            self.track_id = STrack._count

    def update(self, new_track: 'STrack', frame_id: int):
        self.frame_id = frame_id
        self.tracklet_len += 1
        self.tlbr = new_track.tlbr
        self.score = new_track.score
        self.state = TrackState.Tracked
        self.is_activated = True
        self.time_since_update = 0

    def mark_lost(self):
        self.state = TrackState.Lost

    def mark_removed(self):
        self.state = TrackState.Removed

def iou_batch(atlbrs: np.ndarray, btlbrs: np.ndarray) -> np.ndarray:
    """Calculate IoU distance matrix between two sets of boxes."""
    if len(atlbrs) == 0 or len(btlbrs) == 0:
        return np.zeros((len(atlbrs), len(btlbrs)), dtype=np.float32)

    ious = np.zeros((len(atlbrs), len(btlbrs)), dtype=np.float32)
    for i, a in enumerate(atlbrs):
        for j, b in enumerate(btlbrs):
            x1 = max(a[0], b[0])
            y1 = max(a[1], b[1])
            x2 = min(a[2], b[2])
            y2 = min(a[3], b[3])
            w = max(0.0, x2 - x1)
            h = max(0.0, y2 - y1)
            inter = w * h
            sa = (a[2] - a[0]) * (a[3] - a[1])
            sb = (b[2] - b[0]) * (b[3] - b[1])
            union = sa + sb - inter
            ious[i, j] = inter / max(1e-6, union)
    return 1.0 - ious  # Cost matrix = 1 - IoU

class ByteTracker:
    """
    Module 4: ByteTrack lightweight multi-object tracking implementation
    Tracks person bounding boxes consistently across video frames.
    """
    def __init__(self, track_high_thresh: float = 0.6, track_low_thresh: float = 0.1, match_thresh: float = 0.7, max_time_lost: int = 30):
        self.track_high_thresh = track_high_thresh
        self.track_low_thresh = track_low_thresh
        self.match_thresh = match_thresh
        self.max_time_lost = max_time_lost
        
        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []
        self.frame_id = 0

    def update(self, detections: List[Dict[str, Any]]) -> List[STrack]:
        """
        Update tracker with detections from current frame.
        detections: list of dicts with 'box' [x1,y1,x2,y2] and 'confidence'.
        """
        self.frame_id += 1
        activated_stracks = []
        refind_stracks = []
        lost_stracks = []
        removed_stracks = []

        scores = [d.get("confidence", 0.9) for d in detections]
        boxes = [d["box"] for d in detections]

        remain_inds = [i for i, s in enumerate(scores) if s >= self.track_high_thresh]
        inds_low = [i for i, s in enumerate(scores) if self.track_low_thresh <= s < self.track_high_thresh]

        # 1. High score detections
        detections_high = [STrack(boxes[i], scores[i]) for i in remain_inds]
        # 2. Low score detections
        detections_low = [STrack(boxes[i], scores[i]) for i in inds_low]

        # Candidates from currently tracked + lost
        unconfirmed = [t for t in self.tracked_stracks if not t.is_activated]
        tracked_stracks = [t for t in self.tracked_stracks if t.is_activated]
        strack_pool = tracked_stracks + self.lost_stracks

        # Match Step 1: High score detections with existing tracks using IoU
        if strack_pool and detections_high:
            pool_boxes = np.array([t.tlbr for t in strack_pool])
            det_boxes = np.array([t.tlbr for t in detections_high])
            dists = iou_batch(pool_boxes, det_boxes)

            matched_tracks = set()
            matched_dets = set()
            
            # Simple greedy match for edge efficiency
            for _ in range(min(len(pool_boxes), len(det_boxes))):
                min_val = np.min(dists)
                if min_val > self.match_thresh:
                    break
                row, col = np.unravel_index(np.argmin(dists), dists.shape)
                dists[row, :] = 1e5
                dists[:, col] = 1e5
                
                track = strack_pool[row]
                det = detections_high[col]
                if track.state == TrackState.Tracked:
                    track.update(det, self.frame_id)
                    activated_stracks.append(track)
                else:
                    track.re_activate(det, self.frame_id, new_id=False)
                    refind_stracks.append(track)
                matched_tracks.add(row)
                matched_dets.add(col)

            unmatched_tracks = [strack_pool[i] for i in range(len(strack_pool)) if i not in matched_tracks]
            unmatched_dets = [detections_high[i] for i in range(len(detections_high)) if i not in matched_dets]
        else:
            unmatched_tracks = strack_pool
            unmatched_dets = detections_high

        # Match Step 2: Match remaining tracks with low score detections
        if unmatched_tracks and detections_low:
            pool_boxes = np.array([t.tlbr for t in unmatched_tracks])
            det_boxes = np.array([t.tlbr for t in detections_low])
            dists = iou_batch(pool_boxes, det_boxes)

            matched_tracks_2 = set()
            for _ in range(min(len(pool_boxes), len(det_boxes))):
                min_val = np.min(dists)
                if min_val > 0.5: # Lower IoU requirement for low-score detections
                    break
                row, col = np.unravel_index(np.argmin(dists), dists.shape)
                dists[row, :] = 1e5
                dists[:, col] = 1e5
                track = unmatched_tracks[row]
                det = detections_low[col]
                if track.state == TrackState.Tracked:
                    track.update(det, self.frame_id)
                    activated_stracks.append(track)
                else:
                    track.re_activate(det, self.frame_id, new_id=False)
                    refind_stracks.append(track)
                matched_tracks_2.add(row)

            for i, track in enumerate(unmatched_tracks):
                if i not in matched_tracks_2:
                    if track.state != TrackState.Lost:
                        track.mark_lost()
                        lost_stracks.append(track)
        else:
            for track in unmatched_tracks:
                if track.state != TrackState.Lost:
                    track.mark_lost()
                    lost_stracks.append(track)

        # Step 3: Initialize new tracks from unmatched high-score detections
        for det in unmatched_dets:
            det.activate(self.frame_id)
            activated_stracks.append(det)

        # Step 4: Purge dead tracks exceeding max_time_lost
        for track in self.lost_stracks:
            if self.frame_id - track.frame_id > self.max_time_lost:
                track.mark_removed()
                removed_stracks.append(track)

        # Update collections
        self.tracked_stracks = [t for t in self.tracked_stracks if t.state == TrackState.Tracked] + activated_stracks + refind_stracks
        self.lost_stracks = [t for t in self.lost_stracks if t.state == TrackState.Lost] + lost_stracks
        self.removed_stracks += removed_stracks

        # Remove duplicate track IDs
        unique_tracked = {}
        for t in self.tracked_stracks:
            unique_tracked[t.track_id] = t
        self.tracked_stracks = list(unique_tracked.values())

        return [t for t in self.tracked_stracks if t.is_activated]
