import numpy as np
from .base import BaseCalibrator, CalibrationDataPoint, CalibrationResult


class ValveCalibrator(BaseCalibrator):
    """Calibrate valve Cv curve: Cv = f(opening)."""

    def calibrate(self, data: list[CalibrationDataPoint]) -> CalibrationResult:
        if not data:
            raise ValueError("Empty data")
        opening = np.array([d.input_features["opening"] for d in data])
        cv_measured = np.array([d.measured_output for d in data])

        coeffs = np.polyfit(opening, cv_measured, deg=2)
        params = {f"a{i}": round(float(c), 6) for i, c in enumerate(coeffs)}

        cv_pred = np.polyval(coeffs, opening)
        mape = float(np.mean(np.abs((cv_measured - cv_pred) / (cv_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((cv_measured - cv_pred) ** 2)))

        return CalibrationResult(
            equipment_id="unknown", curve_name="Cv-opening",
            original_params={}, calibrated_params=params,
            mape=mape, rmse=rmse, sample_count=len(data)
        )

    def validate(self, data: list[CalibrationDataPoint], params: dict) -> tuple[float, float]:
        opening = np.array([d.input_features["opening"] for d in data])
        cv_measured = np.array([d.measured_output for d in data])
        coeffs = np.array([params["a0"], params["a1"], params["a2"]])
        cv_pred = np.polyval(coeffs, opening)
        mape = float(np.mean(np.abs((cv_measured - cv_pred) / (cv_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((cv_measured - cv_pred) ** 2)))
        return mape, rmse
