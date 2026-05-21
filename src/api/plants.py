"""Plant management API endpoints.

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
_plants: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    """Create a new plant."""
    plant_id = data.get("id") or _new_id()
    plant = {
        "id": plant_id,
        "name": data.get("name", "新建制冷站"),
        "equipment": data.get("equipment", []),
        "pipe_segments": data.get("pipe_segments", []),
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
            return {"id": p.id, "name": p.name}

    _plants[plant_id] = plant
    return {"id": plant_id, "name": plant["name"]}


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


def _new_id() -> str:
    import uuid
    return uuid.uuid4().hex[:16]
