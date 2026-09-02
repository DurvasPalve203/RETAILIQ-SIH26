import time
import json
import uuid
import threading
import logging
from typing import Dict, List, Any, Optional, Tuple

from backend.app.config import settings
from backend.app.database import get_db_connection
from backend.app.alerts.hardware_drivers import PhysicalAlertHardwareDriver
from backend.app.alerts.sms_driver import Sim800lGsmDriver
from backend.app.sync.mqtt_sync import SyncService

logger = logging.getLogger("retailiq.alerts")

class AlertManager:
    """
    Module D: Central Multi-Level Alert & Notification Subsystem
    - Centralizes severity classification and state machine for both shelf and queue events
    - Dispatches to 5 fan-out channels: Dashboard, MQTT, Buzzer, RGB LED, SMS (SIM800L)
    - Manages lifecycle states: NEW -> ACKNOWLEDGED -> ESCALATED -> RESOLVED
    - Automatic escalation watchdog for unacknowledged critical/high alerts
    - Physical hardware priority rate-limiting (reflects single highest active severity)
    """
    def __init__(self, config=settings.alert_subsystem):
        self.config = config
        self.escalation_timeout = config.escalation_timeout_sec
        self.ack_cooldown = config.ack_cooldown_sec
        
        # Hardware channel drivers
        ch = config.channels
        self.hardware_driver = PhysicalAlertHardwareDriver(
            buzzer_pin=ch.buzzer_gpio_pin,
            rgb_pins=ch.rgb_led_pins
        )
        self.sms_driver = Sim800lGsmDriver(
            port=ch.sms_uart_port,
            baudrate=ch.sms_uart_baudrate,
            manager_phone=ch.store_manager_phone
        )
        self.sync_service = SyncService()

        # In-memory active alerts cache: {alert_id: AlertDict}
        self._active_alerts: Dict[str, Dict[str, Any]] = {}
        # Cooldown map: {zone_id_source: float (cooldown_expiry_timestamp)}
        self._cooldowns: Dict[str, float] = {}

        self._running = False
        self._watchdog_thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._watchdog_thread = threading.Thread(target=self._escalation_watchdog_loop, daemon=True, name="AlertEscalationWatchdog")
        self._watchdog_thread.start()
        logger.info("Alert Manager service started.")

    def stop(self):
        self._running = False
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=2.0)
        logger.info("Alert Manager service stopped.")

    def process_raw_event(self, source_module: str, event_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Receives raw events from Shelf or Queue pipelines, classifies severity,
        checks deduplication/cooldown, creates/updates alert, and fans out.
        """
        now = time.time()
        zid = data.get("zone_id", "unknown_zone")
        cooldown_key = f"{source_module}:{zid}:{event_type}"

        # 1. Classify Severity & Priority
        severity, title, message, est_lost_sales = self._classify_severity(source_module, event_type, data)
        if not severity:
            return None

        # Check if zone is in acknowledgement cooldown
        if cooldown_key in self._cooldowns and now < self._cooldowns[cooldown_key]:
            return None

        alert_id = f"alt-{source_module[:2]}-{zid}-{event_type[:4]}"

        # 2. If alert already exists and is active, update
        if alert_id in self._active_alerts:
            existing = self._active_alerts[alert_id]
            if existing["state"] in ["NEW", "ACKNOWLEDGED", "ESCALATED"]:
                existing["title"] = title
                existing["message"] = message
                existing["severity"] = severity
                existing["details"] = data
                existing["priority_score"] = self._calculate_priority_score(severity, data)
                return existing

        # 3. Create NEW Alert
        priority_score = self._calculate_priority_score(severity, data)
        alert = {
            "alert_id": alert_id,
            "source_module": source_module, # 'shelf' | 'queue' | 'system'
            "zone_id": zid,
            "zone_label": data.get("zone_label", zid),
            "title": title,
            "message": message,
            "severity": severity, # 'CRITICAL' | 'HIGH' | 'LOW'
            "state": "NEW",
            "type": event_type,
            "eta_minutes": data.get("eta_minutes", 0.0),
            "priority_score": priority_score,
            "estimated_lost_sales": est_lost_sales,
            "created_at": now,
            "acknowledged_at": None,
            "resolved_at": None,
            "escalate_count": 0,
            "escalation_remaining_sec": self.escalation_timeout,
            "details": data
        }

        self._active_alerts[alert_id] = alert
        self._persist_alert(alert)

        # 4. Fan out to active channels
        self._dispatch_channels(alert, is_initial=True)
        self._update_hardware_indicators()

        return alert

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "store_staff") -> Optional[Dict[str, Any]]:
        """
        Staff acknowledges alert: transitions state from NEW/ESCALATED -> ACKNOWLEDGED.
        Stops physical buzzer pulsing, switches LED to solid, sets cooldown.
        """
        now = time.time()
        alert = self._active_alerts.get(alert_id)
        if not alert:
            return None

        alert["state"] = "ACKNOWLEDGED"
        alert["acknowledged_at"] = now
        alert["acknowledged_by"] = acknowledged_by
        alert["escalation_remaining_sec"] = None

        # Set cooldown for this zone & source to prevent instant re-alerting
        cooldown_key = f"{alert['source_module']}:{alert['zone_id']}:{alert['type']}"
        self._cooldowns[cooldown_key] = now + self.ack_cooldown

        self._update_alert_db(alert)
        self.hardware_driver.acknowledge_signals()
        self._update_hardware_indicators()

        # Log delivery
        self._log_delivery(alert_id, "dashboard", f"Acknowledged by {acknowledged_by}")
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return alert

    def resolve_alert(self, alert_id: str, reason: str = "restock_detected") -> Optional[Dict[str, Any]]:
        """
        Alert resolved: underlying condition cleared or manual override.
        Closes alert, updates DB, resets hardware signals.
        """
        now = time.time()
        alert = self._active_alerts.pop(alert_id, None)
        if not alert:
            return None

        alert["state"] = "RESOLVED"
        alert["resolved_at"] = now
        alert["resolve_reason"] = reason

        self._update_alert_db(alert)
        self._update_hardware_indicators()
        self._log_delivery(alert_id, "dashboard", f"Resolved: {reason}")
        logger.info(f"Alert {alert_id} resolved ({reason})")
        return alert

    def _classify_severity(self, source: str, event_type: str, data: Dict[str, Any]) -> Tuple[Optional[str], str, str, float]:
        """Classify severity according to Section D.2 rules."""
        if source == "shelf":
            if event_type == "immediate_stockout" or event_type == "stock_out":
                # Shelf empty now
                sev = "CRITICAL" if data.get("is_top_sku", True) else "HIGH"
                zname = data.get("zone_label", data.get("zone_id", "Shelf"))
                title = f"{zname} — Immediate Stock-Out"
                msg = f"Zero shelf stock detected. Immediate replenishment required."
                lost_dollars = data.get("estimated_lost_sales", 15.0)
                return sev, title, msg, lost_dollars

            elif event_type == "predictive_stockout" or event_type == "depletion_warning":
                eta = data.get("eta_minutes", 30.0)
                sev = "HIGH" if eta <= 15.0 else ("HIGH" if eta <= 30.0 else "LOW")
                zname = data.get("zone_label", data.get("zone_id", "Shelf"))
                title = f"{zname} — Predicted Stock-Out in {int(eta)}m"
                msg = f"High velocity depletion. Empty projected in {int(eta)} min."
                return sev, title, msg, 0.0

        elif source == "queue":
            wait_sec = data.get("estimated_wait_seconds", 0.0)
            q_len = data.get("queue_length", 0)
            growth = data.get("growth_rate", 0.0)
            zname = data.get("zone_label", "Checkout Counter")

            if wait_sec >= self.config.channels.buzzer_gpio_pin or wait_sec >= 600.0: # >= 10m
                title = f"{zname} — Critical Queue Wait Time ({int(wait_sec/60)}m)"
                msg = f"Queue length is {q_len} customers with estimated wait exceeding 10 minutes. Open additional billing counter immediately."
                return "CRITICAL", title, msg, 0.0

            elif wait_sec >= 300.0 or (growth > 2.0 and q_len >= 3): # >= 5m or rapid surge
                title = f"{zname} — Long Checkout Wait ({int(wait_sec/60)}m)"
                msg = f"Queue wait is {int(wait_sec/60)}m with {q_len} shoppers in line (Growth: +{growth}/min)."
                return "HIGH", title, msg, 0.0

            elif q_len >= 2:
                title = f"{zname} — Queue Forming ({q_len} in line)"
                msg = f"Estimated wait is {data.get('wait_minutes_formatted', f'{int(wait_sec)}s')}."
                return "LOW", title, msg, 0.0

        return None, "", "", 0.0

    def _calculate_priority_score(self, severity: str, data: Dict[str, Any]) -> float:
        base = {"CRITICAL": 100.0, "HIGH": 65.0, "LOW": 30.0}.get(severity, 50.0)
        eta = data.get("eta_minutes", 0.0)
        return round(base + (max(0.0, 30.0 - eta) * 0.5), 1)

    def _dispatch_channels(self, alert: Dict[str, Any], is_initial: bool = True):
        """Fan out alert to configured channels (Dashboard, MQTT, Buzzer, LED, SMS)."""
        aid = alert["alert_id"]
        sev = alert["severity"]
        title = alert["title"]
        msg = alert["message"]
        zid = alert["zone_id"]

        # 1. Dashboard WebSocket Channel
        self._log_delivery(aid, "dashboard", "dispatched_to_websocket")

        # 2. MQTT Channel
        if self.config.channels.mqtt_enabled:
            mqtt_topic = f"{self.config.channels.mqtt_topic_prefix}/{zid}"
            self.sync_service.enqueue_event(f"alerts/{zid}", alert)
            self._log_delivery(aid, "mqtt", f"published_to_{mqtt_topic}")

        # 3. SMS SIM800L Channel: Dispatched for CRITICAL and ESCALATED alerts only
        if self.config.channels.sms_enabled and (sev == "CRITICAL" or alert["state"] == "ESCALATED"):
            sms_res = self.sms_driver.send_emergency_sms(title, msg, sev)
            self._log_delivery(aid, "sms", sms_res.get("status", "sent"), payload=sms_res)

    def _update_hardware_indicators(self):
        """Find highest severity active alert and set physical Buzzer & RGB LED."""
        if not self._active_alerts:
            self.hardware_driver.set_alert_signals(None)
            return

        # Order: CRITICAL > HIGH > LOW
        has_critical = any(a["severity"] == "CRITICAL" and a["state"] != "RESOLVED" for a in self._active_alerts.values())
        has_high = any(a["severity"] == "HIGH" and a["state"] != "RESOLVED" for a in self._active_alerts.values())

        if has_critical:
            highest_sev = "CRITICAL"
            crit_alerts = [a for a in self._active_alerts.values() if a["severity"] == "CRITICAL"]
            state = "NEW" if any(a["state"] in ["NEW", "ESCALATED"] for a in crit_alerts) else "ACKNOWLEDGED"
        elif has_high:
            highest_sev = "HIGH"
            high_alerts = [a for a in self._active_alerts.values() if a["severity"] == "HIGH"]
            state = "NEW" if any(a["state"] in ["NEW", "ESCALATED"] for a in high_alerts) else "ACKNOWLEDGED"
        else:
            highest_sev = "LOW"
            state = "NEW"

        self.hardware_driver.set_alert_signals(highest_sev, state=state)

    def _escalation_watchdog_loop(self):
        """Background watchdog: checks for unacknowledged alerts exceeding escalation timeout."""
        while self._running:
            try:
                time.sleep(2.0)
                now = time.time()

                for aid, alert in list(self._active_alerts.items()):
                    if alert["state"] == "NEW":
                        elapsed = now - alert["created_at"]
                        remaining = max(0.0, self.escalation_timeout - elapsed)
                        alert["escalation_remaining_sec"] = round(remaining, 1)

                        if elapsed >= self.escalation_timeout:
                            # Escalate alert!
                            alert["state"] = "ESCALATED"
                            alert["escalate_count"] += 1
                            if alert["severity"] == "HIGH":
                                alert["severity"] = "CRITICAL"
                            alert["title"] = f"[ESCALATED] {alert['title']}"
                            alert["escalation_remaining_sec"] = None

                            logger.warning(f"Alert {aid} escalated to CRITICAL due to unacknowledged timeout ({self.escalation_timeout}s)")
                            self._update_alert_db(alert)
                            self._dispatch_channels(alert, is_initial=False)
                            self._update_hardware_indicators()
            except Exception:
                pass

    def get_ranked_active_alerts(self) -> List[Dict[str, Any]]:
        """Return list of active alerts sorted by priority score descending."""
        alerts = list(self._active_alerts.values())
        alerts.sort(key=lambda a: a.get("priority_score", 0.0), reverse=True)
        return alerts

    def get_hardware_status(self) -> Dict[str, Any]:
        hw_stat = self.hardware_driver.get_hardware_status()
        sms_stat = self.sms_driver.get_status()
        return {
            "dashboard_active": True,
            "mqtt_connected": self.sync_service.is_connected,
            "mqtt_broker": f"{settings.sync_layer.mqtt_broker}:{settings.sync_layer.mqtt_port}",
            "buzzer_enabled": self.config.channels.buzzer_enabled,
            "buzzer_active": hw_stat["buzzer_active"],
            "buzzer_pattern": hw_stat["buzzer_pattern"],
            "rgb_led_enabled": self.config.channels.rgb_led_enabled,
            "rgb_led_color": hw_stat["led_color"],
            "rgb_led_state": hw_stat["led_mode"],
            "sms_enabled": self.config.channels.sms_enabled,
            "sms_status": "READY" if sms_stat["hardware_connected"] else "EMULATED",
            "sms_manager_phone": sms_stat["manager_phone"],
            "last_sms_event": sms_stat["last_event"]
        }

    def _persist_alert(self, alert: Dict[str, Any]):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (alert_id, source_module, zone_id, title, message, severity, state, created_at, escalate_count, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alert_id) DO UPDATE SET
                    title=excluded.title,
                    message=excluded.message,
                    severity=excluded.severity,
                    details_json=excluded.details_json;
            """, (alert["alert_id"], alert["source_module"], alert["zone_id"], alert["title"], alert["message"],
                  alert["severity"], alert["state"], alert["created_at"], alert["escalate_count"], json.dumps(alert.get("details", {}))))
            conn.commit()
        except Exception:
            pass

    def _update_alert_db(self, alert: Dict[str, Any]):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE alerts
                SET severity = ?, state = ?, acknowledged_at = ?, resolved_at = ?, escalate_count = ?
                WHERE alert_id = ?;
            """, (alert["severity"], alert["state"], alert.get("acknowledged_at"), alert.get("resolved_at"), alert["escalate_count"], alert["alert_id"]))
            conn.commit()
        except Exception:
            pass

    def _log_delivery(self, alert_id: str, channel: str, status: str, payload: Optional[Dict[str, Any]] = None):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            did = f"deliv-{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT INTO alert_deliveries (delivery_id, alert_id, channel, status, sent_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (did, alert_id, channel, status, time.time(), json.dumps(payload or {})))
            conn.commit()
        except Exception:
            pass
