"""Cooling load prediction API."""
import time
from fastapi import APIRouter, Depends, Request
from common.auth import require_role, Role
from ..prediction.physics_model import CoolingLoadPhysicsModel
from ..prediction.ml_model import CoolingLoadMLModel
from ..prediction.blender import PredictionBlender
from ..prediction.data_fetcher import PredictionDataFetcher

router = APIRouter()

_physics_model = CoolingLoadPhysicsModel()
_ml_model = CoolingLoadMLModel()
_blender = PredictionBlender()


@router.post("/load")
async def predict_load(
    request: Request,
    data: dict,
    user: dict = Depends(require_role(Role.VIEWER, Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Predict cooling load using physics + ML dual path.

    Body: {
        "building_id": "...",     // optional, fetches from Env Service if provided
        "timestamp": 1234567890,  // optional
        "building": {...},        // optional, manual building params
        "outdoor": {...},         // optional, manual weather
        "indoor": {...}           // optional, manual indoor conditions
    }

    Returns: {physics_load, ml_load, blended_load, alpha, forecasts, ...}
    """
    building = data.get("building", {})
    outdoor = data.get("outdoor", {})
    indoor = data.get("indoor", {})
    time_features = {"hour": int(data.get("hour", time.localtime().tm_hour)),
                     "day_of_week": data.get("day_of_week", time.localtime().tm_wday),
                     "is_holiday": data.get("is_holiday", False),
                     "month": data.get("month", time.localtime().tm_mon)}

    # Try to fetch from services if building_id provided
    building_id = data.get("building_id")
    if building_id:
        sim_url = getattr(request.app.state, "sim_service_url", None) or "http://localhost:8003"
        # Use configured service URLs from app state
        env_url = getattr(request.app.state, "env_service_url", None) or "http://localhost:8002"
        asset_url = getattr(request.app.state, "asset_service_url", None) or "http://localhost:8001"
        fetcher = PredictionDataFetcher(env_url, asset_url)
        fetched = await fetcher.fetch_all(building_id, data.get("timestamp"))
        building = {**fetched["building"], **building}
        outdoor = {**fetched["weather"], **outdoor}
        indoor = {**fetched["indoor"], **indoor}

    # Physics prediction
    physics_result = _physics_model.predict(building, outdoor, indoor, time_features)
    physics_load = physics_result["total_load_rt"]

    # ML prediction
    ml_result = _ml_model.predict({**building, **outdoor, **indoor, **time_features})
    ml_load = ml_result.get("load_rt", 0)
    ml_confidence = ml_result.get("confidence", 0)

    # Blend
    blend_result = _blender.blend(physics_load, ml_load, ml_confidence)

    # Forecast
    forecast = _blender.generate_forecast(
        blend_result["blended_load_rt"],
        time_features["hour"],
        building_type=data.get("building_type", "office"),
        day_of_week=time_features.get("day_of_week", 0),
        is_holiday=time_features.get("is_holiday", False),
    )

    return {
        "timestamp": data.get("timestamp", time.time()),
        "physics_load_rt": physics_load,
        "physics_components": physics_result.get("components", {}),
        "ml_load_rt": ml_load,
        "ml_confidence": ml_confidence,
        "blended_load_rt": blend_result["blended_load_rt"],
        "alpha": blend_result["alpha"],
        "method": blend_result["method"],
        **forecast,
    }
