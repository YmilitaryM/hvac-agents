import numpy as np


class FeatureBuilder:
    """Build feature vectors for ML anomaly detection from equipment sensor readings."""

    @staticmethod
    def build_equipment_vector(sensors: dict[str, float], sensor_order: list[str]) -> np.ndarray:
        vec = np.zeros(len(sensor_order))
        for i, name in enumerate(sensor_order):
            vec[i] = sensors.get(name, 0.0)
        return vec

    @staticmethod
    def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
        mean = vectors.mean(axis=0, keepdims=True)
        std = vectors.std(axis=0, keepdims=True)
        std[std == 0] = 1.0
        return (vectors - mean) / std

    @staticmethod
    def build_efficiency_vector(metrics: dict[str, float]) -> np.ndarray:
        keys = ["cop", "kw_per_rt", "approach_temp", "plr", "delta_t_chw", "delta_t_cw"]
        return np.array([metrics.get(k, 0.0) for k in keys])
