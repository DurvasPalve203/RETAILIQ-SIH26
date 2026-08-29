import cv2
import time
import threading
import queue
import logging
from typing import Optional, Tuple, Dict, Any
import numpy as np

from backend.app.config import settings
from backend.app.capture.frame_normalizer import FrameNormalizer
from backend.app.capture.synthetic_stream import SyntheticShelfStream

logger = logging.getLogger("retailiq.capture")

class VideoCaptureService:
    """
    Module 2: Video Capture Layer
    - Producer/Consumer architecture with ring-buffer (frame-drop policy)
    - Auto-reconnect with exponential backoff
    - Frame sampling (5-10 FPS)
    - Integrated frame normalization and occlusion detection
    """
    def __init__(self, config=settings.video_capture):
        self.config = config
        self.source = config.source
        self.target_fps = config.target_fps
        self.ring_buffer_size = config.ring_buffer_size
        
        self.frame_queue = queue.Queue(maxsize=self.ring_buffer_size)
        self.normalizer = FrameNormalizer(
            low_light_threshold=config.low_light_luma_threshold,
            occlusion_diff_threshold=config.occlusion_diff_threshold,
            occlusion_area_ratio=config.occlusion_min_area_ratio
        )
        
        self.synthetic_stream: Optional[SyntheticShelfStream] = None
        self.cap: Optional[cv2.VideoCapture] = None
        
        self._running = False
        self._capture_thread: Optional[threading.Thread] = None
        self.is_connected = False
        self.last_reconnect_attempt = 0.0
        self.current_backoff = config.reconnect_initial_delay_sec
        self.downtime_start_ts: Optional[float] = None
        self.total_downtime_sec = 0.0
        self.fps_actual = 0.0
        self._frame_counter = 0
        self._fps_last_calc = time.time()

    def start(self):
        """Start the background frame grabber producer thread."""
        if self._running:
            return
        self._running = True
        self._capture_thread = threading.Thread(target=self._producer_loop, daemon=True, name="FrameGrabberThread")
        self._capture_thread.start()
        logger.info(f"Video capture layer started for source: {self.source}")

    def stop(self):
        """Stop capture and release camera resources."""
        self._running = False
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        self._release_source()
        logger.info("Video capture layer stopped.")

    def _init_source(self) -> bool:
        if self.source == "synthetic":
            self.synthetic_stream = SyntheticShelfStream(
                width=self.config.width,
                height=self.config.height,
                target_fps=self.target_fps
            )
            self.is_connected = True
            return True
        
        try:
            # Handle numeric device index (e.g. "0") or RTSP/file URI
            src = int(self.source) if self.source.isdigit() else self.source
            self.cap = cv2.VideoCapture(src)
            if self.cap.isOpened():
                self.is_connected = True
                self.current_backoff = self.config.reconnect_initial_delay_sec
                if self.downtime_start_ts is not None:
                    downtime = time.time() - self.downtime_start_ts
                    self.total_downtime_sec += downtime
                    logger.info(f"Camera reconnected after {downtime:.2f}s downtime.")
                    self.downtime_start_ts = None
                return True
            else:
                self.is_connected = False
                return False
        except Exception as e:
            logger.error(f"Failed to open video source {self.source}: {e}")
            self.is_connected = False
            return False

    def _release_source(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.synthetic_stream = None
        self.is_connected = False

    def _producer_loop(self):
        frame_interval = 1.0 / max(1, self.target_fps)
        last_grab_time = 0.0

        while self._running:
            now = time.time()

            # Connection check & auto-reconnect backoff
            if not self.is_connected:
                if self.downtime_start_ts is None:
                    self.downtime_start_ts = now

                if now - self.last_reconnect_attempt >= self.current_backoff:
                    self.last_reconnect_attempt = now
                    logger.warning(f"Attempting camera reconnect (backoff: {self.current_backoff:.1f}s)...")
                    if self._init_source():
                        logger.info("Camera reconnected successfully.")
                    else:
                        self.current_backoff = min(
                            self.current_backoff * self.config.reconnect_backoff_factor,
                            self.config.reconnect_max_delay_sec
                        )
                time.sleep(0.1)
                continue

            # Frame rate regulation (sampling at target FPS)
            elapsed = now - last_grab_time
            if elapsed < frame_interval:
                time.sleep(max(0.001, frame_interval - elapsed))

            # Grab Frame
            grab_start = time.time()
            frame = None
            metadata = {}

            if self.source == "synthetic" and self.synthetic_stream is not None:
                ret, frame, metadata = self.synthetic_stream.read()
                if not ret:
                    continue
            elif self.cap is not None:
                ret, raw_frame = self.cap.read()
                if not ret or raw_frame is None:
                    logger.warning("Camera stream disconnected or frame grab failed.")
                    self._release_source()
                    continue
                frame = raw_frame
                metadata = {"frame_id": self._frame_counter, "timestamp": grab_start}
            else:
                self.is_connected = False
                continue

            last_grab_time = grab_start
            self._frame_counter += 1

            # Frame Normalization & Occlusion Check
            normalized_frame, norm_metrics = self.normalizer.normalize(frame)
            payload = {
                "raw_frame": frame,
                "frame": normalized_frame,
                "metadata": metadata,
                "norm_metrics": norm_metrics,
                "timestamp": grab_start,
                "frame_id": self._frame_counter
            }

            # Enforce Frame-Drop Policy (Ring Buffer size 2-3)
            # If buffer full, pop oldest frame so inference ALWAYS processes the freshest frame
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass

            try:
                self.frame_queue.put_nowait(payload)
            except queue.Full:
                pass

            # Calculate actual capture FPS
            if now - self._fps_last_calc >= 2.0:
                self.fps_actual = self._frame_counter / (now - self._fps_last_calc)
                self._frame_counter = 0
                self._fps_last_calc = now

    def get_latest_frame(self, timeout: float = 0.5) -> Optional[Dict[str, Any]]:
        """Consumer method: retrieve freshest normalized frame from queue."""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
