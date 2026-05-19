from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.schemas.equipment import EquipmentTypeSchema, PointTemplateSchema
from ..models import EquipmentTypeModel, PointTemplateModel

router = APIRouter()


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.session_factory() as session:
        yield session


@router.get("/equipment-types", response_model=list[EquipmentTypeSchema])
async def list_equipment_types(category: str | None = None, db=Depends(get_db)):
    stmt = select(EquipmentTypeModel)
    if category:
        stmt = stmt.where(EquipmentTypeModel.category == category)
    result = await db.execute(stmt)
    types = result.scalars().all()
    for t in types:
        pts = await db.execute(
            select(PointTemplateModel)
            .where(PointTemplateModel.equipment_type_id == t.id)
            .order_by(PointTemplateModel.sort_order)
        )
        t.points = pts.scalars().all()
    return types


@router.get("/equipment-types/{type_id}", response_model=EquipmentTypeSchema)
async def get_equipment_type(type_id: str, db=Depends(get_db)):
    result = await db.execute(
        select(EquipmentTypeModel).where(EquipmentTypeModel.id == type_id)
    )
    et = result.scalar_one_or_none()
    if not et:
        raise HTTPException(404, "Equipment type not found")
    pts = await db.execute(
        select(PointTemplateModel)
        .where(PointTemplateModel.equipment_type_id == et.id)
        .order_by(PointTemplateModel.sort_order)
    )
    et.points = pts.scalars().all()
    return et
