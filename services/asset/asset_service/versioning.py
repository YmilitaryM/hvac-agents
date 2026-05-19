from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import EntityVersionModel


async def save_version(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
    old_snapshot: dict,
    new_snapshot: dict,
    changed_by: str = "system",
    change_reason: str = "",
    version_hint: int | None = None,
) -> EntityVersionModel:
    """Save a new version entry for an entity, computing diff from previous state."""
    if version_hint is None:
        result = await session.execute(
            select(func.max(EntityVersionModel.version))
            .where(EntityVersionModel.entity_type == entity_type)
            .where(EntityVersionModel.entity_id == entity_id)
        )
        max_ver = result.scalar() or 0
        version = max_ver + 1
    else:
        version = version_hint

    diff = {}
    all_keys = set(old_snapshot.keys()) | set(new_snapshot.keys())
    for key in all_keys:
        old_val = old_snapshot.get(key)
        new_val = new_snapshot.get(key)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}

    entry = EntityVersionModel(
        entity_type=entity_type,
        entity_id=entity_id,
        version=version,
        snapshot=new_snapshot,
        diff_from_prev=diff if diff else None,
        changed_by=changed_by,
        change_reason=change_reason,
    )
    session.add(entry)
    return entry
