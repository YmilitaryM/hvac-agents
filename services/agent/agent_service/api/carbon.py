from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from ..carbon.carbon_market import GenericCarbonMarket
from ..carbon.emission_calculator import EmissionCalculator

router = APIRouter()


class EmissionRequest(BaseModel):
    power_kw: float
    duration_hours: float
    emission_factor: float = 0.50


class AllowanceRequest(BaseModel):
    region: str
    total_allowance_tco2: float
    carbon_price: float
    period_start: str
    period_end: str


@router.post("/carbon/emissions")
async def calculate_emissions(req: EmissionRequest):
    tco2 = EmissionCalculator.from_power(
        req.power_kw, req.duration_hours, req.emission_factor
    )
    return {"tco2": round(tco2, 4)}


@router.post("/carbon/cost")
async def carbon_cost(req: AllowanceRequest):
    market = GenericCarbonMarket(
        region=req.region,
        carbon_price=req.carbon_price,
        emission_factor=0.50,
        total_allowance=req.total_allowance_tco2,
        period_start=datetime.fromisoformat(req.period_start),
        period_end=datetime.fromisoformat(req.period_end),
    )
    return {
        "carbon_price": market.carbon_price,
        "emission_factor": market.emission_factor,
        "remaining_allowance": market.allowance_remaining(),
    }
