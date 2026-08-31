import time
import os
import psutil
import threading
from typing import Dict, Any, List, Optional
from collections import deque

class SystemMetricsService:
    """
    Module 7: Edge System Metrics & Observability Tracker
    - Tracks capture and inference FPS with rolling windows
    - Measures end-to-end pipeline loop processing latency
    - Monitors active queue lengths, alert counts, and offline sync backlog
    - Measures host CPU %, RAM usage, and camera uptime/downtime
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SystemMetricsService, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.start_time = time.time()
        self._latencies_ms = deque(maxlen=60)
        self._fps_capture = 0.0
        self._fps_inference = 0.0
        self.total_frames_processed = 0
        self.total_frames_dropped = 0
        self.pipeline_crash_count = 0
        self.last_pipeline_error: str = ""
        self.last_pipeline_error_ts: float = 0.0
        self.sync_failed_count = 0
        self.total_sync_records_sent = 0
        self._process = psutil.Process(os.getpid())

    def record_loop_latency(self, latency_ms: float):
        self._latencies_ms.append(latency_ms)
        self.total_frames_processed += 1

    def record_pipeline_error(self, err_msg: str):
        self.pipeline_crash_count += 1
        self.last_pipeline_error = err_msg
        self.last_pipeline_error_ts = time.time()

    def set_fps(self, capture_fps: float, inference_fps: float):
        self._fps_capture = round(capture_fps, 1)
        self._fps_inference = round(inference_fps, 1)

    def record_sync_success(self, count: int = 1):
        self.total_sync_records_sent += count

    def record_sync_failure(self):
        self.sync_failed_count += 1

    def get_metrics_summary(self) -> Dict[str, Any]:
        now = time.time()
        uptime_sec = round(now - self.start_time, 1)
        
        avg_latency = round(sum(self._latencies_ms) / len(self._latencies_ms), 2) if self._latencies_ms else 0.0
        max_latency = round(max(self._latencies_ms), 2) if self._latencies_ms else 0.0

        # Memory and CPU stats
        try:
            mem_info = self._process.memory_info()
            mem_mb = round(mem_info.rss / (1024 * 1024), 1)
            cpu_pct = round(self._process.cpu_percent(interval=None), 1)
        except Exception:
            mem_mb = 0.0
            cpu_pct = 0.0

        try:
            system_cpu = round(psutil.cpu_percent(interval=None), 1)
            system_mem = psutil.virtual_memory()
            sys_mem_pct = round(system_mem.percent, 1)
        except Exception:
            system_cpu = 0.0
            sys_mem_pct = 0.0

        return {
            "uptime_seconds": uptime_sec,
            "fps_capture": self._fps_capture,
            "fps_inference": self._fps_inference,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": max_latency,
            "total_frames_processed": self.total_frames_processed,
            "pipeline_crashes": self.pipeline_crash_count,
            "last_error": self.last_error_dict(),
            "sync_sent_count": self.total_sync_records_sent,
            "sync_failed_count": self.sync_failed_count,
            "process_memory_mb": mem_mb,
            "process_cpu_pct": cpu_pct,
            "system_cpu_pct": system_cpu,
            "system_memory_pct": sys_mem_pct,
            "timestamp": now
        }

    def last_error_dict(self) -> Optional[Dict[str, Any]]:
        if not self.last_pipeline_error:
            return None
        return {
            "message": self.last_pipeline_error,
            "seconds_ago": round(time.time() - self.last_pipeline_error_ts, 1)
        }

metrics_service = SystemMetricsService()
