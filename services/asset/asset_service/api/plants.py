import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PlantModel, LoopModel, PipeSegmentModel, EquipmentModel, EquipmentPointModel
from ..validation import validate_plant_topology
from ..versioning import save_version

router = APIRouter()
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.session_factory() as session:
        yield session


@router.get("/templates")
async def list_templates():
    """Return available plant topology templates."""
    templates = []
    for f in TEMPLATES_DIR.glob("*.json"):
        with open(f) as fp:
            t = json.load(fp)
            templates.append({
                "id": f.stem,
                "name": t["name"],
                "description": t.get("description", ""),
                "complexity": t.get("complexity", "medium"),
                "slot_count": len(t.get("slots", [])),
            })
    return {"templates": templates}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    path = TEMPLATES_DIR / f"{template_id}.json"
    if not path.exists():
        raise HTTPException(404, "Template not found")
    with open(path) as fp:
        return json.load(fp)


@router.post("/", status_code=201)
async def create_plant(data: dict, db=Depends(get_db)):
    """Create a plant -- optionally from a template."""
    plant = PlantModel(name=data["name"], description=data.get("description", ""))
    db.add(plant)
    await db.flush()

    template_id = data.get("template_id")
    if template_id:
        path = TEMPLATES_DIR / f"{template_id}.json"
        if not path.exists():
            raise HTTPException(404, f"Template {template_id} not found")
        with open(path) as fp:
            template = json.load(fp)

        # Create loops from template
        for loop_def in template["loops"]:
            loop = LoopModel(
                plant_id=plant.id,
                name=loop_def["name"],
                fluid_type=loop_def["fluid"],
                loop_type=loop_def.get("loop_type", "primary"),
            )
            db.add(loop)

        N = data.get("template_params", {}).get("N", 2)
        S = data.get("template_params", {}).get("standby", 1)
        total = N + S
        plant.description = f"Created from template: {template['name']} ({N}+{S})"

    await db.commit()
    await db.refresh(plant)

    # Save initial version snapshot
    loops_result = await db.execute(
        select(LoopModel).where(LoopModel.plant_id == plant.id)
    )
    plant_loops = loops_result.scalars().all()

    eq_result = await db.execute(
        select(EquipmentModel).where(EquipmentModel.plant_id == plant.id)
    )
    plant_equipment = eq_result.scalars().all()

    new_snapshot = {
        "name": plant.name,
        "description": plant.description,
        "data_source_mode": plant.data_source_mode,
        "is_active": plant.is_active,
        "loops": [
            {"id": l.id, "name": l.name, "fluid_type": l.fluid_type, "loop_type": l.loop_type}
            for l in plant_loops
        ],
        "equipment_ids": [e.id for e in plant_equipment],
    }
    user_id = data.get("changed_by", "system")
    await save_version(
        session=db,
        entity_type="plant_topology",
        entity_id=plant.id,
        old_snapshot={},
        new_snapshot=new_snapshot,
        changed_by=user_id,
        change_reason="Plant created",
    )
    await db.commit()

    errors, warnings = await validate_plant_topology(plant.id, db)
    return {
        "plant": {"id": plant.id, "name": plant.name, "description": plant.description},
        "validation": {"errors": errors, "warnings": warnings},
    }


@router.get("/", response_model=list[dict])
async def list_plants(db=Depends(get_db)):
    result = await db.execute(select(PlantModel).order_by(PlantModel.created_at.desc()))
    plants = result.scalars().all()
    return [
        {"id": p.id, "name": p.name, "description": p.description, "is_active": p.is_active}
        for p in plants
    ]


@router.get("/{plant_id}")
async def get_plant(plant_id: str, db=Depends(get_db)):
    result = await db.execute(select(PlantModel).where(PlantModel.id == plant_id))
    plant = result.scalar_one_or_none()
    if not plant:
        raise HTTPException(404, "Plant not found")

    loops_result = await db.execute(select(LoopModel).where(LoopModel.plant_id == plant_id))
    loops = loops_result.scalars().all()

    pipe_segments = []
    for loop in loops:
        ps_result = await db.execute(
            select(PipeSegmentModel).where(PipeSegmentModel.loop_id == loop.id)
        )
        pipe_segments.extend(ps_result.scalars().all())

    eq_result = await db.execute(
        select(EquipmentModel).where(EquipmentModel.plant_id == plant_id)
    )
    equipment = eq_result.scalars().all()

    return {
        "id": plant.id,
        "name": plant.name,
        "description": plant.description,
        "data_source_mode": plant.data_source_mode,
        "is_active": plant.is_active,
        "loops": [
            {"id": l.id, "name": l.name, "fluid_type": l.fluid_type, "loop_type": l.loop_type}
            for l in loops
        ],
        "pipe_segments": [
            {
                "id": p.id,
                "from_point_id": p.from_point_id,
                "to_point_id": p.to_point_id,
                "diameter_mm": p.diameter_mm,
                "length_m": p.length_m,
            }
            for p in pipe_segments
        ],
        "equipment": [
            {"id": e.id, "name": e.name, "equipment_type_id": e.equipment_type_id}
            for e in equipment
        ],
    }


@router.put("/{plant_id}/pipe-segments")
async def update_pipe_segments(plant_id: str, segments: list[dict], db=Depends(get_db)):
    """Batch update/create pipe segments (for table editor)."""
    # Capture old plant topology state for versioning
    plant_result = await db.execute(
        select(PlantModel).where(PlantModel.id == plant_id)
    )
    plant = plant_result.scalar_one_or_none()
    if not plant:
        raise HTTPException(404, "Plant not found")

    old_loops_result = await db.execute(
        select(LoopModel).where(LoopModel.plant_id == plant_id)
    )
    old_loops = old_loops_result.scalars().all()

    old_pipes_result = await db.execute(
        select(PipeSegmentModel).join(LoopModel).where(LoopModel.plant_id == plant_id)
    )
    old_pipes = old_pipes_result.scalars().all()

    old_equipment_result = await db.execute(
        select(EquipmentModel).where(EquipmentModel.plant_id == plant_id)
    )
    old_equipment = old_equipment_result.scalars().all()

    old_snapshot = {
        "name": plant.name,
        "description": plant.description,
        "data_source_mode": plant.data_source_mode,
        "loops": [
            {"id": l.id, "name": l.name, "fluid_type": l.fluid_type, "loop_type": l.loop_type}
            for l in old_loops
        ],
        "pipe_segments": [
            {
                "id": p.id,
                "loop_id": p.loop_id,
                "from_point_id": p.from_point_id,
                "to_point_id": p.to_point_id,
                "diameter_mm": p.diameter_mm,
                "length_m": p.length_m,
            }
            for p in old_pipes
        ],
        "equipment_ids": [e.id for e in old_equipment],
    }

    for seg in segments:
        if seg.get("id"):
            result = await db.execute(
                select(PipeSegmentModel).where(PipeSegmentModel.id == seg["id"])
            )
            ps = result.scalar_one_or_none()
            if ps:
                for key in ("diameter_mm", "length_m", "roughness_mm", "insulation_type", "valve_id"):
                    if key in seg:
                        setattr(ps, key, seg[key])
        else:
            ps = PipeSegmentModel(
                id=seg.get("id"),
                loop_id=seg["loop_id"],
                from_point_id=seg["from_point_id"],
                to_point_id=seg["to_point_id"],
                diameter_mm=seg.get("diameter_mm", 200),
                length_m=seg.get("length_m", 5.0),
                roughness_mm=seg.get("roughness_mm", 0.045),
                insulation_type=seg.get("insulation_type", "none"),
                valve_id=seg.get("valve_id"),
            )
            db.add(ps)

    # Build new snapshot from the (still-uncommitted) pipe segment state
    new_pipes_result = await db.execute(
        select(PipeSegmentModel).join(LoopModel).where(LoopModel.plant_id == plant_id)
    )
    new_pipes = new_pipes_result.scalars().all()
    new_loops_result = await db.execute(
        select(LoopModel).where(LoopModel.plant_id == plant_id)
    )
    new_loops = new_loops_result.scalars().all()
    new_equipment_result = await db.execute(
        select(EquipmentModel).where(EquipmentModel.plant_id == plant_id)
    )
    new_equipment = new_equipment_result.scalars().all()

    new_snapshot = {
        "name": plant.name,
        "description": plant.description,
        "data_source_mode": plant.data_source_mode,
        "loops": [
            {"id": l.id, "name": l.name, "fluid_type": l.fluid_type, "loop_type": l.loop_type}
            for l in new_loops
        ],
        "pipe_segments": [
            {
                "id": p.id,
                "loop_id": p.loop_id,
                "from_point_id": p.from_point_id,
                "to_point_id": p.to_point_id,
                "diameter_mm": p.diameter_mm,
                "length_m": p.length_m,
            }
            for p in new_pipes
        ],
        "equipment_ids": [e.id for e in new_equipment],
    }

    await save_version(
        session=db,
        entity_type="plant_topology",
        entity_id=plant_id,
        old_snapshot=old_snapshot,
        new_snapshot=new_snapshot,
        changed_by="system",
        change_reason="Pipe segments updated",
    )

    await db.commit()
    errors, warnings = await validate_plant_topology(plant_id, db)
    return {"status": "ok", "validation": {"errors": errors, "warnings": warnings}}
