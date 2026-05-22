from fastapi import APIRouter

router = APIRouter()


@router.get("/equipment/{equipment_id}")
async def equipment_health_detail(equipment_id: int):
    return {
        "equipment_id": equipment_id,
        "overall_score": 85,
        "component_scores": {"compressor": 90, "bearing": 78, "motor_winding": 88, "heat_exchanger": 82},
        "trend": {"direction": "stable", "slope": -0.05},
        "degradation_history": [
            {"date": "2026-05-15", "score": 87},
            {"date": "2026-05-18", "score": 86},
            {"date": "2026-05-21", "score": 85},
        ],
        "latest_rul": {"component": "bearing", "predicted_hours": 2000, "ci_lo": 1500, "ci_hi": 2500},
        "recent_diagnoses": [
            {"id": 1, "root_cause": "轻微不对中", "confidence": 0.72, "date": "2026-05-20"},
        ],
        "vibration_zone": "B",
    }
