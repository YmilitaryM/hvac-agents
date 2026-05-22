from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/diagnosis")
async def diagnosis_history(equipment_id: int = Query(...)):
    return {
        "items": [
            {"id": 1, "equipment_id": equipment_id, "root_cause": "轴承磨损", "confidence": 0.85, "severity": 3, "cert_level": 2, "timestamp": "2026-05-20T10:30:00"},
        ],
    }


@router.post("/diagnosis/run")
async def run_diagnosis(equipment_id: int = Query(...)):
    return {
        "equipment_id": equipment_id,
        "diagnoses": [
            {"rank": 1, "failure_mode": "轴承磨损", "fmea_id": 1, "confidence": 0.85, "severity": 3},
            {"rank": 2, "failure_mode": "不对中", "fmea_id": 3, "confidence": 0.62, "severity": 2},
            {"rank": 3, "failure_mode": "不平衡", "fmea_id": 2, "confidence": 0.45, "severity": 2},
        ],
    }
