import numpy as np
from .base import BaseCalibrator, CalibrationDataPoint, CalibrationResult


class ChillerCalibrator(BaseCalibrator):
    def calibrate(self, data: list[CalibrationDataPoint]) -> CalibrationResult:
        if not data:
            raise ValueError("Empty calibration data")

        plr = np.array([d.input_features["plr"] for d in data])
        kw_measured = np.array([d.measured_output for d in data])

        coeffs = np.polyfit(plr, kw_measured, deg=3)
        params = {f"a{i}": round(float(c), 6) for i, c in enumerate(coeffs)}

        kw_pred = np.polyval(coeffs, plr)
        mape = float(np.mean(np.abs((kw_measured - kw_pred) / (kw_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((kw_measured - kw_pred) ** 2)))

        return CalibrationResult(
            equipment_id=data[0].input_features.get("equipment_id", "unknown"),
            curve_name="COP-KW",
            original_params={},
            calibrated_params=params,
            mape=mape, rmse=rmse, sample_count=len(data)
        )

    def validate(self, data: list[CalibrationDataPoint], params: dict) -> tuple[float, float]:
        coeffs = [params["a0"], params["a1"], params["a2"], params["a3"]]
        plr = np.array([d.input_features["plr"] for d in data])
        kw_measured = np.array([d.measured_output for d in data])
        kw_pred = np.polyval(coeffs, plr)
        mape = float(np.mean(np.abs((kw_measured - kw_pred) / (kw_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((kw_measured - kw_pred) ** 2)))
        return mape, rmse
