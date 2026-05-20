import numpy as np
from .base import BaseCalibrator, CalibrationDataPoint, CalibrationResult


class TowerCalibrator(BaseCalibrator):
    """Calibrate cooling tower approach curve: T_out = f(wet_bulb, load, flow)."""

    def calibrate(self, data: list[CalibrationDataPoint]) -> CalibrationResult:
        if not data:
            raise ValueError("Empty data")
        wb = np.array([d.input_features["wet_bulb"] for d in data])
        load_ratio = np.array([d.input_features.get("load_ratio", 0.7) for d in data])
        t_out_measured = np.array([d.measured_output for d in data])

        X = np.column_stack([np.ones(len(data)), wb, load_ratio])
        coeffs, _, _, _ = np.linalg.lstsq(X, t_out_measured, rcond=None)
        params = {f"k{i}": round(float(c), 6) for i, c in enumerate(coeffs)}

        t_pred = X @ coeffs
        mape = float(np.mean(np.abs((t_out_measured - t_pred) / (t_out_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((t_out_measured - t_pred) ** 2)))

        return CalibrationResult(
            equipment_id="unknown", curve_name="approach",
            original_params={}, calibrated_params=params,
            mape=mape, rmse=rmse, sample_count=len(data)
        )

    def validate(self, data: list[CalibrationDataPoint], params: dict) -> tuple[float, float]:
        wb = np.array([d.input_features["wet_bulb"] for d in data])
        load_ratio = np.array([d.input_features.get("load_ratio", 0.7) for d in data])
        t_measured = np.array([d.measured_output for d in data])
        X = np.column_stack([np.ones(len(data)), wb, load_ratio])
        coeffs = np.array([params["k0"], params["k1"], params["k2"]])
        t_pred = X @ coeffs
        mape = float(np.mean(np.abs((t_measured - t_pred) / (t_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((t_measured - t_pred) ** 2)))
        return mape, rmse
