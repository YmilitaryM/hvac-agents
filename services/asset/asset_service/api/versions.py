from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from common.auth import require_role
from ..models import EntityVersionModel
from ..versioning import save_version
from ..rollback_validator import validate_rollback

router = APIRouter()


async def compute_diff(prev: dict, curr: dict) -> dict:
    """Simple JSON diff -- returns {field: {"old": ..., "new": ...}}."""
    diff = {}
    all_keys = set(prev.keys()) | set(curr.keys())
    for key in all_keys:
        old_val = prev.get(key)
        new_val = curr.get(key)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    return diff


@router.get("/{entity_type}/{entity_id}")
async def list_versions(entity_type: str, entity_id: str, request: Request):
    """List all versions for an entity."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(EntityVersionModel)
            .where(EntityVersionModel.entity_type == entity_type)
            .where(EntityVersionModel.entity_id == entity_id)
            .order_by(desc(EntityVersionModel.version))
        )
        versions = result.scalars().all()
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "versions": [
                {
                    "version": v.version,
                    "changed_by": v.changed_by,
                    "change_reason": v.change_reason,
                    "created_at": v.created_at.isoformat() if v.created_at else None,
                    "has_diff": v.diff_from_prev is not None,
                }
                for v in versions
            ],
            "count": len(versions),
        }


@router.get("/{entity_type}/{entity_id}/{version}")
async def get_version(entity_type: str, entity_id: str, version: int, request: Request):
    """Get full snapshot of a specific version."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(EntityVersionModel)
            .where(EntityVersionModel.entity_type == entity_type)
            .where(EntityVersionModel.entity_id == entity_id)
            .where(EntityVersionModel.version == version)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(404, "Version not found")
        return {
            "id": entry.id,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "version": entry.version,
            "snapshot": entry.snapshot,
            "diff_from_prev": entry.diff_from_prev,
            "changed_by": entry.changed_by,
            "change_reason": entry.change_reason,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }


@router.get("/{entity_type}/{entity_id}/{version}/diff")
async def get_version_diff(entity_type: str, entity_id: str, version: int, request: Request):
    """Get diff between this version and the previous version."""
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(EntityVersionModel)
            .where(EntityVersionModel.entity_type == entity_type)
            .where(EntityVersionModel.entity_id == entity_id)
            .where(EntityVersionModel.version == version)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(404, "Version not found")

        if entry.diff_from_prev:
            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "version": version,
                "diff": entry.diff_from_prev,
            }

        # No stored diff; compute against previous version
        prev_result = await session.execute(
            select(EntityVersionModel)
            .where(EntityVersionModel.entity_type == entity_type)
            .where(EntityVersionModel.entity_id == entity_id)
            .where(EntityVersionModel.version == version - 1)
        )
        prev_entry = prev_result.scalar_one_or_none()
        if not prev_entry:
            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "version": version,
                "diff": {},
                "message": "No previous version to diff against",
            }

        diff = await compute_diff(prev_entry.snapshot or {}, entry.snapshot or {})
        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "version": version,
            "diff": diff,
        }


@router.post("/snapshot", status_code=201)
async def create_snapshot(snapshot_data: dict, request: Request):
    """Manually create a version snapshot.

    Body: {"entity_type": "plant_topology", "entity_id": "...",
           "snapshot": {...}, "changed_by": "...", "change_reason": "..."}
    """
    entity_type = snapshot_data.get("entity_type")
    entity_id = snapshot_data.get("entity_id")
    if not entity_type or not entity_id:
        raise HTTPException(400, "entity_type and entity_id are required")

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        # Get previous snapshot for diff
        result = await session.execute(
            select(EntityVersionModel)
            .where(EntityVersionModel.entity_type == entity_type)
            .where(EntityVersionModel.entity_id == entity_id)
            .order_by(desc(EntityVersionModel.version))
            .limit(1)
        )
        prev = result.scalar_one_or_none()
        old_snapshot = prev.snapshot if prev else {}

        entry = await save_version(
            session=session,
            entity_type=entity_type,
            entity_id=entity_id,
            old_snapshot=old_snapshot,
            new_snapshot=snapshot_data.get("snapshot", {}),
            changed_by=snapshot_data.get("changed_by", "system"),
            change_reason=snapshot_data.get("change_reason", ""),
        )
        await session.commit()
        return {
            "id": entry.id,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "version": entry.version,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }


@router.post("/{entity_type}/{entity_id}/rollback")
async def rollback(
    entity_type: str,
    entity_id: str,
    rollback_data: dict,
    request: Request,
    user=Depends(require_role("ENGINEER", "ADMIN")),
):
    """Rollback to a target version.

    Body: {"target_version": 3, "reason": "...", "validate": true}

    Flow:
    1. Read target version's snapshot
    2. Compute diff vs current state
    3. If validate=true, call Simulation Engine to pre-validate
    4. Create new version (version = max_version + 1) with target's snapshot
    """
    target_version = rollback_data.get("target_version")
    if target_version is None:
        raise HTTPException(400, "target_version is required")

    reason = rollback_data.get("reason", "")
    do_validate = rollback_data.get("validate", True)

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        # 1. Read target version
        result = await session.execute(
            select(EntityVersionModel)
            .where(EntityVersionModel.entity_type == entity_type)
            .where(EntityVersionModel.entity_id == entity_id)
            .where(EntityVersionModel.version == target_version)
        )
        target_entry = result.scalar_one_or_none()
        if not target_entry:
            raise HTTPException(404, f"Version {target_version} not found")

        # 2. Get current (max) version to compute diff
        curr_result = await session.execute(
            select(EntityVersionModel)
            .where(EntityVersionModel.entity_type == entity_type)
            .where(EntityVersionModel.entity_id == entity_id)
            .order_by(desc(EntityVersionModel.version))
            .limit(1)
        )
        current_entry = curr_result.scalar_one_or_none()
        current_snapshot = current_entry.snapshot if current_entry else {}
        target_snapshot = target_entry.snapshot or {}

        diff = await compute_diff(current_snapshot, target_snapshot)

        # 3. Optionally validate via simulation
        validation_result = None
        if do_validate:
            sim_service_url = getattr(request.app.state, "sim_service_url", "http://localhost:8002")
            asset_service_url = getattr(request.app.state, "asset_service_url", "http://localhost:8001")
            validation_result = await validate_rollback(
                entity_type=entity_type,
                entity_id=entity_id,
                target_snapshot=target_snapshot,
                asset_service_url=asset_service_url,
                sim_service_url=sim_service_url,
            )

        # 4. Create new version with target's snapshot
        changed_by = user.get("sub", "system")
        entry = await save_version(
            session=session,
            entity_type=entity_type,
            entity_id=entity_id,
            old_snapshot=current_snapshot,
            new_snapshot=target_snapshot,
            changed_by=changed_by,
            change_reason=f"Rollback to v{target_version}: {reason}",
        )
        await session.commit()

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "rollback_from_version": current_entry.version if current_entry else None,
            "rollback_to_version": target_version,
            "new_version": entry.version,
            "diff": diff,
            "validation": validation_result,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
