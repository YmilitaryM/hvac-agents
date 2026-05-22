from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/baseline")
async def energy_baseline(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "current_baseline": {
            "baseline_kwh_per_rt": 0.68,
            "method": "regression",
            "r_squared": 0.82,
            "climate_zone": "III",
            "building_type": "office",
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
        "standards_comparison": {
            "gb50189_scop_target": 5.0,
            "current_scop": 5.2,
            "compliant": True,
            "gb19577_grade": 2,
        },
    }


@router.post("/baseline/calibrate")
async def calibrate_baseline(plant_id: int = Query(...), method: str = "regression",
                              period_start: str = None, period_end: str = None):
    return {
        "status": "calibrated",
        "plant_id": plant_id,
        "method": method,
        "new_baseline_kwh_per_rt": 0.66,
        "r_squared": 0.85,
    }
