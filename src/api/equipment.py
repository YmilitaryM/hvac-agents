"""Equipment library API endpoints.

Supports dual-mode: PostgreSQL via repositories (when configured),
or in-memory storage (default/dev).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import use_db as _use_db

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for dev/testing fallback
_equipment: Dict[str, Dict[str, Any]] = {}

# Seed some default equipment types as available library items
_SEED_EQUIPMENT = [
    {"type_code": "centrifugal_chiller", "name_prefix": "离心式冷水主机"},
    {"type_code": "centrifugal_chiller", "name_prefix": "离心式冷水主机"},
    {"type_code": "pump", "name_prefix": "冷冻水泵"},
    {"type_code": "pump", "name_prefix": "冷却水泵"},
    {"type_code": "pump", "name_prefix": "冷冻水泵"},
    {"type_code": "cooling_tower", "name_prefix": "冷却塔"},
    {"type_code": "cooling_tower", "name_prefix": "冷却塔"},
    {"type_code": "control_valve", "name_prefix": "电动调节阀"},
    {"type_code": "control_valve", "name_prefix": "电动调节阀"},
    {"type_code": "temperature_sensor", "name_prefix": "温度传感器"},
    {"type_code": "temperature_sensor", "name_prefix": "温度传感器"},
    {"type_code": "pressure_sensor", "name_prefix": "压力传感器"},
    {"type_code": "flow_sensor", "name_prefix": "流量计"},
    {"type_code": "power_meter", "name_prefix": "功率计"},
]

for i, seed in enumerate(_SEED_EQUIPMENT):
    eid = f"eq-seed-{i:04d}"
    _equipment[eid] = {
        "id": eid,
        "name": f"{seed['name_prefix']} #{i+1}",
        "type_code": seed["type_code"],
        "plant_id": None,
        "design_params": {},
    }


@router.get("/")
async def list_equipment(plant_id: Optional[str] = Query(default=None)):
    """List equipment, optionally filtered by plant_id."""
    if _use_db():
        from src.api.deps import get_db_session, get_equipment_repo

        async for session in get_db_session():
            repo = get_equipment_repo(session)
            if plant_id:
                results = await repo.list_by_plant(plant_id)
            else:
                results = await repo.list_available()
            return {
                "equipment": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "type_code": e.type_code,
                        "plant_id": e.plant_id,
                        "design_params": e.design_params or {},
                    }
                    for e in results
                ]
            }

    items = list(_equipment.values())
    if plant_id:
        items = [e for e in items if e.get("plant_id") == plant_id]
    else:
        items = [e for e in items if not e.get("plant_id")]
    return {"equipment": items}


@router.post("/")
async def create_equipment(data: Dict[str, Any]):
    """Create a new equipment item in the library."""
    eq_id = data.get("id") or _new_id()
    eq = {
        "id": eq_id,
        "name": data.get("name", ""),
        "type_code": data.get("equipment_type_id", data.get("type_code", "")),
        "plant_id": data.get("plant_id"),
        "design_params": data.get("design_params", {}),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if _use_db():
        from src.api.deps import get_db_session, get_equipment_repo

        async for session in get_db_session():
            repo = get_equipment_repo(session)
            e = await repo.create(eq)
            return {
                "id": e.id,
                "name": e.name,
                "type_code": e.type_code,
                "plant_id": e.plant_id,
                "design_params": e.design_params or {},
            }

    _equipment[eq_id] = eq
    return eq


@router.delete("/{equipment_id}")
async def delete_equipment(equipment_id: str):
    """Delete an equipment item."""
    if _use_db():
        from src.api.deps import get_db_session, get_equipment_repo

        async for session in get_db_session():
            repo = get_equipment_repo(session)
            deleted = await repo.delete(equipment_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Equipment not found")
            return {"deleted": True}

    if equipment_id not in _equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    del _equipment[equipment_id]
    return {"deleted": True}


def _new_id() -> str:
    import uuid
    return uuid.uuid4().hex[:16]
