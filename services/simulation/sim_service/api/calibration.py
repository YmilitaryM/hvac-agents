from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..calibration.chiller_cal import ChillerCalibrator
from ..calibration.tower_cal import TowerCalibrator
from ..calibration.pump_cal import PumpCalibrator
from ..calibration.valve_cal import ValveCalibrator
from ..calibration.cleaner import DataCleaner
from ..calibration.validator import CalibrationValidator
from ..calibration.base import CalibrationDataPoint

router = APIRouter()

CALIBRATORS = {
    "chiller": ChillerCalibrator,
    "cooling_tower": TowerCalibrator,
    "pump": PumpCalibrator,
    "valve": ValveCalibrator,
}


class CalibrationRequest(BaseModel):
    equipment_id: str
    equipment_type: str
    data: list[dict]


@router.post("/calibration/run")
async def run_calibration(req: CalibrationRequest):
    calibrator_cls = CALIBRATORS.get(req.equipment_type)
    if not calibrator_cls:
        raise HTTPException(400, f"Unknown equipment type: {req.equipment_type}")

    points = [
        CalibrationDataPoint(
            timestamp=p["timestamp"],
            input_features={**p.get("input_features", {}), "equipment_id": req.equipment_id},
            measured_output=p["measured_output"]
        ) for p in req.data
    ]

    cleaned = DataCleaner.clean(points)
    if len(cleaned) < 4:
        raise HTTPException(400, f"Insufficient data after cleaning: {len(cleaned)} points")

    train_data, test_data = CalibrationValidator.split_data(cleaned)
    calibrator = calibrator_cls()
    result = calibrator.calibrate(train_data)

    if test_data:
        test_mape, test_rmse = calibrator.validate(test_data, result.calibrated_params)
        result.mape = test_mape
        result.rmse = test_rmse

    acceptable = CalibrationValidator.is_acceptable(result)

    return {
        "result": {
            "equipment_id": result.equipment_id,
            "curve_name": result.curve_name,
            "calibrated_params": result.calibrated_params,
            "mape": round(result.mape, 2),
            "rmse": round(result.rmse, 2),
            "sample_count": result.sample_count,
            "acceptable": acceptable,
        }
    }


@router.get("/calibration/history")
async def calibration_history(equipment_id: str | None = None):
    return {"history": []}
