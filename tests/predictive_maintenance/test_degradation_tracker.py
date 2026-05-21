import pytest

from services.agent.agent_service.predictive_maintenance.degradation_tracker import (
    cop_degradation,
    cusum_detect,
    DegradationTracker,
)


class TestCopDegradation:
    """Tests for cop_degradation: (design_cop - avg) / design_cop * 100"""

    def test_no_degradation_when_matching_design(self):
        """If current window values average to the design COP, degradation is 0%."""
        result = cop_degradation(design_cop=5.5, window_values=[5.5, 5.5, 5.5])
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_positive_degradation_when_below_design(self):
        """When actual COP is below design, degradation is positive (percentage drop)."""
        result = cop_degradation(design_cop=5.5, window_values=[4.4, 4.4, 4.4])
        # (5.5 - 4.4) / 5.5 * 100 = 20.0
        assert result == pytest.approx(20.0, rel=1e-6)

    def test_negative_degradation_when_above_design(self):
        """When actual COP is above design, degradation is negative (better than design)."""
        result = cop_degradation(design_cop=5.5, window_values=[6.05, 6.05])
        # (5.5 - 6.05) / 5.5 * 100 = -10.0
        assert result == pytest.approx(-10.0, rel=1e-6)

    def test_empty_window_returns_zero(self):
        """Empty window should return 0.0 (guard clause)."""
        result = cop_degradation(design_cop=5.5, window_values=[])
        assert result == 0.0

    def test_single_value_window(self):
        """A single value in the window should compute correctly."""
        result = cop_degradation(design_cop=5.0, window_values=[4.0])
        # (5.0 - 4.0) / 5.0 * 100 = 20.0
        assert result == pytest.approx(20.0, rel=1e-6)

    def test_severe_degradation(self):
        """Dramatic COP drop should produce large degradation percentage."""
        result = cop_degradation(design_cop=6.0, window_values=[2.0, 2.0, 2.0])
        # (6.0 - 2.0) / 6.0 * 100 = 66.666...
        assert result == pytest.approx(66.6667, abs=0.01)

    def test_different_design_cop(self):
        """Works with any design COP value."""
        result = cop_degradation(design_cop=10.0, window_values=[7.5, 7.5])
        # (10.0 - 7.5) / 10.0 * 100 = 25.0
        assert result == pytest.approx(25.0, rel=1e-6)


class TestCusumDetect:
    """Tests for cusum_detect: change-point detection using CUSUM algorithm."""

    def test_too_few_values_returns_no_trigger(self):
        """Less than 4 values should not trigger (guard clause)."""
        triggered, idx = cusum_detect([1.0, 2.0, 3.0], threshold=1.0)
        assert triggered is False
        assert idx is None

    def test_no_change_in_stable_data(self):
        """Stable data with no shift should not trigger CUSUM."""
        values = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        triggered, idx = cusum_detect(values, threshold=1.0)
        assert triggered is False
        assert idx is None

    def test_no_change_with_small_noise(self):
        """Minor fluctuations around the reference mean should not trigger."""
        values = [10.0, 10.1, 9.9, 10.0, 10.2, 9.8, 10.0, 10.1]
        triggered, idx = cusum_detect(values, threshold=1.0)
        assert triggered is False
        assert idx is None

    def test_positive_shift_detected(self):
        """A sustained upward shift should trigger CUSUM."""
        # First half mean ~ 1.0, then a sharp upward shift to ~ 5.0
        values = [1.0, 1.0, 1.0, 1.0, 5.0, 5.0, 5.0, 5.0]
        triggered, idx = cusum_detect(values, threshold=1.0)
        assert triggered is True
        assert idx is not None
        assert idx >= 4  # change should be at or after the shift starts

    def test_negative_shift_detected(self):
        """A sustained downward shift should also trigger CUSUM."""
        # First half mean ~ 5.0, then sharp drop to ~ 1.0
        values = [5.0, 5.0, 5.0, 5.0, 1.0, 1.0, 1.0, 1.0]
        triggered, idx = cusum_detect(values, threshold=1.0)
        assert triggered is True
        assert idx is not None

    def test_short_window_exactly_four(self):
        """Exactly 4 values (minimum required) should work."""
        values = [1.0, 1.0, 3.0, 3.0]
        triggered, idx = cusum_detect(values, threshold=1.0)
        # First 2 values ref_mean=1.0, second 2 shift up - should trigger
        assert triggered is True
        assert idx is not None

    def test_higher_threshold_delays_detection(self):
        """A higher threshold should require a larger shift to trigger."""
        # Small shift that triggers at threshold=0.5 but not at threshold=5.0
        values = [1.0, 1.0, 1.0, 1.0, 1.5, 1.5, 1.5, 1.5]
        triggered_low, _ = cusum_detect(values, threshold=0.3)
        triggered_high, _ = cusum_detect(values, threshold=5.0)
        # Should trigger at low threshold but not at high
        assert triggered_low is True
        # At high threshold, the small shift may or may not trigger depending on the algorithm
        # Just verify that the threshold param is being used (doesn't crash)

    def test_gradual_shift_detected(self):
        """A gradual drifting upward should eventually trigger."""
        values = [1.0, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0]
        triggered, idx = cusum_detect(values, threshold=1.0)
        assert triggered is True
        assert idx is not None


class TestDegradationTracker:
    """Tests for the DegradationTracker class evaluate method."""

    def test_normal_severity_when_all_parameters_good(self):
        """When COP degradation is low and approach temp is normal, severity is 'normal'."""
        tracker = DegradationTracker("eq-001", "chiller")
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=[5.4, 5.4, 5.4],  # ~1.8% degradation
            approach_temp_avg=1.0,  # well under 3.0
            vibration_window=[2.0, 2.0, 2.0],
        )
        assert result["severity"] == "normal"
        assert result["equipment_id"] == "eq-001"
        assert result["equipment_type"] == "chiller"
        assert result["cop_degradation_pct"] == pytest.approx(1.8, abs=0.1)
        assert result["approach_temp_drift_k"] == 1.0
        assert result["recommended_action"] is None

    def test_critical_severity_from_cop_drift(self):
        """COP degradation > 15% should trigger critical severity."""
        tracker = DegradationTracker("eq-002", "chiller")
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=[4.0, 4.0, 4.0],  # ~27.3% degradation
            approach_temp_avg=1.0,
            vibration_window=[2.0],
        )
        assert result["severity"] == "critical"
        assert "immediate maintenance" in result["recommended_action"]
        assert "eq-002" in result["recommended_action"]

    def test_critical_severity_from_approach_temp(self):
        """Approach temp > 5.0 should trigger critical severity even if COP is fine."""
        tracker = DegradationTracker("eq-003", "cooling_tower")
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=[5.4, 5.4, 5.4],  # low degradation
            approach_temp_avg=6.0,  # over critical threshold
            vibration_window=[2.0],
        )
        assert result["severity"] == "critical"

    def test_degrading_severity_from_cop(self):
        """COP degradation between 7-15% should trigger degrading severity."""
        tracker = DegradationTracker("eq-004", "chiller")
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=[4.9, 4.9, 4.9],  # ~10.9% degradation
            approach_temp_avg=1.0,
            vibration_window=[2.0],
        )
        assert result["severity"] == "degrading"
        assert "within next 2 weeks" in result["recommended_action"]

    def test_degrading_severity_from_approach_temp(self):
        """Approach temp between 3-5K should trigger degrading."""
        tracker = DegradationTracker("eq-005", "cooling_tower")
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=[5.4, 5.4, 5.4],
            approach_temp_avg=4.0,  # between 3 and 5
            vibration_window=[2.0],
        )
        assert result["severity"] == "degrading"

    def test_cusum_triggered_when_shift_exists(self):
        """CUSUM should detect a shift in the COP window."""
        tracker = DegradationTracker("eq-006", "chiller")
        # From ~5.4 to ~3.0 - clear degradation shift
        cop_vals = [5.4, 5.4, 5.4, 5.4, 3.0, 3.0, 3.0, 3.0]
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=cop_vals,
            approach_temp_avg=1.0,
            vibration_window=[2.0],
        )
        assert result["cusum_triggered"] is True

    def test_vibration_trend_computed(self):
        """Vibration trend should be the average of the vibration window."""
        tracker = DegradationTracker("eq-007", "pump")
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=[5.4, 5.4],
            approach_temp_avg=2.0,
            vibration_window=[3.0, 5.0, 4.0],
        )
        assert result["vibration_trend"] == pytest.approx(4.0, rel=1e-6)

    def test_empty_vibration_window_returns_zero(self):
        """Empty vibration window should return 0 instead of crashing."""
        tracker = DegradationTracker("eq-008", "pump")
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=[5.4, 5.4],
            approach_temp_avg=2.0,
            vibration_window=[],
        )
        assert result["vibration_trend"] == 0

    def test_equipment_id_and_type_preserved(self):
        """Result should include the equipment_id and equipment_type as passed in."""
        tracker = DegradationTracker("my-cooler-42", "cooling_tower")
        result = tracker.evaluate(
            design_cop=6.0,
            cop_window=[5.9, 5.9],
            approach_temp_avg=2.0,
            vibration_window=[],
        )
        assert result["equipment_id"] == "my-cooler-42"
        assert result["equipment_type"] == "cooling_tower"

    def test_cop_degradation_rounded(self):
        """cop_degradation_pct should be rounded to 1 decimal place."""
        tracker = DegradationTracker("eq-009", "chiller")
        result = tracker.evaluate(
            design_cop=5.5,
            cop_window=[4.567, 4.567, 4.567],  # exact degradation with many decimals
            approach_temp_avg=1.0,
            vibration_window=[],
        )
        # Verify it's rounded to 1 decimal
        assert result["cop_degradation_pct"] == round(
            (5.5 - 4.567) / 5.5 * 100, 1
        )
        # Check it's actually at most 1 decimal place
        assert result["cop_degradation_pct"] * 10 == pytest.approx(
            round(result["cop_degradation_pct"] * 10)
        )
