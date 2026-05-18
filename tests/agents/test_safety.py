"""Tests for the Safety Agent — pure rule engine."""

import pytest

from src.agents.safety import check_safety, SafetyCheckResult, SafetyAgent
from src.schemas.strategy import (
    Strategy,
    StrategyAction,
    TransitionPhase,
    TransitionPlan,
    TriggerType,
)
from src.simulation.chiller import CentrifugalChiller


def make_transition_plan(with_abort=True):
    abort_conditions = ["Any chiller enters FAULT state"] if with_abort else []
    return TransitionPlan(
        total_duration_sec=600.0,
        phases=[
            TransitionPhase(
                seq=1, duration_sec=600.0, description="Ramp to target"
            )
        ],
        abort_conditions=abort_conditions,
    )


def make_strategy(actions, **kwargs):
    defaults = dict(
        strategy_id="test-safety-1",
        trigger_type=TriggerType.SCHEDULED,
        actions=actions,
        current_load_rt=500.0,
        outdoor_wb_temp=26.0,
    )
    defaults.update(kwargs)
    # For non-FAULT triggers with actions, we need a transition plan
    if (
        defaults["trigger_type"] != TriggerType.FAULT
        and defaults["actions"]
        and "transition_plan" not in defaults
    ):
        defaults["transition_plan"] = make_transition_plan()
    return Strategy(**defaults)


class TestCheckSafety:
    def test_pass_clean_strategy(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="set_load", value=400.0),
                StrategyAction(seq=2, device="chiller_2", action="set_load", value=200.0),
            ],
            current_load_rt=600.0,
        )
        result = check_safety(s)
        assert result.passed is True
        assert len(result.failures) == 0
        assert result.blocking is False

    def test_block_surge_violation(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="set_load", value=50.0),
            ],
            current_load_rt=100.0,
        )
        result = check_safety(s)
        assert result.passed is False
        assert result.blocking is True
        assert any("surge" in f.lower() for f in result.failures)

    def test_block_missing_transition_plan(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="start"),
                StrategyAction(seq=2, device="chiller_1", action="set_load", value=400.0),
            ],
            trigger_type=TriggerType.FAULT,
        )
        # No transition_plan for FAULT trigger with start/stop actions
        # This should fail the safety check
        result = check_safety(s)
        assert result.passed is False
        assert result.blocking is True
        assert any(
            "transition" in f.lower() or "plan" in f.lower()
            for f in result.failures
        )

    def test_warn_min_runtime(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="stop"),
            ],
            current_load_rt=300.0,
        )
        device_states = {
            "chiller_1": {"last_start_time": 500.0, "last_stop_time": None},
        }
        result = check_safety(s, device_states=device_states, current_time=600.0)
        assert result.passed is True
        assert len(result.failures) == 0
        assert len(result.warnings) >= 1
        assert any(
            "runtime" in w.lower() or "too short" in w.lower() for w in result.warnings
        )
        assert result.blocking is False

    def test_block_motor_start_interval(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="start"),
                StrategyAction(seq=2, device="chiller_1", action="set_load", value=400.0),
            ],
            current_load_rt=400.0,
            trigger_type=TriggerType.FAULT,
            transition_plan=make_transition_plan(),
        )
        recent_motor_starts = [("chiller_2", 590.0)]
        result = check_safety(
            s, current_time=600.0, recent_motor_starts=recent_motor_starts
        )
        assert result.passed is False
        assert result.blocking is True
        assert any(
            "motor" in f.lower() or "start" in f.lower() for f in result.failures
        )

    def test_warn_missing_abort_conditions(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="set_load", value=400.0),
            ],
            current_load_rt=400.0,
            transition_plan=make_transition_plan(with_abort=False),
        )
        result = check_safety(s)
        assert result.passed is True
        assert len(result.failures) == 0
        assert len(result.warnings) >= 1
        assert any(
            "abort" in w.lower() for w in result.warnings
        )

    def test_warn_high_ambient(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="set_load", value=400.0),
            ],
            current_load_rt=400.0,
            outdoor_wb_temp=32.0,
        )
        result = check_safety(s)
        assert result.passed is True
        assert len(result.warnings) >= 1
        assert any(
            "ambient" in w.lower() or "temperature" in w.lower()
            for w in result.warnings
        )

    def test_pass_with_warnings(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="set_load", value=400.0),
            ],
            current_load_rt=400.0,
            outdoor_wb_temp=32.0,
            transition_plan=make_transition_plan(with_abort=False),
        )
        result = check_safety(s)
        assert result.passed is True
        assert result.blocking is False
        assert len(result.warnings) >= 2

    def test_zero_load_strategy(self):
        s = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="stop"),
                StrategyAction(seq=2, device="chiller_2", action="stop"),
            ],
            current_load_rt=0.0,
        )
        result = check_safety(s)
        assert result.passed is True
        assert result.blocking is False
        assert len(result.failures) == 0


class TestSafetyAgent:
    async def test_safety_agent_run(self):
        strategy = make_strategy(
            [
                StrategyAction(seq=1, device="chiller_1", action="set_load", value=400.0),
            ],
            current_load_rt=400.0,
        )
        agent = SafetyAgent()
        result = await agent.run(
            {
                "pending_strategy": strategy,
                "t_cw": 30.0,
                "current_time": 0.0,
            }
        )
        assert "safety_result" in result
        assert result["safety_result"]["passed"] is True
        assert result["safety_result"]["blocking"] is False
