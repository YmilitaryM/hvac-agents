from fastapi import APIRouter
from pydantic import BaseModel

from ..degradation_tracker import DegradationTracker
from ..failure_predictor import FailurePredictor, build_training_data

router = APIRouter()

# Lazy-init predictor, train on first use
_predictor: FailurePredictor | None = None


def _get_predictor() -> FailurePredictor:
    global _predictor
    if _predictor is None:
        _predictor = FailurePredictor()
        X, y = build_training_data()
        _predictor.train(X, y)
    return _predictor


class DegradationRequest(BaseModel):
    edge_id: str
    equipment_id: str
    equipment_type: str
    design_cop: float = 5.5
    cop_window: list[float]
    approach_temp_avg: float = 0.0
    vibration_window: list[float] = []


class PredictRequest(BaseModel):
    cop_current: float
    vibration_rms: float
    approach_temp: float


@router.post("/evaluate")
async def evaluate_degradation(body: DegradationRequest):
    tracker = DegradationTracker(body.equipment_id, body.equipment_type)
    result = tracker.evaluate(
        design_cop=body.design_cop,
        cop_window=body.cop_window,
        approach_temp_avg=body.approach_temp_avg,
        vibration_window=body.vibration_window,
    )
    result["edge_id"] = body.edge_id
    return result


@router.post("/predict")
async def predict_failure(body: PredictRequest):
    p = _get_predictor()
    proba = p.predict_proba([body.cop_current, body.vibration_rms, body.approach_temp])
    return {
        "failure_probability": round(proba, 4),
        "features": {
            "cop_current": body.cop_current,
            "vibration_rms": body.vibration_rms,
            "approach_temp": body.approach_temp,
        },
    }
