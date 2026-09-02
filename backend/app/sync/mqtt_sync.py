import time
import json
import threading
import logging
import paho.mqtt.client as mqtt
from typing import Dict, Any, Optional
from backend.app.config import settings
from backend.app.database import get_db_connection

logger = logging.getLogger("retailiq.sync")

class SyncService:
    """
    Module 8: Sync Layer (Offline-First MQTT & Cloud Event Sync)
    - Buffers events to local SQLite offline_sync_queue
    - Flushes structured telemetry via MQTT when online
    - Exponential backoff retry on network disconnection
    - Zero raw video egress; structured metrics only
    """
    def __init__(self, config=settings.sync_layer, node_id=settings.edge_device.node_id):
        self.config = config
        self.node_id = node_id
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None
        self.mqtt_client = mqtt.Client()
        self.is_connected = False
        self.backoff_delay = config.retry_interval_sec
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.is_connected = True
                logger.info(f"Connected to MQTT broker {self.config.mqtt_broker}:{self.config.mqtt_port}")
            else:
                self.is_connected = False
        def on_disconnect(client, userdata, rc):
            self.is_connected = False
            
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_disconnect = on_disconnect

    def start(self):
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_worker, daemon=True, name="MqttSyncWorker")
        self._sync_thread.start()

    def stop(self):
        self._running = False
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=2.0)

    def enqueue_event(self, topic_suffix: str, payload: Dict[str, Any]):
        """Persist structured event locally to offline buffer (source of truth)."""
        topic = f"{self.config.mqtt_topic_prefix}/{topic_suffix}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO offline_sync_queue (payload_json, topic, status, retry_count, created_at)
            VALUES (?, ?, 'pending', 0, ?)
        """, (json.dumps(payload), topic, time.time()))
        conn.commit()

    def _sync_worker(self):
        while self._running:
            time.sleep(self.backoff_delay)
            if not self.config.mqtt_enabled:
                continue

            try:
                # Check for pending records
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT queue_id, payload_json, topic, retry_count
                    FROM offline_sync_queue
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (self.config.batch_sync_size,))
                records = cursor.fetchall()

                if not records:
                    continue

                # Try to connect if not connected
                if not self.is_connected:
                    try:
                        self.mqtt_client.connect(self.config.mqtt_broker, self.config.mqtt_port, 10)
                        self.mqtt_client.loop_start()
                        time.sleep(0.5) # Wait for connect callback
                    except Exception as e:
                        logger.warning(f"MQTT connect failed: {e}")
                        raise e

                if not self.is_connected:
                    raise Exception("Not connected to MQTT broker after attempt")

                # If connected, publish each record
                for r in records:
                    qid = r["queue_id"]
                    topic = r["topic"]
                    payload = r["payload_json"]
                    msg = self.mqtt_client.publish(topic, payload, qos=1)
                    msg.wait_for_publish(timeout=2.0)
                    if msg.is_published():
                        # Mark synced
                        cursor.execute("""
                            UPDATE offline_sync_queue
                            SET status = 'synced', synced_at = ?
                            WHERE queue_id = ?
                        """, (time.time(), qid))
                    else:
                        raise Exception("MQTT publish failed or timed out")
                conn.commit()
                self.backoff_delay = self.config.retry_interval_sec

            except Exception as e:
                logger.warning(f"Sync failed, keeping records pending: {e}")
                self.is_connected = False
                self.backoff_delay = min(60.0, self.backoff_delay * 1.5)

    def get_sync_status(self) -> Dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as pending_cnt FROM offline_sync_queue WHERE status = 'pending'")
        pending = cursor.fetchone()["pending_cnt"]
        return {
            "mqtt_enabled": self.config.mqtt_enabled,
            "is_connected": self.is_connected,
            "pending_offline_records": pending,
            "broker": f"{self.config.mqtt_broker}:{self.config.mqtt_port}"
        }
