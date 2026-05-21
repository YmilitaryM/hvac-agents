from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/oil")
async def oil_analysis(equipment_id: int = Query(...)):
    return {
        "items": [
            {"id": 1, "sample_date": "2026-05-01", "viscosity": 32.5, "tan": 0.15, "moisture_ppm": 45,
             "wear_metals": {"Fe": 12, "Cu": 3, "Al": 2}, "particle_count_iso": "18/15/12"},
        ],
    }
