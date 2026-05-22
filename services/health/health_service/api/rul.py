from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/rul")
async def rul_predictions(plant_id: int = Query(None), equipment_id: int = Query(None)):
    return {
        "items": [
            {"equipment_id": 1, "component": "bearing", "predicted_hours": 2000, "ci_lo": 1500, "ci_hi": 2500, "degradation_model": "weibull"},
            {"equipment_id": 2, "component": "compressor", "predicted_hours": 5000, "ci_lo": 4200, "ci_hi": 5800, "degradation_model": "exp"},
        ],
    }


@router.post("/rul/compute")
async def compute_rul(equipment_id: int = Query(...), component: str = Query(...)):
    return {"equipment_id": equipment_id, "component": component, "status": "triggered", "predicted_hours": 1850}
