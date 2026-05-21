from datetime import datetime, timedelta, timezone

import pytest

from services.agent.agent_service.predictive_maintenance.maintenance_scheduler import (
    recommend_window,
)


class TestRecommendWindow:
    """Tests for recommend_window that generates scheduling windows by severity."""

    # ------------------------------------------------------------------
    # Critical severity
    # ------------------------------------------------------------------

    def test_critical_severity_returns_immediate_urgency(self):
        """Critical severity should have urgency 'immediate'."""
        result = recommend_window("critical")
        assert result["urgency"] == "immediate"
        assert result["severity"] == "critical"

    def test_critical_starts_within_4_hours(self):
        """Critical maintenance should start within 4 hours from now."""
        now = datetime.now(timezone.utc)
        result = recommend_window("critical", current_time=now)
        start = datetime.fromisoformat(result["recommended_start"])
        expected_start = now + timedelta(hours=4)
        assert start == pytest.approx(expected_start, abs=timedelta(seconds=1))

    def test_critical_deadline_within_2_days(self):
        """Critical maintenance deadline should be 2 days from now."""
        now = datetime.now(timezone.utc)
        result = recommend_window("critical", current_time=now)
        deadline = datetime.fromisoformat(result["deadline"])
        expected_deadline = now + timedelta(days=2)
        assert deadline == pytest.approx(expected_deadline, abs=timedelta(seconds=1))

    def test_critical_window_is_reasonable(self):
        """Critical start should be before the deadline."""
        now = datetime.now(timezone.utc)
        result = recommend_window("critical", current_time=now)
        start = datetime.fromisoformat(result["recommended_start"])
        deadline = datetime.fromisoformat(result["deadline"])
        assert start < deadline

    # ------------------------------------------------------------------
    # Degrading severity
    # ------------------------------------------------------------------

    def test_degrading_severity_returns_planned_urgency(self):
        """Degrading severity should have urgency 'planned'."""
        result = recommend_window("degrading")
        assert result["urgency"] == "planned"
        assert result["severity"] == "degrading"

    def test_degrading_starts_after_3_days(self):
        """Degrading maintenance should start 3 days from now."""
        now = datetime.now(timezone.utc)
        result = recommend_window("degrading", current_time=now)
        start = datetime.fromisoformat(result["recommended_start"])
        expected_start = now + timedelta(days=3)
        assert start == pytest.approx(expected_start, abs=timedelta(seconds=1))

    def test_degrading_deadline_14_days(self):
        """Degrading maintenance deadline should be 14 days from now."""
        now = datetime.now(timezone.utc)
        result = recommend_window("degrading", current_time=now)
        deadline = datetime.fromisoformat(result["deadline"])
        expected_deadline = now + timedelta(days=14)
        assert deadline == pytest.approx(expected_deadline, abs=timedelta(seconds=1))

    def test_degrading_window_is_reasonable(self):
        """Degrading start should be before the deadline."""
        now = datetime.now(timezone.utc)
        result = recommend_window("degrading", current_time=now)
        start = datetime.fromisoformat(result["recommended_start"])
        deadline = datetime.fromisoformat(result["deadline"])
        assert start < deadline

    # ------------------------------------------------------------------
    # Normal / unknown severity
    # ------------------------------------------------------------------

    def test_normal_severity_returns_planned_urgency(self):
        """Normal severity should have urgency 'planned'."""
        result = recommend_window("normal")
        assert result["urgency"] == "planned"
        assert result["severity"] == "normal"

    def test_normal_starts_after_7_days(self):
        """Normal maintenance should start 7 days from now."""
        now = datetime.now(timezone.utc)
        result = recommend_window("normal", current_time=now)
        start = datetime.fromisoformat(result["recommended_start"])
        expected_start = now + timedelta(days=7)
        assert start == pytest.approx(expected_start, abs=timedelta(seconds=1))

    def test_normal_deadline_30_days(self):
        """Normal maintenance deadline should be 30 days from now."""
        now = datetime.now(timezone.utc)
        result = recommend_window("normal", current_time=now)
        deadline = datetime.fromisoformat(result["deadline"])
        expected_deadline = now + timedelta(days=30)
        assert deadline == pytest.approx(expected_deadline, abs=timedelta(seconds=1))

    def test_unknown_severity_uses_normal_default(self):
        """Any unrecognized severity string should fall into the 'else' (normal) branch."""
        now = datetime.now(timezone.utc)
        result = recommend_window("some_unknown_status", current_time=now)
        # Should use normal scheduling
        start = datetime.fromisoformat(result["recommended_start"])
        expected_start = now + timedelta(days=7)
        assert start == pytest.approx(expected_start, abs=timedelta(seconds=1))
        assert result["urgency"] == "planned"

    # ------------------------------------------------------------------
    # Explicit current_time
    # ------------------------------------------------------------------

    def test_explicit_current_time_is_used(self):
        """When current_time is passed explicitly, all dates are relative to it."""
        fixed_now = datetime(2026, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = recommend_window("critical", current_time=fixed_now)

        start = datetime.fromisoformat(result["recommended_start"])
        deadline = datetime.fromisoformat(result["deadline"])

        assert start == fixed_now + timedelta(hours=4)
        assert deadline == fixed_now + timedelta(days=2)

    def test_explicit_time_degrading(self):
        """Verify explicit current_time for degrading severity."""
        fixed_now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = recommend_window("degrading", current_time=fixed_now)

        start = datetime.fromisoformat(result["recommended_start"])
        deadline = datetime.fromisoformat(result["deadline"])

        assert start == fixed_now + timedelta(days=3)
        assert deadline == fixed_now + timedelta(days=14)

    def test_explicit_time_normal(self):
        """Verify explicit current_time for normal severity."""
        fixed_now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = recommend_window("normal", current_time=fixed_now)

        start = datetime.fromisoformat(result["recommended_start"])
        deadline = datetime.fromisoformat(result["deadline"])

        assert start == fixed_now + timedelta(days=7)
        assert deadline == fixed_now + timedelta(days=30)

    # ------------------------------------------------------------------
    # Return structure
    # ------------------------------------------------------------------

    def test_result_structure(self):
        """The result dict must have all required keys with correct types."""
        result = recommend_window("critical")
        assert isinstance(result["severity"], str)
        assert isinstance(result["recommended_start"], str)
        assert isinstance(result["deadline"], str)
        assert isinstance(result["urgency"], str)
        assert result["urgency"] in ("immediate", "planned")

    def test_isoformat_strings_parseable(self):
        """All ISO format strings should be parseable back to datetime."""
        result = recommend_window("critical")
        datetime.fromisoformat(result["recommended_start"])
        datetime.fromisoformat(result["deadline"])

    def test_default_current_time_is_utc(self):
        """When current_time is not provided, times should be in UTC."""
        result = recommend_window("normal")
        deadline = datetime.fromisoformat(result["deadline"])
        assert deadline.tzinfo is not None

    def test_recommend_window_is_deterministic(self):
        """Same severity and current_time produce same results."""
        fixed_now = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
        r1 = recommend_window("critical", current_time=fixed_now)
        r2 = recommend_window("critical", current_time=fixed_now)
        assert r1 == r2
