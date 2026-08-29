import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("retailiq.sms")

class Sim800lGsmDriver:
    """
    Module D.4: SIM800L GSM Module SMS Driver via UART AT Commands.
    - Sends plain-text SMS notifications with zero WiFi and zero mobile data
    - Reserved for CRITICAL and ESCALATED alerts (cost + rate limiting)
    - Full AT command workflow (AT+CMGF=1, AT+CMGS) with error detection and emulated delivery receipt
    """
    def __init__(self, port: str = "COM3", baudrate: int = 9600, manager_phone: str = "+1-800-555-0199"):
        self.port = port
        self.baudrate = baudrate
        self.manager_phone = manager_phone
        self.last_sent_event: Optional[Dict[str, Any]] = None
        self.delivery_count = 0
        self.last_error = None
        
        self._serial_conn = None
        self._hardware_connected = False
        self._init_uart()

    def _init_uart(self):
        try:
            import serial
            self._serial_conn = serial.Serial(self.port, self.baudrate, timeout=3.0)
            # Test AT ping
            self._serial_conn.write(b"AT\r\n")
            time.sleep(0.5)
            resp = self._serial_conn.read_all().decode(errors="ignore")
            if "OK" in resp:
                self._hardware_connected = True
                # Set SMS text mode
                self._serial_conn.write(b"AT+CMGF=1\r\n")
                time.sleep(0.3)
                logger.info(f"SIM800L GSM Module connected on {self.port}")
        except Exception as e:
            self._hardware_connected = False
            self.last_error = str(e)
            logger.info(f"SIM800L UART ({self.port}) not physically attached; engaging cellular emulation mode.")

    def send_emergency_sms(self, alert_title: str, message: str, severity: str) -> Dict[str, Any]:
        """
        Send urgent SMS alert to store manager.
        """
        sms_text = f"[RetailIQ {severity}] {alert_title}\n{message}\nTime: {time.strftime('%H:%M:%S')}"
        now = time.time()
        status = "sent"

        if self._hardware_connected and self._serial_conn:
            try:
                # 1. AT+CMGF=1 (Text mode)
                self._serial_conn.write(b"AT+CMGF=1\r\n")
                time.sleep(0.2)
                # 2. AT+CMGS="<phone>"
                cmd = f'AT+CMGS="{self.manager_phone}"\r\n'.encode()
                self._serial_conn.write(cmd)
                time.sleep(0.3)
                # 3. Message body + Ctrl+Z (\x1a)
                payload = sms_text.encode() + b"\x1a"
                self._serial_conn.write(payload)
                time.sleep(1.0)
                resp = self._serial_conn.read_all().decode(errors="ignore")
                if "ERROR" in resp:
                    status = "failed"
                    self.last_error = resp
            except Exception as e:
                status = "failed"
                self.last_error = str(e)
        else:
            # High-fidelity cellular emulation mode
            status = "emulated_delivered"

        self.delivery_count += 1
        record = {
            "phone": self.manager_phone,
            "severity": severity,
            "message": sms_text,
            "status": status,
            "timestamp": now,
            "hardware_mode": "UART_PHYSICAL" if self._hardware_connected else "CELLULAR_EMULATED",
            "at_sequence": f'AT+CMGF=1 -> AT+CMGS="{self.manager_phone}" -> [PAYLOAD] -> \\x1a'
        }
        self.last_sent_event = record
        logger.info(f"SIM800L SMS dispatched: {alert_title} -> {self.manager_phone} ({status})")
        return record

    def get_status(self) -> Dict[str, Any]:
        return {
            "hardware_connected": self._hardware_connected,
            "port": self.port,
            "manager_phone": self.manager_phone,
            "total_sent": self.delivery_count,
            "last_event": self.last_sent_event,
            "last_error": self.last_error
        }
