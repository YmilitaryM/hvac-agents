from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/mv/verify")
async def mv_verify(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "baseline_energy_kwh": 120000.0,
        "actual_energy_kwh": 108000.0,
        "savings_kwh": 12000.0,
        "savings_pct": 10.0,
        "uncertainty_pct": 8.5,
        "cv_rmse_pct": 15.2,
        "nmbe_pct": -1.8,
        "compliant_ashrae_g14": True,
        "compliant_gb28750": True,
        "coal_equivalent_tons": 4.8,
        "carbon_reduction_kg": 9600.0,
    }
