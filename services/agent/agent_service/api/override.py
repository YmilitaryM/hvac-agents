import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class OverrideType(str, Enum):
    SETPOINT = "setpoint"
    CHILLER_ON = "chiller_on"
    CHILLER_OFF = "chiller_off"
    PUMP_SPEED = "pump_speed"
    TOWER_FAN = "tower_fan"
    VALVE_POSITION = "valve_position"
    STRATEGY_SWITCH = "strategy_switch"


@dataclass
class OverrideEntry:
    override_id: str
    device_id: str
    override_type: OverrideType
    value: float
    operator: str = ""
    reason: str = ""
    created_at: float = field(default_factory=time.time)
    expires_at: float = float("inf")
    active: bool = True


class OverrideCreate(BaseModel):
    device_id: str
    override_type: OverrideType
    value: float
    reason: str = ""
    timeout_minutes: int = 30  # auto-revert after this many minutes


class OverrideList(BaseModel):
    overrides: list[dict]


# In-memory store (production would use DB + Redis)
_overrides: dict[str, OverrideEntry] = {}
_revert_tasks: dict[str, asyncio.Task] = {}


async def _auto_revert(override_id: str, delay_seconds: float):
    await asyncio.sleep(delay_seconds)
    entry = _overrides.get(override_id)
    if entry and entry.active:
        entry.active = False
        logger.info("Auto-reverted override %s (%s on %s)", override_id, entry.override_type, entry.device_id)


@router.post("/override", status_code=201)
async def create_override(body: OverrideCreate):
    import uuid

    oid = str(uuid.uuid4())[:8]
    expires = time.time() + body.timeout_minutes * 60 if body.timeout_minutes > 0 else float("inf")
    entry = OverrideEntry(
        override_id=oid,
        device_id=body.device_id,
        override_type=body.override_type,
        value=body.value,
        reason=body.reason,
        expires_at=expires,
    )
    _overrides[oid] = entry

    if expires != float("inf"):
        delay = body.timeout_minutes * 60
        _revert_tasks[oid] = asyncio.create_task(_auto_revert(oid, delay))

    # In production: send command to acquisition service
    logger.info("Override created: %s=%s on %s (timeout=%dmin)", body.override_type, body.value, body.device_id, body.timeout_minutes)

    return {
        "override_id": oid,
        "device_id": body.device_id,
        "override_type": body.override_type.value,
        "value": body.value,
        "expires_at": expires,
        "active": True,
    }


@router.get("/override")
async def list_overrides(active_only: bool = True):
    result = []
    for oid, entry in _overrides.items():
        if active_only and not entry.active:
            continue
        result.append({
            "override_id": entry.override_id,
            "device_id": entry.device_id,
            "override_type": entry.override_type.value,
            "value": entry.value,
            "reason": entry.reason,
            "created_at": entry.created_at,
            "expires_at": entry.expires_at,
            "active": entry.active,
        })
    return {"overrides": result}


@router.delete("/override/{override_id}")
async def cancel_override(override_id: str):
    entry = _overrides.get(override_id)
    if not entry:
        raise HTTPException(404, "Override not found")
    if not entry.active:
        raise HTTPException(400, "Override already reverted")

    entry.active = False
    task = _revert_tasks.pop(override_id, None)
    if task and not task.done():
        task.cancel()

    logger.info("Override %s cancelled by operator", override_id)
    return {"override_id": override_id, "status": "cancelled"}


@router.post("/override/{override_id}/revert")
async def revert_override(override_id: str):
    entry = _overrides.get(override_id)
    if not entry:
        raise HTTPException(404, "Override not found")
    if not entry.active:
        raise HTTPException(400, "Override already reverted")

    entry.active = False
    task = _revert_tasks.pop(override_id, None)
    if task and not task.done():
        task.cancel()

    # In production: send revert command to acquisition service
    logger.info("Override %s manually reverted", override_id)
    return {"override_id": override_id, "status": "reverted"}
