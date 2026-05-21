from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/peak-demand")
async def peak_demand(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "current_kw": 450.0,
        "predicted_peak_kw": 520.0,
        "demand_limit_kw": 500.0,
        "warning": True,
        "trend": [420, 440, 460, 450, 470, 490, 450],
        "events": [
            {"id": 1, "start_time": "2026-05-20T14:00:00", "peak_kw": 535.0, "strategy": "load_shift", "actual_reduction_kw": 40.0},
        ],
    }


@router.post("/peak-demand/optimize")
async def optimize_demand(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "recommendations": [
            {"action": "delay_chiller_start", "equipment_id": 3, "delay_minutes": 15},
            {"action": "reduce_chw_flow", "equipment_id": 7, "new_setpoint": 85.0},
        ],
        "expected_peak_reduction_kw": 45.0,
    }
