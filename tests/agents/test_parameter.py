"""Tests for the Parameter Agent."""

import pytest

from src.agents.parameter import (
    apply_deadband,
    apply_rate_limit,
    detect_oscillation,
    adjust_parameters,
    ParameterResult,
    ParameterAdjustment,
    ParameterAgent,
)


class TestApplyDeadband:
    def test_deadband_within_range(self):
        value, was_in_deadband = apply_deadband(102.0, 100.0, deadband=5.0)
        assert value == 100.0
        assert was_in_deadband is True

    def test_deadband_outside_range(self):
        value, was_in_deadband = apply_deadband(120.0, 100.0, deadband=5.0)
        assert value == 120.0
        assert was_in_deadband is False

    def test_deadband_exact_boundary(self):
        value, was_in_deadband = apply_deadband(105.0, 100.0, deadband=5.0)
        assert value == 100.0
        assert was_in_deadband is True

    def test_deadband_negative_direction(self):
        value, was_in_deadband = apply_deadband(96.0, 100.0, deadband=5.0)
        assert value == 100.0
        assert was_in_deadband is True


class TestApplyRateLimit:
    def test_rate_limit_applied(self):
        limited, was_limited = apply_rate_limit(300.0, 400.0, max_rate=25.0)
        assert limited == 325.0
        assert was_limited is True

    def test_rate_limit_no_limit(self):
        limited, was_limited = apply_rate_limit(300.0, 310.0, max_rate=25.0)
        assert limited == 310.0
        assert was_limited is False

    def test_rate_limit_negative_direction(self):
        limited, was_limited = apply_rate_limit(400.0, 300.0, max_rate=25.0)
        assert limited == 375.0
        assert was_limited is True

    def test_rate_limit_exact_boundary(self):
        limited, was_limited = apply_rate_limit(300.0, 325.0, max_rate=25.0)
        assert limited == 325.0
        assert was_limited is False


class TestDetectOscillation:
    def test_detect_oscillation_true(self):
        history = [
            {"load": 100.0},
            {"load": 110.0},
            {"load": 105.0},
            {"load": 115.0},
            {"load": 108.0},
        ]
        assert detect_oscillation(history, window_size=5, threshold=0.5) is True

    def test_detect_oscillation_false_monotonic(self):
        history = [
            {"load": 100.0},
            {"load": 110.0},
            {"load": 120.0},
            {"load": 130.0},
            {"load": 140.0},
        ]
        assert detect_oscillation(history, window_size=5, threshold=0.5) is False

    def test_detect_oscillation_false_flat(self):
        history = [
            {"load": 100.0},
            {"load": 100.0},
            {"load": 100.0},
            {"load": 100.0},
            {"load": 100.0},
        ]
        assert detect_oscillation(history, window_size=5, threshold=0.5) is False

    def test_detect_oscillation_short_history(self):
        history = [
            {"load": 100.0},
            {"load": 110.0},
        ]
        assert detect_oscillation(history, window_size=5, threshold=0.5) is False


class TestAdjustParameters:
    def test_adjust_parameters_deadband(self):
        target = {"chiller_1": 400.0}
        current = {"chiller_1": 405.0}
        capacity = {"chiller_1": 500.0}
        result = adjust_parameters(target, current, capacity, deadband_rt=15.0)
        assert result.deadband_active is True
        assert len(result.adjustments) == 1
        assert result.adjustments[0].adjusted_value == 405.0

    def test_adjust_parameters_rate_limited(self):
        target = {"chiller_1": 400.0}
        current = {"chiller_1": 100.0}
        capacity = {"chiller_1": 500.0}
        result = adjust_parameters(target, current, capacity, max_rate_rt_per_min=25.0)
        assert result.rate_limited is True
        assert result.adjustments[0].adjusted_value == 125.0

    def test_adjust_parameters_no_change_needed(self):
        target = {"chiller_1": 400.0}
        current = {"chiller_1": 400.0}
        capacity = {"chiller_1": 500.0}
        result = adjust_parameters(target, current, capacity)
        assert len(result.adjustments) == 0
        assert result.deadband_active is False
        assert result.rate_limited is False

    def test_adjust_parameters_oscillation_triggers_new_strategy(self):
        target = {"chiller_1": 400.0}
        current = {"chiller_1": 300.0}
        capacity = {"chiller_1": 500.0}
        load_history = [
            {"chiller_1": 380.0},
            {"chiller_1": 300.0},
            {"chiller_1": 370.0},
            {"chiller_1": 310.0},
            {"chiller_1": 360.0},
        ]
        result = adjust_parameters(target, current, capacity, load_history=load_history)
        assert result.needs_new_strategy is True
        assert len(result.new_strategy_reason) > 0

    def test_adjust_parameters_large_deviation_triggers_new_strategy(self):
        target = {"chiller_1": 400.0}
        current = {"chiller_1": 100.0}
        capacity = {"chiller_1": 500.0}
        result = adjust_parameters(target, current, capacity, max_rate_rt_per_min=25.0)
        # After rate limiting: adjusted = 125, deviation from target = 275
        # 275 / 500 = 55% > 5% → needs new strategy
        assert result.needs_new_strategy is True

    def test_adjust_parameters_multiple_chillers(self):
        target = {"chiller_1": 400.0, "chiller_2": 300.0, "chiller_3": 0.0}
        current = {"chiller_1": 405.0, "chiller_2": 100.0, "chiller_3": 0.0}
        capacity = {"chiller_1": 500.0, "chiller_2": 500.0, "chiller_3": 500.0}
        result = adjust_parameters(target, current, capacity, deadband_rt=15.0, max_rate_rt_per_min=25.0)
        # chiller_1: deadband (405), chiller_2: rate-limited (100→125), chiller_3: no change
        assert len(result.adjustments) == 2
        assert result.deadband_active is True
        assert result.rate_limited is True
        ch1_adj = [a for a in result.adjustments if a.device == "chiller_1"][0]
        assert ch1_adj.adjusted_value == 405.0
        ch2_adj = [a for a in result.adjustments if a.device == "chiller_2"][0]
        assert ch2_adj.adjusted_value == 125.0

    def test_adjust_parameters_default_capacity(self):
        target = {"chiller_new": 400.0}
        current = {"chiller_new": 100.0}
        capacity = {}
        result = adjust_parameters(target, current, capacity, max_rate_rt_per_min=25.0)
        assert result.rate_limited is True
        assert result.adjustments[0].adjusted_value == 125.0


class TestParameterAgent:
    async def test_parameter_agent_run(self):
        agent = ParameterAgent()
        result = await agent.run(
            {
                "target_loads": {"chiller_1": 400.0},
                "current_loads": {"chiller_1": 405.0},
                "capacity_rt": {"chiller_1": 500.0},
                "deadband_rt": 15.0,
                "max_rate_rt_per_min": 25.0,
            }
        )
        assert "adjustments" in result
        assert result["deadband_active"] is True
        assert len(result["adjustments"]) == 1
