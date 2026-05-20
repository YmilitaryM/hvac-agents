# services/agent/tests/test_degradation_tracker.py
import pytest
from agent_service.predictive_maintenance.degradation_tracker import (
    DegradationTracker, cop_degradation, cusum_detect
)


def test_cop_degradation_normal():
    # Design COP = 5.5, current window avg = 5.3
    degradation = cop_degradation(design_cop=5.5, window_values=[5.2, 5.3, 5.4, 5.3, 5.35])
    assert 2 < degradation < 5  # roughly 3.6%


def test_cop_degradation_severe():
    degradation = cop_degradation(design_cop=5.5, window_values=[3.8, 3.9, 3.7, 3.85, 3.9])
    assert degradation > 25  # roughly 29%


def test_cusum_no_change():
    values = [5.0, 5.1, 4.9, 5.0, 5.1, 4.9, 5.0, 5.1]
    triggered, change_point = cusum_detect(values, threshold=1.0)
    assert not triggered


def test_cusum_detects_shift():
    values = [5.0, 5.1, 4.9, 5.0, 4.0, 3.9, 3.8, 3.7, 3.6, 3.5]
    triggered, change_point = cusum_detect(values, threshold=1.0)
    assert triggered
    assert change_point is not None


def test_degradation_tracker_evaluate():
    tracker = DegradationTracker(equipment_id="CH-1", equipment_type="chiller")
    # Simulate degraded readings
    report = tracker.evaluate(design_cop=5.5, cop_window=[3.8, 3.9, 3.7, 3.85, 3.9],
                              approach_temp_avg=4.5, vibration_window=[1.2, 1.3, 1.1])
    assert report["severity"] in ("normal", "degrading", "critical")
    assert report["cop_degradation_pct"] > 25
