from collections import deque
import numpy as np
from .realtime_rules import QualityEvent


class StatisticalDetector:
    def __init__(self, freeze_window: int = 100, freeze_threshold: float = 0.001):
        self._histories: dict[str, deque] = {}
        self._freeze_window = freeze_window
        self._freeze_threshold = freeze_threshold

    def check_frozen(self, point_id: str, equipment_id: str, value: float) -> QualityEvent | None:
        if point_id not in self._histories:
            self._histories[point_id] = deque(maxlen=self._freeze_window)
        self._histories[point_id].append(value)

        window = self._histories[point_id]
        if len(window) < self._freeze_window:
            return None

        if np.var(list(window)) < self._freeze_threshold:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="sensor_frozen", severity="high",
                value=value, threshold=None,
            )
        return None

    def check_spike(self, point_id: str, equipment_id: str, current: float,
                    previous: float, sigma: float = 5.0) -> QualityEvent | None:
        if previous == 0:
            return None
        change = abs(current - previous) / abs(previous)
        if change > sigma:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="spike", severity="high",
                value=current, threshold=previous * (1 + sigma),
            )
        return None
