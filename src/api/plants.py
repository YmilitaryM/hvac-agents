"""Plant management API endpoints.

Supports dual-mode: PostgreSQL via repositories (when configured),
or in-memory storage (default/dev).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import use_db as _use_db

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage for dev/testing fallback
_plants: Dict[str, Dict[str, Any]] = {}

# Template directory relative to project root
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "services" / "asset" / "asset_service" / "templates"

_FALLBACK_TEMPLATES = [
    {
        "id": "primary_variable_flow",
        "name": "一次泵变流量系统",
        "description": "冷冻水一次泵变流量 + 冷却水定流量，N+1 冗余",
        "complexity": "medium",
        "slot_count": 6,
    },
    {
        "id": "primary_secondary",
        "name": "一二次泵系统",
        "description": "冷冻水一二次泵解耦 + 冷却水定流量",
        "complexity": "high",
        "slot_count": 8,
    },
    {
        "id": "simple_air_cooled",
        "name": "风冷模块系统",
        "description": "小型风冷冷水机组 + 一次泵定流量",
        "complexity": "low",
        "slot_count": 3,
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    import uuid
    return uuid.uuid4().hex[:16]


# --- Template helpers ---

def _load_json_templates() -> List[Dict[str, Any]]:
    templates = []
    if _TEMPLATES_DIR.is_dir():
        for f in _TEMPLATES_DIR.glob("*.json"):
            with open(f) as fp:
                t = json.load(fp)
                templates.append({
                    "id": f.stem,
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "complexity": t.get("complexity", "medium"),
                    "slot_count": len(t.get("slots", [])),
                })
    return templates or _FALLBACK_TEMPLATES


def _build_topology(template: Dict, N: int = 2, S: int = 1) -> tuple:
    """Generate equipment nodes and pipe connections from a template."""
    equipment: List[Dict] = []
    pipe_segments: List[Dict] = []

    # Groups of equipment by role
    chillers: List[str] = []
    chw_pumps: List[str] = []
    cw_pumps: List[str] = []
    towers: List[str] = []

    for slot in template.get("slots", []):
        count_key = slot.get("count", "1")
        count = N if count_key == "N" else S if count_key == "S" else int(count_key)
        if not count:
            continue

        role = slot.get("role", "")
        type_code = slot.get("type_code", "")

        for i in range(1, count + 1):
            eq_id = slot["id"].replace("{n}", str(i))
            name_map = {
                "chw_primary": f"冷冻水泵-{i}",
                "cw": f"冷却水泵-{i}",
                "primary": f"冷水机组-{i}" if type_code == "centrifugal_chiller" else f"冷却塔-{i}",
                "flow_control": f"调节阀-{i}",
                "bypass": "旁通阀",
            }
            eq_name = name_map.get(role, f"{role}-{i}")
            equipment.append({"id": eq_id, "name": eq_name, "type_code": type_code, "design_params": {}})

            if type_code == "centrifugal_chiller":
                chillers.append(eq_id)
            elif type_code == "pump":
                if role == "chw_primary":
                    chw_pumps.append(eq_id)
                elif role == "cw":
                    cw_pumps.append(eq_id)
            elif type_code == "cooling_tower":
                towers.append(eq_id)

    for loop in template.get("loops", []):
        fluid = loop.get("fluid", "")
        if fluid == "chilled_water":
            for pump_id in chw_pumps:
                for ch_id in chillers:
                    ps_id = _new_id()
                    pipe_segments.append({
                        "id": ps_id,
                        "from_equipment_id": pump_id,
                        "from_point_code": "outlet_pressure",
                        "to_equipment_id": ch_id,
                        "to_point_code": "chw_supply_temp",
                        "diameter_mm": 200,
                        "length_m": 0,
                        "waypoints": [],
                    })
        elif fluid == "cooling_water":
            for ch_id in chillers:
                for pump_id in cw_pumps:
                    ps_id = _new_id()
                    pipe_segments.append({
                        "id": ps_id,
                        "from_equipment_id": ch_id,
                        "from_point_code": "cw_leaving_temp",
                        "to_equipment_id": pump_id,
                        "to_point_code": "inlet_pressure",
                        "diameter_mm": 200,
                        "length_m": 0,
                        "waypoints": [],
                    })
            for pump_id in cw_pumps:
                for tower_id in towers:
                    ps_id = _new_id()
                    pipe_segments.append({
                        "id": ps_id,
                        "from_equipment_id": pump_id,
                        "from_point_code": "outlet_pressure",
                        "to_equipment_id": tower_id,
                        "to_point_code": "water_in_temp",
                        "diameter_mm": 200,
                        "length_m": 0,
                        "waypoints": [],
                    })

    return equipment, pipe_segments


# --- Template endpoints ---

@router.get("/templates")
async def list_templates():
    """List available plant topology templates."""
    return {"templates": _load_json_templates()}


# --- Plant CRUD endpoints ---

@router.get("/")
async def list_plants(limit: int = Query(default=50, le=200)):
    """List all plants."""
    if _use_db():
        from src.api.deps import get_db_session, get_plant_repo

        async for session in get_db_session():
            repo = get_plant_repo(session)
            results = await repo.list_all(limit=limit)
            return {
                "plants": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "equipment": p.equipment_data or [],
                        "pipe_segments": p.pipe_segments or [],
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    }
                    for p in results
                ]
            }

    return {"plants": list(_plants.values())}


@router.get("/{plant_id}")
async def get_plant(plant_id: str):
    """Get a single plant by ID."""
    if _use_db():
        from src.api.deps import get_db_session, get_plant_repo

        async for session in get_db_session():
            repo = get_plant_repo(session)
            p = await repo.get_by_id(plant_id)
            if p is None:
                raise HTTPException(status_code=404, detail="Plant not found")
            return {
                "id": p.id,
                "name": p.name,
                "equipment": p.equipment_data or [],
                "pipe_segments": p.pipe_segments or [],
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }

    plant = _plants.get(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return plant


@router.post("/")
async def create_plant(data: Dict[str, Any]):
    """Create a new plant, optionally from a template."""
    template_id = data.get("template_id")
    N = data.get("N", 2)
    S = data.get("standby", 1)
    equipment: List[Dict] = data.get("equipment", [])
    pipe_segments: List[Dict] = data.get("pipe_segments", [])
    plant_name = data.get("name", "新建制冷站")
    plant_id = data.get("id") or _new_id()

    if template_id:
        tpl_path = _TEMPLATES_DIR / f"{template_id}.json"
        if tpl_path.is_file():
            with open(tpl_path) as fp:
                t = json.load(fp)
                plant_name = data.get("name") or t.get("name", plant_name)
                equipment, pipe_segments = _build_topology(t, N=N, S=S)
        else:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    plant = {
        "id": plant_id,
        "name": plant_name,
        "equipment": equipment,
        "pipe_segments": pipe_segments,
        "created_at": _now(),
        "updated_at": _now(),
    }

    if _use_db():
        from src.api.deps import get_db_session, get_plant_repo

        async for session in get_db_session():
            repo = get_plant_repo(session)
            existing = await repo.get_by_id(plant_id)
            if existing:
                raise HTTPException(status_code=409, detail="Plant already exists")
            p = await repo.create({
                "id": plant_id,
                "name": plant["name"],
                "equipment_data": plant["equipment"],
                "pipe_segments": plant["pipe_segments"],
            })
            return {"id": p.id, "name": p.name, "equipment": equipment, "pipe_segments": pipe_segments}

    _plants[plant_id] = plant
    return {"id": plant_id, "name": plant["name"], "equipment": equipment, "pipe_segments": pipe_segments}


@router.put("/{plant_id}")
async def update_plant(plant_id: str, data: Dict[str, Any]):
    """Update an existing plant (upsert)."""
    plant = {
        "id": plant_id,
        "name": data.get("name", "新建制冷站"),
        "equipment": data.get("equipment", []),
        "pipe_segments": data.get("pipe_segments", []),
        "updated_at": _now(),
    }

    if _use_db():
        from src.api.deps import get_db_session, get_plant_repo

        async for session in get_db_session():
            repo = get_plant_repo(session)
            existing = await repo.get_by_id(plant_id)
            if existing:
                p = await repo.update(plant_id, {
                    "name": plant["name"],
                    "equipment_data": plant["equipment"],
                    "pipe_segments": plant["pipe_segments"],
                })
            else:
                p = await repo.create({
                    "id": plant_id,
                    "name": plant["name"],
                    "equipment_data": plant["equipment"],
                    "pipe_segments": plant["pipe_segments"],
                })
            return {"id": p.id, "name": p.name}

    if plant_id in _plants:
        existing = _plants[plant_id]
        existing.update(plant)
        _plants[plant_id] = existing
    else:
        plant["created_at"] = _now()
        _plants[plant_id] = plant
    return {"id": plant_id, "name": plant["name"]}


@router.delete("/{plant_id}")
async def delete_plant(plant_id: str):
    """Delete a plant."""
    if _use_db():
        from src.api.deps import get_db_session, get_plant_repo

        async for session in get_db_session():
            repo = get_plant_repo(session)
            deleted = await repo.delete(plant_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Plant not found")
            return {"deleted": True}

    if plant_id not in _plants:
        raise HTTPException(status_code=404, detail="Plant not found")
    del _plants[plant_id]
    return {"deleted": True}
