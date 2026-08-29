import time
from backend.app.alerts.alert_manager import AlertManager
from backend.app.alerts.hardware_drivers import PhysicalAlertHardwareDriver
from backend.app.alerts.sms_driver import Sim800lGsmDriver

def test_alert_state_machine():
    manager = AlertManager()
    
    # 1. Process Raw Event -> Creates NEW alert
    alert = manager.process_raw_event(
        source_module="shelf",
        event_type="immediate_stockout",
        data={"zone_id": "zone-test-01", "zone_label": "Milk Shelf", "is_top_sku": True, "estimated_lost_sales": 20.0}
    )
    assert alert is not None
    assert alert["severity"] == "CRITICAL"
    assert alert["state"] == "NEW"

    # 2. Staff Acknowledges Alert -> State ACKNOWLEDGED
    aid = alert["alert_id"]
    ack_alert = manager.acknowledge_alert(aid, acknowledged_by="floor_staff_1")
    assert ack_alert is not None
    assert ack_alert["state"] == "ACKNOWLEDGED"
    assert ack_alert["acknowledged_at"] is not None

    # 3. Restock / Condition Cleared -> State RESOLVED
    res_alert = manager.resolve_alert(aid, reason="Restocked shelf")
    assert res_alert is not None
    assert res_alert["state"] == "RESOLVED"

def test_hardware_dispatch():
    driver = PhysicalAlertHardwareDriver(buzzer_pin=18, rgb_pins=[23, 24, 25])
    
    driver.set_alert_signals("CRITICAL", state="NEW")
    stat = driver.get_hardware_status()
    assert stat["led_color"] == "RED"
    assert stat["led_mode"] == "BLINKING"

    driver.acknowledge_signals()
    stat_ack = driver.get_hardware_status()
    assert stat_ack["led_mode"] == "SOLID"
    assert stat_ack["buzzer_active"] is False

    # SMS Driver
    sms = Sim800lGsmDriver()
    sms_res = sms.send_emergency_sms("Test Alert", "Critical queue wait > 10m", "CRITICAL")
    assert sms_res["status"] in ["sent", "emulated_delivered"]

if __name__ == "__main__":
    test_alert_state_machine()
    test_hardware_dispatch()
    print("Alert Subsystem tests passed!")
