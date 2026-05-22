from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/power-quality")
async def power_quality(equipment_id: int = Query(...)):
    return {
        "equipment_id": equipment_id,
        "latest": {"thd_v_pct": 3.2, "thd_i_pct": 8.5, "power_factor": 0.93, "voltage_unbalance_pct": 0.8, "frequency_hz": 50.02},
        "trend_thd_v": [3.1, 3.3, 3.2, 3.0, 3.2],
    }
