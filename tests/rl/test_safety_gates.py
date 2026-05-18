"""Tests for RL safety gates."""

import pytest

from src.rl.safety_gates import check_rl_safety_gates, SafetyGateResult


class TestSafetyGates:
    """Tests for the RL safety gate checks."""

    def test_normal_conditions_allowed(self):
        """Normal operating conditions should allow RL to decide."""
        result = check_rl_safety_gates(
            current_load_rt=750.0,
            outdoor_wb_temp=28.0,
            electricity_price=0.8,
            carbon_intensity=0.5,
        )
        assert result.allowed is True
        assert result.force_human is False
        assert result.force_reject is False
        assert result.force_approve is False

    def test_critical_anomaly_forces_human(self):
        """Critical anomaly should force human review."""
        result = check_rl_safety_gates(
            anomaly_detected=True,
            anomaly_details="CRITICAL warning: chiller pressure exceeded limit",
        )
        assert result.allowed is False
        assert result.force_human is True
        assert "critical_anomaly" in result.conditions_triggered

    def test_emergency_forces_reject(self):
        """Emergency/Fault should force rejection."""
        result = check_rl_safety_gates(
            anomaly_detected=True,
            anomaly_details="FAULT in chiller_1: compressor failure",
        )
        assert result.allowed is False
        assert result.force_reject is True
        assert "emergency_fault" in result.conditions_triggered

    def test_emergency_keyword_variations(self):
        """Both 'FAULT' and 'EMERGENCY' should trigger force_reject."""
        # EMERGENCY
        r1 = check_rl_safety_gates(
            anomaly_detected=True,
            anomaly_details="EMERGENCY shutdown initiated",
        )
        assert r1.allowed is False
        assert r1.force_reject is True

        # fault (lowercase)
        r2 = check_rl_safety_gates(
            anomaly_detected=True,
            anomaly_details="sensor fault detected on tower_2",
        )
        assert r2.allowed is False
        assert r2.force_reject is True

    def test_extreme_weather_forces_human(self):
        """Outdoor wet bulb > 35C should force human review."""
        result = check_rl_safety_gates(outdoor_wb_temp=38.0)
        assert result.allowed is False
        assert result.force_human is True
        assert "extreme_weather" in result.conditions_triggered
        assert "38.0" in result.reason or "38" in result.reason

    def test_weather_boundary(self):
        """35.0C exactly should NOT trigger (only > 35 triggers)."""
        result = check_rl_safety_gates(
            outdoor_wb_temp=35.0,
            current_load_rt=750.0,  # normal load to avoid low-load gate
        )
        assert result.allowed is True  # 35 is NOT > 35

    def test_extreme_load_forces_reject(self):
        """Load > 1400 RT should force rejection."""
        result = check_rl_safety_gates(current_load_rt=1450.0)
        assert result.allowed is False
        assert result.force_reject is True
        assert "extreme_load" in result.conditions_triggered

    def test_load_boundary(self):
        """1400 RT exactly should NOT trigger (only > 1400 triggers)."""
        result = check_rl_safety_gates(current_load_rt=1400.0)
        assert result.allowed is True  # 1400 is NOT > 1400

    def test_very_low_load_forces_reject(self):
        """Load < 50 RT should force rejection."""
        result = check_rl_safety_gates(current_load_rt=30.0)
        assert result.allowed is False
        assert result.force_reject is True
        assert "very_low_load" in result.conditions_triggered

    def test_low_load_boundary(self):
        """50 RT should NOT trigger (only < 50 triggers)."""
        result = check_rl_safety_gates(current_load_rt=50.0)
        assert result.allowed is True

    def test_price_spike_forces_human(self):
        """Electricity price > 3.0 should force human review."""
        result = check_rl_safety_gates(
            electricity_price=3.5,
            current_load_rt=750.0,  # normal load to avoid low-load gate
        )
        assert result.allowed is False
        assert result.force_human is True
        assert "price_spike" in result.conditions_triggered

    def test_price_boundary(self):
        """3.0 exactly should NOT trigger (only > 3.0 triggers)."""
        result = check_rl_safety_gates(
            electricity_price=3.0,
            current_load_rt=750.0,  # normal load to avoid low-load gate
        )
        assert result.allowed is True

    def test_clean_grid_forces_approve(self):
        """Carbon intensity < 0.05 should force approval (clean grid)."""
        result = check_rl_safety_gates(
            carbon_intensity=0.02,
            current_load_rt=750.0,  # normal load to avoid low-load gate
        )
        assert result.allowed is True
        assert result.force_approve is True
        assert "clean_grid" in result.conditions_triggered

    def test_clean_grid_boundary(self):
        """0.05 should NOT trigger (only < 0.05 triggers)."""
        result = check_rl_safety_gates(carbon_intensity=0.05)
        assert result.force_approve is False

    def test_gate_priority_critical_over_emergency(self):
        """Critical anomaly is checked BEFORE emergency/fault and takes priority."""
        result = check_rl_safety_gates(
            anomaly_detected=True,
            anomaly_details="CRITICAL EMERGENCY in main transformer",
        )
        assert result.allowed is False
        assert result.force_human is True
        assert "critical_anomaly" in result.conditions_triggered

    def test_emergency_checked_after_critical(self):
        """Emergency with no CRITICAL keyword should still get rejected."""
        result = check_rl_safety_gates(
            anomaly_detected=True,
            anomaly_details="FAULT in chiller_3 requires attention",
        )
        assert result.allowed is False
        assert result.force_reject is True

    def test_no_anomaly_details_is_safe(self):
        """anomaly_detected=True with empty details should pass through."""
        result = check_rl_safety_gates(
            anomaly_detected=True,
            anomaly_details="",
        )
        # Should pass through to normal gates
        assert "critical_anomaly" not in result.conditions_triggered
        assert "emergency_fault" not in result.conditions_triggered
