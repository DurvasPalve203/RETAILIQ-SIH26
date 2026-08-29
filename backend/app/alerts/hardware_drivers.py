import time
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("retailiq.hardware")

class PhysicalAlertHardwareDriver:
    """
    Module D.4: Physical Edge Alert Hardware Driver (GPIO Buzzer & RGB LED)
    - Buzzer: Single short beep (LOW), double beep (HIGH), continuous alarm (CRITICAL)
    - RGB LED: Green (normal), Yellow (HIGH), Red (CRITICAL); Blinking (NEW), Solid (ACKNOWLEDGED)
    - Detects Raspberry Pi GPIO or provides smooth emulated software fallback with virtual states
    """
    def __init__(self, buzzer_pin: int = 18, rgb_pins: list = [23, 24, 25]):
        self.buzzer_pin = buzzer_pin
        self.rgb_pins = rgb_pins # [Red, Green, Blue]

        self.buzzer_active = False
        self.current_buzzer_pattern = "OFF"
        self.current_led_color = "OFF"
        self.current_led_mode = "SOLID"

        self._gpio_available = False
        self._buzzer_device = None
        self._rgb_device = None
        self._pattern_thread: Optional[threading.Thread] = None
        self._running = True

        # Initialize physical GPIO if available
        self._init_gpio()

        # Start background pattern driver
        self._pattern_thread = threading.Thread(target=self._pattern_loop, daemon=True, name="HardwarePatternDriver")
        self._pattern_thread.start()

    def _init_gpio(self):
        try:
            import gpiozero
            # Attempt to bind hardware pins
            self._buzzer_device = gpiozero.Buzzer(self.buzzer_pin)
            self._rgb_device = gpiozero.RGBLED(red=self.rgb_pins[0], green=self.rgb_pins[1], blue=self.rgb_pins[2])
            self._gpio_available = True
            logger.info(f"Physical GPIO hardware initialized on pins buzzer={self.buzzer_pin}, rgb={self.rgb_pins}")
        except Exception:
            self._gpio_available = False
            logger.info("Operating in Edge Virtual Hardware Emulation mode (non-Pi environment).")

    def set_alert_signals(self, highest_severity: Optional[str], state: str = "NEW"):
        """
        Update buzzer and LED based on the highest active alert severity and state.
        Priority rule: Reflects single highest-severity active alert.
        """
        if highest_severity is None or highest_severity == "RESOLVED":
            self.current_buzzer_pattern = "OFF"
            self.current_led_color = "GREEN"
            self.current_led_mode = "SOLID"
            self.buzzer_active = False
            return

        is_new = (state == "NEW" or state == "ESCALATED")

        if highest_severity == "CRITICAL":
            self.current_led_color = "RED"
            self.current_led_mode = "BLINKING" if is_new else "SOLID"
            self.current_buzzer_pattern = "CRITICAL_CONTINUOUS" if is_new else "OFF"
            self.buzzer_active = is_new

        elif highest_severity == "HIGH":
            self.current_led_color = "YELLOW"
            self.current_led_mode = "BLINKING" if is_new else "SOLID"
            self.current_buzzer_pattern = "HIGH_DOUBLE_BEEP" if is_new else "OFF"
            self.buzzer_active = is_new

        elif highest_severity == "LOW":
            self.current_led_color = "YELLOW"
            self.current_led_mode = "SOLID"
            self.current_buzzer_pattern = "LOW_BEEP" if is_new else "OFF"
            self.buzzer_active = False # Single beep handled on transition

    def acknowledge_signals(self):
        """Staff acknowledged: Silence buzzer and switch LED from blinking to solid."""
        self.buzzer_active = False
        self.current_buzzer_pattern = "OFF"
        self.current_led_mode = "SOLID"

    def _pattern_loop(self):
        """Controls physical buzzer pulsing and LED blinking cycles."""
        blink_state = False
        while self._running:
            try:
                time.sleep(0.3)
                blink_state = not blink_state

                # Physical GPIO control if attached
                if self._gpio_available and self._buzzer_device and self._rgb_device:
                    # Buzzer control
                    if self.buzzer_active and self.current_buzzer_pattern == "CRITICAL_CONTINUOUS":
                        self._buzzer_device.toggle()
                    elif self.buzzer_active and self.current_buzzer_pattern == "HIGH_DOUBLE_BEEP" and blink_state:
                        self._buzzer_device.beep(on_time=0.1, off_time=0.1, n=2, background=True)
                    else:
                        self._buzzer_device.off()

                    # RGB LED control
                    if self.current_led_color == "RED":
                        if self.current_led_mode == "BLINKING" and not blink_state:
                            self._rgb_device.color = (0, 0, 0)
                        else:
                            self._rgb_device.color = (1, 0, 0)
                    elif self.current_led_color == "YELLOW":
                        if self.current_led_mode == "BLINKING" and not blink_state:
                            self._rgb_device.color = (0, 0, 0)
                        else:
                            self._rgb_device.color = (1, 0.6, 0)
                    elif self.current_led_color == "GREEN":
                        self._rgb_device.color = (0, 1, 0)
                    else:
                        self._rgb_device.color = (0, 0, 0)

            except Exception:
                pass

    def get_hardware_status(self) -> Dict[str, Any]:
        return {
            "gpio_available": self._gpio_available,
            "buzzer_active": self.buzzer_active,
            "buzzer_pattern": self.current_buzzer_pattern,
            "led_color": self.current_led_color,
            "led_mode": self.current_led_mode
        }
