import cv2
import time
import threading
import queue
import logging
from urllib.parse import urlparse
from typing import Optional, Tuple, Dict, Any
import numpy as np

from backend.app.config import settings
from backend.app.capture.frame_normalizer import FrameNormalizer
from backend.app.capture.synthetic_stream import SyntheticShelfStream

logger = logging.getLogger("retailiq.capture")

def normalize_camera_source(src: Any) -> Tuple[Any, bool]:
    """
    Normalizes camera source strings:
    - Identifies integer device indices (e.g. '0', '1', 0) -> returns int
    - Detects 'synthetic' / 'demo' / 'mock' -> returns ('synthetic', True)
    - Normalizes phone IP Webcam URLs (prepends http://, adds /video if missing port path)
    """
    if src is None:
        return "synthetic", True
    
    s = str(src).strip()
    if s.lower() in ("synthetic", "demo", "mock", "simulated"):
        return "synthetic", True

    if s.isdigit():
        return int(s), False

    # Check if user entered URL
    if not s.startswith("http://") and not s.startswith("https://") and not s.startswith("rtsp://"):
        s = "http://" + s

    try:
        parsed = urlparse(s)
        # If port 8080 or 4747 provided without path or just '/', append '/video' for IP Webcam / DroidCam
        if (parsed.port == 8080 or ":8080" in s) and (not parsed.path or parsed.path in ("", "/")):
            s = s.rstrip("/") + "/video"
        elif (parsed.port == 4747 or ":4747" in s) and (not parsed.path or parsed.path in ("", "/")):
            s = s.rstrip("/") + "/video"
    except Exception:
        pass

    return s, False

class VideoCaptureService:
    """
    Module 1: Hardened Video Capture Layer (Live Mobile Camera / RTSP / USB / Synthetic)
    - High-throughput Producer/Consumer architecture with ring-buffer (frame-drop policy)
    - Auto-reconnect watchdog (triggers if no frame received for > 5.0s) with exponential backoff
    - Orientation normalization (0, 90, 180, 270 degrees) and resolution standardization
    - Multi-backend fallback for USB (DirectShow -> MSMF -> Default) & sensor warm-up retry
    - Diagnostic 'CAMERA DISCONNECTED / RECONNECTING' visual state instead of silent freeze
    - Dynamic source switching (IP Webcam / RTSP / Webcam / Synthetic) without system restart
    """
    def __init__(self, config=settings.video_capture):
        self.config = config
        self.source = str(config.source)
        self.target_fps = config.target_fps
        self.ring_buffer_size = max(1, min(config.ring_buffer_size, 3))
        self.rotation_deg = getattr(config, "rotation_deg", 0)
        self.target_width = config.width
        self.target_height = config.height
        
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
        self._lock = threading.Lock()
        
        self.is_connected = False
        self.is_reconnecting = False
        self.reconnect_count = 0
        self.last_reconnect_attempt = 0.0
        self.last_frame_received_ts = time.time()
        self.current_backoff = config.reconnect_initial_delay_sec
        self.downtime_start_ts: Optional[float] = None
        self.total_downtime_sec = 0.0
        self.fps_actual = 0.0
        self._frame_counter = 0
        self._fps_last_calc = time.time()
        self.last_error_message = ""
        self._consecutive_read_errors = 0

    def start(self):
        """Start the background frame grabber producer thread."""
        if self._running:
            return
        self._running = True
        self._capture_thread = threading.Thread(target=self._producer_loop, daemon=True, name="FrameGrabberThread")
        self._capture_thread.start()
        logger.info(f"Hardened video capture layer started for source: {self.source}")

    def stop(self):
        """Stop capture and release camera resources."""
        self._running = False
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
        self._release_source()
        logger.info("Video capture layer stopped.")

    def set_source(self, new_source: str, rotation_deg: int = 0) -> Dict[str, Any]:
        """Dynamically switch video source and orientation on the fly."""
        with self._lock:
            cleaned_src, is_syn = normalize_camera_source(new_source)
            logger.info(f"Switching video source from '{self.source}' to '{cleaned_src}', rotation={rotation_deg}°")
            self.source = str(cleaned_src)
            self.rotation_deg = rotation_deg
            self._release_source()
            self.reconnect_count = 0
            self.current_backoff = self.config.reconnect_initial_delay_sec
            self.last_reconnect_attempt = 0.0
            self.downtime_start_ts = time.time()
            self.last_frame_received_ts = time.time()
            self._consecutive_read_errors = 0
            
            # Clear frame queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break

            success = self._init_source()
            return {
                "source": self.source,
                "rotation_deg": self.rotation_deg,
                "is_connected": self.is_connected,
                "is_synthetic": self.is_synthetic(),
                "status": "connected" if success else "connecting",
                "message": f"Source set to {self.source}" if success else f"Connecting to {self.source}..."
            }

    def is_synthetic(self) -> bool:
        return str(self.source).lower() in ("synthetic", "demo", "mock", "simulated")

    def _init_source(self) -> bool:
        if self.is_synthetic():
            self.synthetic_stream = SyntheticShelfStream(
                width=self.target_width,
                height=self.target_height,
                target_fps=self.target_fps
            )
            self.is_connected = True
            self.is_reconnecting = False
            self.last_frame_received_ts = time.time()
            self.last_error_message = ""
            self._consecutive_read_errors = 0
            logger.info("Synthetic demo stream initialized.")
            return True
        
        parsed_src, _ = normalize_camera_source(self.source)
        
        try:
            # Handle USB camera index
            if isinstance(parsed_src, int):
                # Try DirectShow first on Windows, then default
                cap = None
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if hasattr(cv2, "CAP_DSHOW") else [cv2.CAP_ANY]
                for backend in backends:
                    try:
                        temp_cap = cv2.VideoCapture(parsed_src, backend)
                        if temp_cap.isOpened():
                            cap = temp_cap
                            break
                        temp_cap.release()
                    except Exception:
                        continue
                self.cap = cap if cap is not None else cv2.VideoCapture(parsed_src)
            else:
                # Handle IP Webcam / RTSP URL
                self.cap = cv2.VideoCapture(str(parsed_src))

            if self.cap is not None and self.cap.isOpened():
                try:
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                # Warm up hardware sensor / network buffer by grabbing a test frame
                warmed_up = False
                for _ in range(6):
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None and test_frame.size > 0:
                        warmed_up = True
                        break
                    time.sleep(0.08)

                if warmed_up:
                    self.is_connected = True
                    self.is_reconnecting = False
                    self.current_backoff = self.config.reconnect_initial_delay_sec
                    self.last_frame_received_ts = time.time()
                    self.last_error_message = ""
                    self._consecutive_read_errors = 0
                    
                    if self.downtime_start_ts is not None:
                        downtime = time.time() - self.downtime_start_ts
                        self.total_downtime_sec += downtime
                        logger.info(f"Camera '{self.source}' successfully connected after {downtime:.2f}s.")
                        self.downtime_start_ts = None
                    return True
                else:
                    self.is_connected = False
                    self.is_reconnecting = True
                    self.last_error_message = f"Camera device '{self.source}' opened but produced no initial frame."
                    logger.warning(self.last_error_message)
                    return False
            else:
                self.is_connected = False
                self.is_reconnecting = True
                self.last_error_message = f"Unable to open camera stream at '{self.source}'. Check URL/Index."
                return False
        except Exception as e:
            self.is_connected = False
            self.is_reconnecting = True
            self.last_error_message = str(e)
            logger.error(f"Exception opening video source '{self.source}': {e}")
            return False

    def _release_source(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.synthetic_stream = None
        self.is_connected = False

    def _apply_rotation_and_scaling(self, frame: np.ndarray) -> np.ndarray:
        """Standardize frame orientation and dimensions to target width/height."""
        if frame is None or frame.size == 0:
            return frame

        # Apply rotation if specified
        if self.rotation_deg == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation_deg == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotation_deg == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        h, w = frame.shape[:2]
        if (w != self.target_width or h != self.target_height) and self.target_width > 0 and self.target_height > 0:
            frame = cv2.resize(frame, (self.target_width, self.target_height), interpolation=cv2.INTER_LINEAR)

        return frame

    def _generate_disconnected_frame(self) -> np.ndarray:
        """
        Renders a diagnostic disconnected status frame so the video feed clearly
        indicates camera disconnect & retry state rather than freezing silently.
        """
        w, h = self.target_width, self.target_height
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        canvas[:] = (20, 24, 30) # Dark slate background

        # Red pulsing header bar
        cv2.rectangle(canvas, (0, 0), (w, 50), (35, 20, 30), -1)
        cv2.line(canvas, (0, 50), (w, 50), (60, 40, 220), 2)

        # Warning icon/text
        cv2.circle(canvas, (40, 25), 10, (50, 50, 240), -1)
        cv2.putText(canvas, "!", (37, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(canvas, "LIVE CAMERA FEED CONNECTING / RECONNECTING", (65, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (80, 80, 255), 2)

        # Center diagnostic box
        box_w, box_h = min(720, w - 60), 230
        bx = (w - box_w) // 2
        by = (h - box_h) // 2
        cv2.rectangle(canvas, (bx, by), (bx + box_w, by + box_h), (28, 33, 42), -1)
        cv2.rectangle(canvas, (bx, by), (bx + box_w, by + box_h), (50, 60, 75), 1)

        cv2.putText(canvas, "Active Camera Watchdog Monitoring Feed", (bx + 25, by + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
        
        src_label = f"Configured Target Source: {self.source}"
        if len(src_label) > 65:
            src_label = src_label[:62] + "..."
        cv2.putText(canvas, src_label, (bx + 25, by + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 220, 255), 1)

        retrying_str = f"Reconnection Attempt #{self.reconnect_count} (Backoff: {self.current_backoff:.1f}s)"
        cv2.putText(canvas, retrying_str, (bx + 25, by + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (240, 180, 50), 1)

        if self.last_error_message:
            err_str = f"Status: {self.last_error_message[:68]}"
            cv2.putText(canvas, err_str, (bx + 25, by + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 240), 1)

        tip_str = "Tips: For Phone Cam, ensure IP Webcam server is started (http://<ip>:8080/video)"
        cv2.putText(canvas, tip_str, (bx + 25, by + 175), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (150, 160, 175), 1)
        tip_str2 = "For USB Webcam, select Index '0'. Or click 'Reset to Simulation' in UI."
        cv2.putText(canvas, tip_str2, (bx + 25, by + 202), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (150, 160, 175), 1)

        # Footer timestamp
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(canvas, f"Edge Node Time: {now_str}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 110, 120), 1)

        return canvas

    def _producer_loop(self):
        frame_interval = 1.0 / max(1, self.target_fps)
        last_grab_time = 0.0

        while self._running:
            now = time.time()

            # Watchdog check: If connected to live stream but no frames arrived for > 5.0 seconds -> trigger disconnect
            if self.is_connected and not self.is_synthetic():
                if now - self.last_frame_received_ts > 5.0:
                    logger.warning(f"Watchdog: No frame received from '{self.source}' for >5.0s. Marking disconnected.")
                    self.is_connected = False
                    self.is_reconnecting = True
                    self._release_source()

            # Auto-Reconnect with Exponential Backoff
            if not self.is_connected:
                if self.downtime_start_ts is None:
                    self.downtime_start_ts = now

                if now - self.last_reconnect_attempt >= self.current_backoff:
                    self.last_reconnect_attempt = now
                    self.reconnect_count += 1
                    logger.warning(f"Attempting camera reconnect #{self.reconnect_count} to '{self.source}' (backoff: {self.current_backoff:.1f}s)...")
                    
                    if self._init_source():
                        logger.info(f"Camera '{self.source}' successfully reconnected.")
                        self.is_connected = True
                        self.is_reconnecting = False
                        self.reconnect_count = 0
                        self._consecutive_read_errors = 0
                    else:
                        self.current_backoff = min(
                            self.current_backoff * self.config.reconnect_backoff_factor,
                            self.config.reconnect_max_delay_sec
                        )

                # Push a diagnostic disconnected frame into the buffer so the UI displays the reconnect state
                disc_frame = self._generate_disconnected_frame()
                norm_frame, norm_metrics = self.normalizer.normalize(disc_frame)
                payload = {
                    "raw_frame": disc_frame,
                    "frame": norm_frame,
                    "metadata": {"is_disconnected": True, "source": self.source, "reconnect_count": self.reconnect_count},
                    "norm_metrics": norm_metrics,
                    "timestamp": now,
                    "frame_id": self._frame_counter,
                    "is_camera_disconnected": True
                }
                
                # Push freshest frame to queue
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                try:
                    self.frame_queue.put_nowait(payload)
                except queue.Full:
                    pass

                time.sleep(0.12)
                continue

            # Frame rate regulation
            elapsed = now - last_grab_time
            if elapsed < frame_interval:
                time.sleep(max(0.001, frame_interval - elapsed))

            # Grab Frame from active source
            grab_start = time.time()
            frame = None
            metadata = {}

            if self.is_synthetic() and self.synthetic_stream is not None:
                ret, frame, metadata = self.synthetic_stream.read()
                if not ret or frame is None:
                    time.sleep(0.05)
                    continue
                self.last_frame_received_ts = grab_start
                self._consecutive_read_errors = 0
            elif self.cap is not None:
                try:
                    ret, raw_frame = self.cap.read()
                    if not ret or raw_frame is None or raw_frame.size == 0:
                        self._consecutive_read_errors += 1
                        if self._consecutive_read_errors >= 4:
                            logger.warning(f"Multiple consecutive frame grab failures from '{self.source}'. Releasing to trigger reconnect.")
                            self.is_connected = False
                            self.is_reconnecting = True
                            self._release_source()
                        else:
                            time.sleep(0.05)
                        continue
                    
                    frame = raw_frame
                    self.last_frame_received_ts = grab_start
                    self._consecutive_read_errors = 0
                    metadata = {"frame_id": self._frame_counter, "timestamp": grab_start, "source": self.source}
                except Exception as e:
                    logger.warning(f"Exception during frame capture: {e}")
                    self._consecutive_read_errors += 1
                    if self._consecutive_read_errors >= 3:
                        self.is_connected = False
                        self.is_reconnecting = True
                        self._release_source()
                    continue
            else:
                self.is_connected = False
                continue

            last_grab_time = grab_start
            self._frame_counter += 1

            # Standardize rotation and resolution
            frame = self._apply_rotation_and_scaling(frame)

            # Frame Normalization & Occlusion Check
            normalized_frame, norm_metrics = self.normalizer.normalize(frame)
            payload = {
                "raw_frame": frame,
                "frame": normalized_frame,
                "metadata": metadata,
                "norm_metrics": norm_metrics,
                "timestamp": grab_start,
                "frame_id": self._frame_counter,
                "is_camera_disconnected": False
            }

            # Producer Ring-buffer write (drop oldest if full)
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass

            try:
                self.frame_queue.put_nowait(payload)
            except queue.Full:
                pass

            # Calculate Actual Capture FPS
            now_fps = time.time()
            if now_fps - self._fps_last_calc >= 2.0:
                self.fps_actual = round(self._frame_counter / (now_fps - self._fps_last_calc), 1)
                self._frame_counter = 0
                self._fps_last_calc = now_fps

    def get_latest_frame(self, timeout: float = 0.3) -> Optional[Dict[str, Any]]:
        """Consumer method: Grab latest available frame from queue."""
        try:
            latest = self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        while True:
            try:
                latest = self.frame_queue.get_nowait()
            except queue.Empty:
                return latest

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state inspection for health check & frontend HUD."""
        return {
            "source": self.source,
            "is_synthetic": self.is_synthetic(),
            "is_connected": self.is_connected,
            "is_reconnecting": self.is_reconnecting,
            "rotation_deg": self.rotation_deg,
            "fps_actual": self.fps_actual,
            "reconnect_attempts": self.reconnect_count,
            "current_backoff_sec": self.current_backoff,
            "last_error": self.last_error_message,
            "total_downtime_sec": round(self.total_downtime_sec + (time.time() - self.downtime_start_ts if self.downtime_start_ts else 0.0), 1)
        }
