from fastapi import APIRouter

router = APIRouter()


@router.get("/kpi")
async def get_kpi():
    return {"kpi": {"system_cop": 0, "total_cooling_load_rt": 0, "total_power_kw": 0, "outdoor_wb_temp": 0}}


@router.get("/snapshot")
async def get_snapshot():
    return {"snapshot": {}}
