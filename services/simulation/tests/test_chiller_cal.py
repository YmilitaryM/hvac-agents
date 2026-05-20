from datetime import datetime, timezone
import pytest
from sim_service.calibration.base import CalibrationDataPoint
from sim_service.calibration.chiller_cal import ChillerCalibrator


def make_data(plr, kw):
    return CalibrationDataPoint(
        timestamp=datetime.now(timezone.utc),
        input_features={"plr": plr, "chwst": 7.0, "cwst": 30.0, "chwrt": 12.0},
        measured_output=kw
    )


def test_chiller_calibration_basic():
    calibrator = ChillerCalibrator()
    data = [
        make_data(0.3, 180.0),
        make_data(0.5, 260.0),
        make_data(0.7, 340.0),
        make_data(1.0, 460.0),
    ]
    result = calibrator.calibrate(data)
    assert result.curve_name == "COP-KW"
    assert result.mape < 10.0
    assert result.rmse < 50.0
    assert len(result.calibrated_params) == 4


def test_chiller_calibration_empty_data():
    calibrator = ChillerCalibrator()
    with pytest.raises(ValueError):
        calibrator.calibrate([])
