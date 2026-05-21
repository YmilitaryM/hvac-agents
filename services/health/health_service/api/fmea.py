from fastapi import APIRouter, Query, Body

router = APIRouter()


@router.get("/fmea")
async def search_fmea(equipment_type: str = None, component: str = None, q: str = None):
    return {
        "items": [
            {"id": 1, "equipment_type": "centrifugal_chiller", "component": "compressor",
             "failure_mode": "bearing_wear", "severity": 7, "occurrence": 4, "detection": 3, "rpn": 84,
             "mitigation": "定期振动监测，每3个月更换润滑油", "symptoms": {"vibration_rms": ">7.0", "temp_rise": ">10"}},
        ],
    }


@router.post("/fmea")
async def create_fmea(
    equipment_type: str = Body(...), component: str = Body(...),
    failure_mode: str = Body(...), severity: int = Body(...),
    occurrence: int = Body(...), detection: int = Body(...),
    effects: str = Body(None), mitigation: str = Body(None),
    symptoms: dict = Body(None),
):
    rpn = severity * occurrence * detection
    return {"id": 1, "equipment_type": equipment_type, "failure_mode": failure_mode, "rpn": rpn, "status": "created"}
