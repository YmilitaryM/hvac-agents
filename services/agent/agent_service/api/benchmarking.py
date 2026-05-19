"""Multi-plant benchmarking API."""
from fastapi import APIRouter, Depends, Query
from common.auth import require_role, Role
from ..benchmarking.engine import PlantBenchmarker

router = APIRouter()

_benchmarker = PlantBenchmarker()


@router.get("/plants")
async def benchmark_plants(
    plant_ids: str = Query(None),
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Compare energy efficiency across plants."""
    ids = [p.strip() for p in plant_ids.split(",")] if plant_ids else []
    if ids:
        result = _benchmarker.compare(ids)
        return result
    return {
        "rankings": [],
        "group_avg_cop": 0,
        "total_plants": 0,
        "message": "Provide snapshot data via POST for comparison",
    }


@router.get("/plant/{plant_id}/trend")
async def plant_trend(
    plant_id: str,
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Get COP/carbon trend for a single plant."""
    return _benchmarker.get_trend(plant_id)
