from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BuildingModel

router = APIRouter()


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.session_factory() as session:
        yield session


@router.post("/buildings", status_code=201)
async def create_building(data: dict, db=Depends(get_db)):
    building = BuildingModel(**data)
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return {"id": building.id, "name": building.name}


@router.get("/buildings")
async def list_buildings(db=Depends(get_db)):
    result = await db.execute(select(BuildingModel))
    buildings = result.scalars().all()
    return {
        "buildings": [
            {"id": b.id, "name": b.name, "area_m2": b.area_m2, "building_type": b.building_type}
            for b in buildings
        ]
    }
