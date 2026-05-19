import random


class Sensor:
    """Sensor with configurable noise and drift."""

    def __init__(self, name: str, accuracy: float = 0.1, drift_rate_per_year: float = 0.05,
                 resolution: float = 0.01, fail_probability: float = 0.0):
        self.name = name
        self.sigma = accuracy / 3.0  # 3-sigma
        self.drift_rate = drift_rate_per_year / (365 * 24 * 3600)  # per second
        self.resolution = resolution
        self.fail_probability = fail_probability
        self._drift_offset = 0.0
        self._operational_seconds = 0.0
        self._failed = False

    def read(self, true_value: float, dt_seconds: float = 1.0) -> float:
        """Return measured value = true + noise + drift, quantized."""
        if random.random() < self.fail_probability:
            self._failed = True
        if self._failed:
            return float("nan")

        self._operational_seconds += dt_seconds
        self._drift_offset += self.drift_rate * dt_seconds
        noise = random.gauss(0, self.sigma)
        raw = true_value + noise + self._drift_offset
        if self.resolution > 0:
            raw = round(raw / self.resolution) * self.resolution
        return raw

    def reset_drift(self):
        self._drift_offset = 0.0
        self._operational_seconds = 0.0

    def recover(self):
        self._failed = False
