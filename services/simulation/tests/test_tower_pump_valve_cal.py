from datetime import datetime, timezone
from sim_service.calibration.base import CalibrationDataPoint
from sim_service.calibration.tower_cal import TowerCalibrator
from sim_service.calibration.pump_cal import PumpCalibrator
from sim_service.calibration.valve_cal import ValveCalibrator


def test_tower_calibration():
    calibrator = TowerCalibrator()
    data = [
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"wet_bulb": 24, "load_ratio": 0.8}, measured_output=30.5),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"wet_bulb": 26, "load_ratio": 1.0}, measured_output=32.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"wet_bulb": 22, "load_ratio": 0.5}, measured_output=28.0),
    ]
    result = calibrator.calibrate(data)
    assert result.curve_name == "approach"
    assert result.mape < 20.0


def test_pump_calibration():
    calibrator = PumpCalibrator()
    data = [
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"flow_rate": 100}, measured_output=30.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"flow_rate": 200}, measured_output=28.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"flow_rate": 300}, measured_output=24.0),
    ]
    result = calibrator.calibrate(data)
    assert result.curve_name == "Q-H"
    assert result.mape < 20.0


def test_valve_calibration():
    calibrator = ValveCalibrator()
    data = [
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"opening": 0.2}, measured_output=10.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"opening": 0.5}, measured_output=50.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"opening": 0.8}, measured_output=90.0),
    ]
    result = calibrator.calibrate(data)
    assert result.curve_name == "Cv-opening"
    assert result.mape < 20.0
