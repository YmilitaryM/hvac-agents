from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/comparison")
async def energy_comparison(plant_id: int = Query(...), period: str = "month"):
    return {
        "plant_id": plant_id,
        "period": period,
        "current": {"total_kwh": 108000, "avg_cop": 5.2, "avg_power_kw": 450},
        "previous": {"total_kwh": 112000, "avg_cop": 5.0, "avg_power_kw": 467},
        "mom_change_pct": {"total_kwh": -3.6, "avg_cop": 4.0, "avg_power_kw": -3.6},
        "yoy_change_pct": {"total_kwh": -5.2, "avg_cop": 6.1, "avg_power_kw": -5.2},
    }
