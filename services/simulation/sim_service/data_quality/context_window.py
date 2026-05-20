from __future__ import annotations

from collections import defaultdict

import numpy as np

from .realtime_rules import QualityEvent


class BaselineComparator:
    """Maintains EWMA baselines per (hour_of_day, day_type) key for each point_id."""

    def __init__(self, alpha: float = 0.1, sigma_pct: float = 0.05):
        self._alpha = alpha
        self._sigma_pct = sigma_pct
        # _baselines[point_id][(hour, day_type)] -> ewma_value
        self._baselines: dict[str, dict[tuple[int, str], float]] = defaultdict(dict)

    def update_baseline(self, point_id: str, hour: int, day_type: str, value: float) -> None:
        key = (hour, day_type)
        prev = self._baselines[point_id].get(key)
        if prev is None:
            self._baselines[point_id][key] = value
        else:
            self._baselines[point_id][key] = self._alpha * value + (1 - self._alpha) * prev

    def check(
        self, point_id: str, equipment_id: str,
        hour: int, day_type: str, value: float,
    ) -> QualityEvent | None:
        key = (hour, day_type)
        baseline = self._baselines[point_id].get(key)
        if baseline is None or baseline == 0:
            return None
        deviation = abs(value - baseline) / abs(baseline)
        if deviation > 3 * self._sigma_pct:
            return QualityEvent(
                point_id=point_id,
                equipment_id=equipment_id,
                event_type="baseline_deviation",
                severity="warning",
                value=value,
                threshold=baseline * (1 + 3 * self._sigma_pct),
            )
        return None


class DriftTracker:
    """CUSUM + EWMA for tracking slow degradation."""

    def __init__(self, alpha: float = 0.1, cusum_threshold: float = 5.0):
        self._alpha = alpha
        self._cusum_threshold = cusum_threshold
        # _ewma[point_id] -> current ewma
        self._ewma: dict[str, float] = {}
        # _cusum_pos[point_id] -> accumulated positive CUSUM
        self._cusum_pos: dict[str, float] = defaultdict(float)
        # _cusum_neg[point_id] -> accumulated negative CUSUM
        self._cusum_neg: dict[str, float] = defaultdict(float)

    def update(self, point_id: str, value: float) -> None:
        if point_id not in self._ewma:
            self._ewma[point_id] = value
            return

        prev_ewma = self._ewma[point_id]
        new_ewma = self._alpha * value + (1 - self._alpha) * prev_ewma
        self._ewma[point_id] = new_ewma

        residual = value - new_ewma
        slack = self._cusum_threshold * 0.05  # small allowance to avoid windup

        self._cusum_pos[point_id] = max(0.0, self._cusum_pos[point_id] + residual - slack)
        self._cusum_neg[point_id] = max(0.0, self._cusum_neg[point_id] - residual - slack)

    def check(self, point_id: str, equipment_id: str) -> QualityEvent | None:
        pos = self._cusum_pos.get(point_id, 0.0)
        neg = self._cusum_neg.get(point_id, 0.0)

        if pos > self._cusum_threshold:
            return QualityEvent(
                point_id=point_id,
                equipment_id=equipment_id,
                event_type="drift_detected",
                severity="high",
                value=pos,
                threshold=self._cusum_threshold,
                metadata={"drift_direction": "up"},
            )
        if neg > self._cusum_threshold:
            return QualityEvent(
                point_id=point_id,
                equipment_id=equipment_id,
                event_type="drift_detected",
                severity="high",
                value=neg,
                threshold=self._cusum_threshold,
                metadata={"drift_direction": "down"},
            )
        return None


class PeerComparator:
    """Groups points by equipment type for peer comparison."""

    def __init__(self, max_deviation_pct: float = 0.05):
        self._max_deviation_pct = max_deviation_pct
        # _groups[group_name] -> set of point_ids
        self._groups: dict[str, set[str]] = {}
        # _values[point_id] -> latest value
        self._values: dict[str, float] = {}

    def add_peer_group(self, group_name: str, point_ids: set[str]) -> None:
        self._groups[group_name] = point_ids

    def update_value(self, point_id: str, value: float) -> None:
        self._values[point_id] = value

    def check(
        self, point_id: str, equipment_id: str,
        value: float, group_name: str,
    ) -> QualityEvent | None:
        group = self._groups.get(group_name)
        if not group:
            return None

        group_values = [
            self._values[pid]
            for pid in group
            if pid in self._values
        ]
        if not group_values:
            return None

        median = float(np.median(group_values))
        if median == 0:
            return None

        deviation = abs(value - median) / abs(median)
        if deviation > self._max_deviation_pct:
            return QualityEvent(
                point_id=point_id,
                equipment_id=equipment_id,
                event_type="peer_deviation",
                severity="warning",
                value=value,
                threshold=median * (1 + self._max_deviation_pct),
                metadata={"group_name": group_name, "group_median": median},
            )
        return None


class OperationalChecker:
    """Checks for physically impossible or improbable operational states."""

    def check_freeze_risk(
        self, point_id: str, equipment_id: str,
        temp_value: float,
        is_cooling_mode: bool = True,
    ) -> QualityEvent | None:
        if temp_value < 2.0 and is_cooling_mode:
            return QualityEvent(
                point_id=point_id,
                equipment_id=equipment_id,
                event_type="freeze_risk",
                severity="critical",
                value=temp_value,
                threshold=2.0,
            )
        return None

    def check_missing_free_cooling(
        self, point_id: str, equipment_id: str,
        ambient_temp: float,
        is_mechanical_cooling: bool,
    ) -> QualityEvent | None:
        if ambient_temp < 10.0 and is_mechanical_cooling:
            return QualityEvent(
                point_id=point_id,
                equipment_id=equipment_id,
                event_type="missing_free_cooling",
                severity="high",
                value=ambient_temp,
                threshold=10.0,
            )
        return None
