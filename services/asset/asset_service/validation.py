from sqlalchemy import select

from .models import PlantModel, LoopModel, PipeSegmentModel, EquipmentModel, EquipmentPointModel


async def validate_plant_topology(plant_id: str, db) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []

    # Check 1: Every loop must have at least one pipe segment
    loops_result = await db.execute(
        select(LoopModel).where(LoopModel.plant_id == plant_id)
    )
    loops = loops_result.scalars().all()

    all_segs = []
    for loop in loops:
        segs_result = await db.execute(
            select(PipeSegmentModel).where(PipeSegmentModel.loop_id == loop.id)
        )
        segs = segs_result.scalars().all()
        all_segs.extend(segs)
        if not segs:
            warnings.append(f"Loop '{loop.name}' has no pipe segments")

    # Check 2: All from_point_id and to_point_id must reference real points
    point_ids = set()
    for seg in all_segs:
        point_ids.add(seg.from_point_id)
        point_ids.add(seg.to_point_id)

    for pid in point_ids:
        pt_result = await db.execute(
            select(EquipmentPointModel).where(EquipmentPointModel.id == pid)
        )
        if not pt_result.scalar_one_or_none():
            errors.append(f"Pipe segment references non-existent point: {pid}")

    # Check 3: Isolated equipment (no connected points)
    eq_result = await db.execute(
        select(EquipmentModel).where(EquipmentModel.plant_id == plant_id)
    )
    equipment = eq_result.scalars().all()

    for eq in equipment:
        pts_result = await db.execute(
            select(EquipmentPointModel).where(EquipmentPointModel.equipment_id == eq.id)
        )
        pts = pts_result.scalars().all()
        connected = any(
            p.id in {s.from_point_id for s in all_segs}
            or p.id in {s.to_point_id for s in all_segs}
            for p in pts
        )
        if not connected and pts:
            warnings.append(f"Equipment '{eq.name}' has no connected pipe segments")

    # Check 4: At least one pump per chilled/cooling water loop (warn)
    for loop in loops:
        if loop.fluid_type in ("chilled_water", "cooling_water"):
            has_pump = False
            for eq in equipment:
                # Check if equipment type is pump via equipment_type relationship
                if hasattr(eq, 'equipment_type') and eq.equipment_type:
                    if eq.equipment_type.category == "pump":
                        has_pump = True
                        break
            if not has_pump:
                warnings.append(f"Loop '{loop.name}' may be missing a pump")

    return errors, warnings
