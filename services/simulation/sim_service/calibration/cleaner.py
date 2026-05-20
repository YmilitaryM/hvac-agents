import numpy as np
from .base import CalibrationDataPoint


class DataCleaner:
    @staticmethod
    def remove_outliers(data: list[CalibrationDataPoint], sigma: float = 3.0) -> list[CalibrationDataPoint]:
        if len(data) < 5:
            return data
        values = np.array([d.measured_output for d in data])
        mean, std = np.mean(values), np.std(values)
        if std == 0:
            return data
        return [d for d, v in zip(data, values) if abs(v - mean) <= sigma * std]

    @staticmethod
    def remove_startup(data: list[CalibrationDataPoint], min_plr: float = 0.1) -> list[CalibrationDataPoint]:
        return [d for d in data if d.input_features.get("plr", 0.5) >= min_plr]

    @staticmethod
    def remove_stale(data: list[CalibrationDataPoint], max_seconds: float = 300.0) -> list[CalibrationDataPoint]:
        if len(data) < 2:
            return data
        cleaned = [data[0]]
        for i in range(1, len(data)):
            delta = (data[i].timestamp - data[i-1].timestamp).total_seconds()
            if delta <= max_seconds:
                cleaned.append(data[i])
        return cleaned

    @classmethod
    def clean(cls, data: list[CalibrationDataPoint]) -> list[CalibrationDataPoint]:
        data = cls.remove_outliers(data)
        data = cls.remove_startup(data)
        data = cls.remove_stale(data)
        return data
