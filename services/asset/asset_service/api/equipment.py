from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas.equipment import EquipmentSchema, EquipmentPointSchema
from ..models import EquipmentModel, EquipmentPointModel, EquipmentTypeModel, PointTemplateModel

router = APIRouter()


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.session_factory() as session:
        yield session


async def _equipment_to_schema(eq: EquipmentModel) -> dict:
    pts = eq.points or []
    result = await _build_equipment_dict(eq, pts)
    return result


async def _build_equipment_dict(eq: EquipmentModel, pts: list) -> dict:
    """Build dict from EquipmentModel, resolving point data."""
    return {
        "id": eq.id,
        "name": eq.name,
        "equipment_type_id": eq.equipment_type_id,
        "plant_id": eq.plant_id,
        "design_params": eq.design_params,
        "is_active": eq.is_active,
        "created_at": eq.created_at,
        "points": [
            {
                "id": p.id,
                "equipment_id": p.equipment_id,
                "point_template_id": p.point_template_id,
                "code": p.point_template.code if hasattr(p, 'point_template') and p.point_template else "",
                "name": p.custom_name or "",
                "unit": "",
                "io_direction": "output",
                "current_value": p.current_value,
                "last_updated": p.last_updated,
            }
            for p in pts
        ]
    }


def _equipment_to_schema_sync(eq: EquipmentModel) -> EquipmentSchema:
    """Sync version for when we have loaded points."""
    pts = []
    for p in (eq.points or []):
        code = ""
        if hasattr(p, 'point_template') and p.point_template:
            code = p.point_template.code
        pts.append(EquipmentPointSchema(
            id=p.id,
            equipment_id=p.equipment_id,
            point_template_id=p.point_template_id,
            code=code,
            name=p.custom_name or "",
            unit="",
            io_direction="output",
            current_value=p.current_value,
            last_updated=p.last_updated,
        ))
    return EquipmentSchema(
        id=eq.id,
        name=eq.name,
        equipment_type_id=eq.equipment_type_id,
        plant_id=eq.plant_id,
        design_params=eq.design_params or {},
        is_active=eq.is_active,
        created_at=eq.created_at,
        points=pts,
    )


@router.post("/", response_model=EquipmentSchema, status_code=201)
async def create_equipment(data: dict, db=Depends(get_db)):
    """Create equipment -- auto-generates points from type template."""
    # Look up equipment type
    result = await db.execute(
        select(EquipmentTypeModel).where(EquipmentTypeModel.id == data["equipment_type_id"])
    )
    et = result.scalar_one_or_none()
    if not et:
        raise HTTPException(404, "Equipment type not found")

    eq = EquipmentModel(
        name=data["name"],
        equipment_type_id=data["equipment_type_id"],
        plant_id=data.get("plant_id"),
        design_params=data.get("design_params", {}),
    )
    db.add(eq)
    await db.flush()

    # Auto-generate points from template
    pts_result = await db.execute(
        select(PointTemplateModel)
        .where(PointTemplateModel.equipment_type_id == data["equipment_type_id"])
        .order_by(PointTemplateModel.sort_order)
    )
    for pt in pts_result.scalars().all():
        ep = EquipmentPointModel(
            equipment_id=eq.id,
            point_template_id=pt.id,
            custom_name=pt.name,
            current_value=None,
        )
        db.add(ep)

    await db.commit()
    await db.refresh(eq)
    # Load points for response
    return _equipment_to_schema_sync(eq)


@router.get("/", response_model=list[EquipmentSchema])
async def list_equipment(plant_id: str | None = None, category: str | None = None, db=Depends(get_db)):
    stmt = select(EquipmentModel)
    if plant_id:
        stmt = stmt.where(EquipmentModel.plant_id == plant_id)
    if category:
        # Join with equipment_types to filter by category
        stmt = stmt.join(EquipmentTypeModel).where(EquipmentTypeModel.category == category)
    result = await db.execute(stmt)
    equipment = result.scalars().all()
    return [_equipment_to_schema_sync(eq) for eq in equipment]


@router.get("/{equipment_id}", response_model=EquipmentSchema)
async def get_equipment(equipment_id: str, db=Depends(get_db)):
    result = await db.execute(
        select(EquipmentModel).where(EquipmentModel.id == equipment_id)
    )
    eq = result.scalar_one_or_none()
    if not eq:
        raise HTTPException(404, "Equipment not found")
    return _equipment_to_schema_sync(eq)


@router.put("/{equipment_id}", response_model=EquipmentSchema)
async def update_equipment(equipment_id: str, data: dict, db=Depends(get_db)):
    result = await db.execute(
        select(EquipmentModel).where(EquipmentModel.id == equipment_id)
    )
    eq = result.scalar_one_or_none()
    if not eq:
        raise HTTPException(404, "Equipment not found")
    for key in ("name", "plant_id", "design_params", "is_active"):
        if key in data:
            setattr(eq, key, data[key])
    await db.commit()
    await db.refresh(eq)
    return _equipment_to_schema_sync(eq)


@router.delete("/{equipment_id}", status_code=204)
async def delete_equipment(equipment_id: str, db=Depends(get_db)):
    result = await db.execute(
        select(EquipmentModel).where(EquipmentModel.id == equipment_id)
    )
    eq = result.scalar_one_or_none()
    if not eq:
        raise HTTPException(404, "Equipment not found")
    await db.delete(eq)
    await db.commit()
