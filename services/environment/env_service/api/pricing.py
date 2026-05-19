from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EnergyPriceModel

router = APIRouter()


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.session_factory() as session:
        yield session


@router.post("/pricing")
async def set_pricing(data: dict, db=Depends(get_db)):
    """Set energy pricing for a timestamp."""
    price = EnergyPriceModel(
        timestamp=data["timestamp"],
        electricity_price_per_kwh=data["price_per_kwh"],
        carbon_intensity_kg_per_kwh=data.get("carbon_intensity", 0),
    )
    db.add(price)
    await db.commit()
    return {"status": "ok"}


@router.get("/pricing")
async def get_pricing(from_ts: float, to_ts: float, db=Depends(get_db)):
    result = await db.execute(
        select(EnergyPriceModel)
        .where(EnergyPriceModel.timestamp >= from_ts)
        .where(EnergyPriceModel.timestamp <= to_ts)
        .order_by(EnergyPriceModel.timestamp.asc())
        .limit(10000)
    )
    prices = result.scalars().all()
    return {
        "prices": [
            {
                "timestamp": p.timestamp,
                "price": p.electricity_price_per_kwh,
                "carbon": p.carbon_intensity_kg_per_kwh,
            }
            for p in prices
        ]
    }
