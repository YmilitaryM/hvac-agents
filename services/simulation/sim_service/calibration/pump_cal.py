import numpy as np
from .base import BaseCalibrator, CalibrationDataPoint, CalibrationResult


class PumpCalibrator(BaseCalibrator):
    """Calibrate pump Q-H curve: head = a0 + a1*Q + a2*Q^2 (at rated speed)."""

    def calibrate(self, data: list[CalibrationDataPoint]) -> CalibrationResult:
        if not data:
            raise ValueError("Empty data")
        flow = np.array([d.input_features["flow_rate"] for d in data])
        head_measured = np.array([d.measured_output for d in data])

        coeffs = np.polyfit(flow, head_measured, deg=2)
        params = {f"a{i}": round(float(c), 6) for i, c in enumerate(coeffs)}

        head_pred = np.polyval(coeffs, flow)
        mape = float(np.mean(np.abs((head_measured - head_pred) / (head_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((head_measured - head_pred) ** 2)))

        return CalibrationResult(
            equipment_id="unknown", curve_name="Q-H",
            original_params={}, calibrated_params=params,
            mape=mape, rmse=rmse, sample_count=len(data)
        )

    def validate(self, data: list[CalibrationDataPoint], params: dict) -> tuple[float, float]:
        flow = np.array([d.input_features["flow_rate"] for d in data])
        head_measured = np.array([d.measured_output for d in data])
        coeffs = np.array([params["a0"], params["a1"], params["a2"]])
        head_pred = np.polyval(coeffs, flow)
        mape = float(np.mean(np.abs((head_measured - head_pred) / (head_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((head_measured - head_pred) ** 2)))
        return mape, rmse
