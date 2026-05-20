from fastapi import APIRouter
from pydantic import BaseModel

from ..optimization.station_dispatch import StationStatus, inter_station_dispatch

router = APIRouter()


class DispatchRequest(BaseModel):
    stations: list[dict]
    total_load_rt: float
    carbon_budget_tco2: float | None = None


@router.post("/dispatch/inter-station")
async def dispatch(req: DispatchRequest):
    stations = [
        StationStatus(
            station_id=s["station_id"],
            available_capacity=s["available_capacity"],
            marginal_cost=s["marginal_cost"],
            current_load=s["current_load"],
            cop=s["cop"],
            carbon_intensity=s.get("carbon_intensity", 0.0),
        )
        for s in req.stations
    ]
    result = inter_station_dispatch(stations, req.total_load_rt, req.carbon_budget_tco2)
    return {
        "targets": result.stations,
        "marginal_costs": result.marginal_cost,
        "unused_capacity": result.unused_capacity,
    }
