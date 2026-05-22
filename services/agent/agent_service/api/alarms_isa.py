"""ISA-18.2 / EEMUA 191 Alarm Management API endpoints.

Provides REST endpoints for the full alarm lifecycle:
  - List alarms with ISA-18.2 metadata
  - Acknowledge / Shelve / Suppress / Clear
  - Performance KPIs (ISA-18.2)
  - Rationalization report and update
  - HMI summary (EEMUA 191 operator display format)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from common.auth import require_role, Role

from ..alarm_models import ISA18Alarm, AlarmState, AlarmSeverity
from ..alarm_manager import AlarmManager
from ..alarm_compliance import (
    validate_compliance,
    get_unrationalized_alarms,
    get_chattering_alarms,
)

router = APIRouter()

# Module-level singleton AlarmManager
_alarm_manager = AlarmManager()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RaiseAlarmRequest(BaseModel):
    tag: str = Field(..., description="Equipment tag, e.g. CH-01")
    description: str = Field(..., description="Alarm description")
    severity: int = Field(..., ge=1, le=5, description="ISA-18.2 severity 1-5")
    rationalization: str = Field(..., description="ISA-18.2 rationalization (mandatory)")
    consequence_of_inaction: str = Field(..., description="Consequence if alarm is ignored")
    time_to_respond_seconds: int = Field(..., gt=0, description="TTR in seconds")


class AcknowledgeRequest(BaseModel):
    user: str = Field(..., description="Operator ID acknowledging the alarm")


class ShelveRequest(BaseModel):
    until: str = Field(..., description="ISO datetime when shelving expires")


class SuppressRequest(BaseModel):
    reason: str = Field(..., description="Documented reason for suppression")


class RationalizeRequest(BaseModel):
    rationalization: str = Field(..., description="ISA-18.2 rationalization text")


# ---------------------------------------------------------------------------
# Alarm lifecycle endpoints
# ---------------------------------------------------------------------------

@router.post("/isa", tags=["Alarms:ISA-18.2"])
async def raise_alarm(
    body: RaiseAlarmRequest,
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Raise a new ISA-18.2 compliant alarm."""
    alarm = ISA18Alarm(
        tag=body.tag,
        description=body.description,
        severity=AlarmSeverity(body.severity),
        rationalization=body.rationalization,
        consequence_of_inaction=body.consequence_of_inaction,
        time_to_respond_seconds=body.time_to_respond_seconds,
    )
    result = _alarm_manager.raise_alarm(alarm)
    return result.to_hmi_format()


@router.get("/isa", tags=["Alarms:ISA-18.2"])
async def list_alarms(
    state: Optional[str] = None,
    severity: Optional[int] = None,
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """List alarms with ISA-18.2 metadata.  Optional filters by state and severity."""
    if state:
        try:
            state_enum = AlarmState(state)
            alarms = _alarm_manager.get_alarms_by_state(state_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
    elif severity:
        try:
            sev_enum = AlarmSeverity(severity)
            alarms = _alarm_manager.get_alarms_by_severity(sev_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    else:
        alarms = _alarm_manager.get_active_alarms()

    return {"alarms": [a.to_hmi_format() for a in alarms], "count": len(alarms)}


@router.get("/isa/{alarm_id}", tags=["Alarms:ISA-18.2"])
async def get_alarm(
    alarm_id: str,
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Get a single alarm by ID with full ISA-18.2 metadata."""
    alarm = _alarm_manager.get_alarm(alarm_id)
    if alarm is None:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return alarm.to_hmi_format()


@router.post("/isa/{alarm_id}/acknowledge", tags=["Alarms:ISA-18.2"])
async def acknowledge_alarm(
    alarm_id: str,
    body: AcknowledgeRequest,
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Acknowledge an alarm (operator has seen and accepted it)."""
    try:
        result = _alarm_manager.acknowledge(alarm_id, body.user)
        return result.to_hmi_format()
    except KeyError:
        raise HTTPException(status_code=404, detail="Alarm not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/isa/{alarm_id}/shelve", tags=["Alarms:ISA-18.2"])
async def shelve_alarm(
    alarm_id: str,
    body: ShelveRequest,
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Shelve an alarm — temporarily hide until the given time."""
    try:
        until = datetime.fromisoformat(body.until)
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        result = _alarm_manager.shelve(alarm_id, until)
        return result.to_hmi_format()
    except KeyError:
        raise HTTPException(status_code=404, detail="Alarm not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/isa/{alarm_id}/suppress", tags=["Alarms:ISA-18.2"])
async def suppress_alarm(
    alarm_id: str,
    body: SuppressRequest,
    user: dict = Depends(require_role(Role.ENGINEER, Role.ADMIN)),
):
    """Suppress an alarm — intentionally hide with a documented reason."""
    try:
        result = _alarm_manager.suppress(alarm_id, body.reason)
        return result.to_hmi_format()
    except KeyError:
        raise HTTPException(status_code=404, detail="Alarm not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/isa/{alarm_id}/clear", tags=["Alarms:ISA-18.2"])
async def clear_alarm(
    alarm_id: str,
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Clear an alarm — the alarm condition no longer exists."""
    try:
        result = _alarm_manager.clear(alarm_id)
        return result.to_hmi_format()
    except KeyError:
        raise HTTPException(status_code=404, detail="Alarm not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/isa/{alarm_id}/unshelve", tags=["Alarms:ISA-18.2"])
async def unshelve_alarm(
    alarm_id: str,
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Manually return a shelved alarm to active state."""
    try:
        result = _alarm_manager.unshelve(alarm_id)
        return result.to_hmi_format()
    except KeyError:
        raise HTTPException(status_code=404, detail="Alarm not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ---------------------------------------------------------------------------
# ISA-18.2 Compliance & Performance
# ---------------------------------------------------------------------------

@router.get("/isa/performance", tags=["Alarms:ISA-18.2"])
async def get_performance_metrics(
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Get ISA-18.2 KPIs: alarm rate, peak rate, stale %, chatter, time-to-ack."""
    return _alarm_manager.get_performance_metrics()


@router.get("/isa/compliance", tags=["Alarms:ISA-18.2"])
async def get_compliance_report(
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Run ISA-18.2 compliance validation and return the report."""
    report = validate_compliance(_alarm_manager)
    return {
        "overall_compliant": report.overall_compliant,
        "passed_count": report.passed_count,
        "failed_count": report.failed_count,
        "generated_at": report.generated_at,
        "checks": [
            {
                "name": c.name,
                "description": c.description,
                "passed": c.passed,
                "actual_value": c.actual_value,
                "threshold": c.threshold,
                "unit": c.unit,
            }
            for c in report.checks
        ],
    }


@router.get("/isa/rationalization", tags=["Alarms:ISA-18.2"])
async def get_rationalization_report(
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Get the ISA-18.2 rationalization report for all alarms."""
    return {
        "alarms": _alarm_manager.get_rationalization_report(),
        "unrationalized": get_unrationalized_alarms(_alarm_manager),
        "chattering": get_chattering_alarms(_alarm_manager),
    }


@router.post("/isa/rationalize", tags=["Alarms:ISA-18.2"])
async def rationalize_alarm(
    body: RationalizeRequest,
    user: dict = Depends(require_role(Role.ENGINEER, Role.ADMIN)),
):
    """Add or update rationalization for an alarm."""
    # Body needs alarm_id — we accept it as a query param
    from fastapi import Query
    raise HTTPException(
        status_code=400,
        detail="Use POST /isa/{alarm_id}/rationalize instead"
    )


@router.post("/isa/{alarm_id}/rationalize", tags=["Alarms:ISA-18.2"])
async def rationalize_alarm_by_id(
    alarm_id: str,
    body: RationalizeRequest,
    user: dict = Depends(require_role(Role.ENGINEER, Role.ADMIN)),
):
    """Add or update the ISA-18.2 rationalization for an alarm."""
    try:
        result = _alarm_manager.rationalize(alarm_id, body.rationalization)
        return result.to_hmi_format()
    except KeyError:
        raise HTTPException(status_code=404, detail="Alarm not found")


# ---------------------------------------------------------------------------
# HMI endpoints (EEMUA 191 operator display)
# ---------------------------------------------------------------------------

@router.get("/isa/hmi/list", tags=["Alarms:ISA-18.2"])
async def get_hmi_alarm_list(
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Get all active alarms in EEMUA 191 HMI display format.

    Sorted by priority (highest first), then by activation time (newest first).
    """
    return {"alarms": _alarm_manager.to_hmi_list()}


@router.get("/isa/hmi/summary", tags=["Alarms:ISA-18.2"])
async def get_hmi_summary(
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Get HMI summary panel data per EEMUA 191.

    Returns counts by severity and state for the operator overview display.
    """
    return _alarm_manager.get_hmi_summary()


@router.post("/isa/check-shelved", tags=["Alarms:ISA-18.2"])
async def check_shelved_alarms(
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Auto-return any shelved alarms whose time has expired.

    Normally called by a background scheduler; exposed as an endpoint for
    manual trigger during testing or operator override.
    """
    returned = _alarm_manager.check_shelved()
    return {
        "returned_count": len(returned),
        "returned": [a.to_hmi_format() for a in returned],
    }
