import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PlantModel, LoopModel, PipeSegmentModel, EquipmentModel, EquipmentPointModel
from ..validation import validate_plant_topology

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
    await db.commit()
    errors, warnings = await validate_plant_topology(plant_id, db)
    return {"status": "ok", "validation": {"errors": errors, "warnings": warnings}}
