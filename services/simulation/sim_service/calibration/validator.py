import numpy as np
from .base import CalibrationDataPoint, CalibrationResult


class CalibrationValidator:
    MAPE_THRESHOLD = 15.0
    RMSE_THRESHOLD = 100.0

    @classmethod
    def is_acceptable(cls, result: CalibrationResult) -> bool:
        return result.mape < cls.MAPE_THRESHOLD and result.rmse < cls.RMSE_THRESHOLD

    @classmethod
    def split_data(cls, data: list[CalibrationDataPoint], train_ratio: float = 0.8):
        n = len(data)
        indices = np.random.RandomState(42).permutation(n)
        split = int(n * train_ratio)
        train_idx = indices[:split]
        test_idx = indices[split:]
        return [data[i] for i in train_idx], [data[i] for i in test_idx]
