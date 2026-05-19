"""Alerting API endpoints for rule management, acknowledgement, and escalation."""

from fastapi import APIRouter, Depends

from common.auth import require_role, Role

from ..alerting.engine import AlertEngine
from ..alerting.suppression import SuppressionEngine
from ..alerting.escalation import EscalationEngine

router = APIRouter()

# Module-level singletons
_alert_engine = AlertEngine()
_alert_engine.load_rules()  # load default rules
_suppression_engine = SuppressionEngine()
_escalation_engine = EscalationEngine()


@router.get("/rules")
async def get_rules(
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    return {"rules": _alert_engine.get_rules()}


@router.put("/rules")
async def update_rules(
    rules_data: dict,
    user: dict = Depends(require_role(Role.ENGINEER, Role.ADMIN)),
):
    _alert_engine.update_rules(rules_data.get("rules", []))
    return {"status": "updated", "count": len(_alert_engine.rules)}


@router.put("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    _escalation_engine.acknowledge(alert_id)
    return {"status": "acknowledged", "alert_id": alert_id}


@router.post("/maintenance/{device_id}")
async def set_maintenance(
    device_id: str,
    data: dict,
    user: dict = Depends(require_role(Role.ENGINEER, Role.ADMIN)),
):
    """Set or clear maintenance mode for a device. Body: {"maintenance": true/false}"""
    if data.get("maintenance"):
        _suppression_engine.add_maintenance(device_id)
        return {"status": "maintenance_on", "device_id": device_id}
    else:
        _suppression_engine.remove_maintenance(device_id)
        return {"status": "maintenance_off", "device_id": device_id}


@router.get("/escalations")
async def get_escalations(
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    return {"escalations": _escalation_engine.check_escalations()}
