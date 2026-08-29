import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.app.database import get_db_connection
from backend.app.schemas import AlertItem, AlertAcknowledgeRequest, AlertResolveRequest, HardwareStatusResponse

router = APIRouter(prefix="/alerts", tags=["Multi-Level Alert & Notification Subsystem"])

alert_manager_instance = None

def set_alert_manager_instance(am):
    global alert_manager_instance
    alert_manager_instance = am

@router.get("", response_model=List[AlertItem])
def get_active_alerts():
    """Retrieve all ranked active alerts currently in the Alert Manager state machine."""
    if not alert_manager_instance:
        return []
    
    alerts = alert_manager_instance.get_ranked_active_alerts()
    res = []
    for a in alerts:
        res.append(AlertItem(
            alert_id=a["alert_id"],
            source_module=a["source_module"],
            zone_id=a["zone_id"],
            zone_label=a.get("zone_label"),
            title=a["title"],
            message=a["message"],
            severity=a["severity"],
            state=a["state"],
            type=a.get("type", "alert"),
            eta_minutes=a.get("eta_minutes", 0.0),
            priority_score=a.get("priority_score", 50.0),
            estimated_lost_sales=a.get("estimated_lost_sales", 0.0),
            created_at=a["created_at"],
            acknowledged_at=a.get("acknowledged_at"),
            resolved_at=a.get("resolved_at"),
            escalate_count=a.get("escalate_count", 0),
            escalation_remaining_sec=a.get("escalation_remaining_sec"),
            details=a.get("details")
        ))
    return res

@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, req: AlertAcknowledgeRequest = AlertAcknowledgeRequest()):
    """Staff acknowledges an active alert: silences repeat buzzer/LED pulsing and begins cooldown."""
    if not alert_manager_instance:
        raise HTTPException(status_code=503, detail="Alert Manager not initialized")
    
    alert = alert_manager_instance.acknowledge_alert(alert_id, acknowledged_by=req.acknowledged_by)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found in active state")
    
    return {"status": "success", "alert": alert, "message": f"Alert {alert_id} acknowledged"}

@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: str, req: AlertResolveRequest = AlertResolveRequest()):
    """Manually resolve an active alert and reset hardware indicators."""
    if not alert_manager_instance:
        raise HTTPException(status_code=503, detail="Alert Manager not initialized")
    
    alert = alert_manager_instance.resolve_alert(alert_id, reason=req.reason)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found in active state")
    
    return {"status": "success", "alert": alert, "message": f"Alert {alert_id} resolved"}

@router.get("/hardware/status", response_model=HardwareStatusResponse)
def get_hardware_channel_status():
    """Get live health and connection status for all 5 alert channels."""
    if not alert_manager_instance:
        return HardwareStatusResponse()
    
    status_dict = alert_manager_instance.get_hardware_status()
    return HardwareStatusResponse(**status_dict)

class ChannelTestRequest(BaseModel):
    channel: str # "buzzer" | "led" | "sms"
    pattern_or_color: Optional[str] = "HIGH"
    test_message: Optional[str] = "Manual test alert from RetailIQ Dashboard"

@router.post("/test-channel")
def test_alert_channel(req: ChannelTestRequest):
    """Interactive diagnostic endpoint to trigger test buzzer beeps, LED colors, or SMS."""
    if not alert_manager_instance:
        raise HTTPException(status_code=503, detail="Alert Manager not initialized")

    if req.channel == "buzzer":
        alert_manager_instance.hardware_driver.set_alert_signals(req.pattern_or_color, state="NEW")
        return {"status": "success", "channel": "buzzer", "message": f"Buzzer test pattern {req.pattern_or_color} triggered"}
    
    elif req.channel == "led":
        alert_manager_instance.hardware_driver.set_alert_signals(req.pattern_or_color, state="NEW")
        return {"status": "success", "channel": "led", "message": f"RGB LED test color {req.pattern_or_color} triggered"}
    
    elif req.channel == "sms":
        sms_res = alert_manager_instance.sms_driver.send_emergency_sms(
            alert_title="TEST ALERT",
            message=req.test_message or "Test SMS dispatch from RetailIQ Edge",
            severity="CRITICAL"
        )
        return {"status": "success", "channel": "sms", "result": sms_res}

    return {"status": "unknown_channel"}
