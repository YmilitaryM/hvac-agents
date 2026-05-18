"""Tests for the Reliability Advocate Agent."""

import pytest
from src.agents.advocates.reliability import review_reliability, ReliabilityAdvocate
from src.optimization.solver import OptimizationSolution
from src.schemas.review import ReviewVerdict
from src.schemas.strategy import (
    Strategy,
    StrategyAction,
    StrategyStatus,
    TransitionPhase,
    TransitionPlan,
    TriggerType,
)


def make_transition_plan(with_abort: bool = True) -> TransitionPlan:
    """Helper to create a valid transition plan."""
    abort_conditions = (
        ["Any chiller enters FAULT state"] if with_abort else []
    )
    return TransitionPlan(
        total_duration_sec=600.0,
        phases=[
            TransitionPhase(
                seq=1,
                duration_sec=600.0,
                description="Ramp to target",
            )
        ],
        abort_conditions=abort_conditions,
    )


def make_strategy(
    actions: list,
    *,
    trigger_type: TriggerType = TriggerType.SCHEDULED,
    transition_plan: TransitionPlan | None = None,
    risk_mitigations: list | None = None,
    current_load_rt: float = 300.0,
    **kwargs,
) -> Strategy:
    """Helper to create a Strategy with common defaults."""
    if transition_plan is None and trigger_type != TriggerType.FAULT and actions:
        transition_plan = make_transition_plan()

    return Strategy(
        strategy_id="test_strat_1",
        trigger_type=trigger_type,
        current_load_rt=current_load_rt,
        actions=actions,
        transition_plan=transition_plan,
        risk_mitigations=risk_mitigations or [],
        **kwargs,
    )


class TestReviewReliability:
    """Tests for the review_reliability core function."""

    def test_approve_safe_strategy(self):
        """Clean strategy with good margins should be APPROVE."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="start"),
            StrategyAction(seq=2, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(actions, current_load_rt=200.0)
        opinion = review_reliability(strategy)
        assert opinion.verdict == ReviewVerdict.APPROVE
        assert opinion.confidence >= 0.85

    def test_reject_surge_risk(self):
        """Strategy with chiller at 80RT (below 20% of 500RT) should be REJECT."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="start"),
            StrategyAction(seq=2, device="chiller_1", action="set_load", value=80.0),
        ]
        strategy = make_strategy(actions, current_load_rt=80.0)
        opinion = review_reliability(strategy)
        assert opinion.verdict == ReviewVerdict.REJECT
        assert opinion.confidence >= 0.85
        assert any("surge" in c.lower() for c in opinion.concerns)

    def test_conditional_low_headroom(self):
        """Tight capacity margin should be CONDITIONAL_APPROVAL."""
        # Single chiller at 480RT — very close to 500RT capacity
        # This means capacity / load = 500/480 ≈ 1.04 < 1.1, so low headroom
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="start"),
            StrategyAction(seq=2, device="chiller_1", action="set_load", value=480.0),
        ]
        strategy = make_strategy(actions, current_load_rt=480.0)
        opinion = review_reliability(strategy)
        assert opinion.verdict == ReviewVerdict.CONDITIONAL_APPROVAL
        assert any("headroom" in c.lower() or "capacity" in c.lower() for c in opinion.concerns)

    def test_excessive_starts(self):
        """Strategy with 3+ start actions should raise concern."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="start"),
            StrategyAction(seq=2, device="chiller_1", action="set_load", value=150.0),
            StrategyAction(seq=3, device="chiller_2", action="start"),
            StrategyAction(seq=4, device="chiller_2", action="set_load", value=150.0),
            StrategyAction(seq=5, device="chiller_3", action="start"),
            StrategyAction(seq=6, device="chiller_3", action="set_load", value=150.0),
        ]
        strategy = make_strategy(actions, current_load_rt=450.0)
        opinion = review_reliability(strategy)
        # 3 starts is a concern but not a hard violation in itself
        assert opinion.verdict == ReviewVerdict.CONDITIONAL_APPROVAL
        assert any("start" in c.lower() for c in opinion.concerns)

    def test_no_transition_plan_with_changes(self):
        """Has start/stop actions but no transition plan should REJECT."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="stop"),
            StrategyAction(seq=2, device="chiller_2", action="start"),
            StrategyAction(seq=3, device="chiller_2", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            trigger_type=TriggerType.FAULT,
            transition_plan=None,
        )
        opinion = review_reliability(strategy)
        assert opinion.verdict == ReviewVerdict.REJECT
        assert any("transition" in c.lower() or "plan" in c.lower() for c in opinion.concerns)

    def test_abort_conditions_present(self):
        """Strategy has abort conditions should APPROVE (given clean otherwise)."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=250.0),
        ]
        tp = make_transition_plan(with_abort=True)
        strategy = make_strategy(actions, transition_plan=tp, current_load_rt=250.0)
        opinion = review_reliability(strategy)
        assert opinion.verdict == ReviewVerdict.APPROVE

    def test_risk_mitigations_positive(self):
        """Strategy has risk_mitigations should be positive."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=300.0),
        ]
        strategy = make_strategy(
            actions,
            risk_mitigations=["Backup chiller on standby", "Operator on call"],
            current_load_rt=300.0,
        )
        opinion = review_reliability(strategy)
        # Having risk mitigations is positive — may still be CONDITIONAL if other issues
        assert opinion.verdict in (ReviewVerdict.APPROVE, ReviewVerdict.CONDITIONAL_APPROVAL)

    def test_clean_strategy_high_confidence(self):
        """APPROVE verdict should have confidence >= 0.85."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        tp = make_transition_plan(with_abort=True)
        strategy = make_strategy(actions, transition_plan=tp, current_load_rt=200.0)
        opinion = review_reliability(strategy)
        assert opinion.verdict == ReviewVerdict.APPROVE
        assert opinion.confidence >= 0.85

    def test_surge_concern_below_30_pct(self):
        """Chiller below 30% of 500RT (below 150RT) should raise surge concern."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="start"),
            StrategyAction(seq=2, device="chiller_1", action="set_load", value=120.0),
        ]
        strategy = make_strategy(actions, current_load_rt=120.0)
        opinion = review_reliability(strategy)
        # Below 150RT (30%) but above 100RT (20%) — concern, not rejection
        assert opinion.verdict == ReviewVerdict.CONDITIONAL_APPROVAL
        assert any("surge" in c.lower() for c in opinion.concerns)


class TestReliabilityAdvocate:
    """Tests for the ReliabilityAdvocate agent class."""

    @pytest.mark.asyncio
    async def test_run_with_dict_input(self):
        """Agent run should accept dict input and return serialized opinion."""
        agent = ReliabilityAdvocate()
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="start"),
            StrategyAction(seq=2, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(actions, current_load_rt=200.0)
        result = await agent.run({"strategy": strategy.model_dump()})
        assert "opinion" in result
        opinion = result["opinion"]
        assert opinion["advocate"] == "reliability"
        assert opinion["verdict"] in ("approve", "conditional_approval", "reject", "abstain")

    @pytest.mark.asyncio
    async def test_run_with_strategy_object(self):
        """Agent run should accept Strategy object directly."""
        agent = ReliabilityAdvocate()
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        tp = make_transition_plan(with_abort=True)
        strategy = make_strategy(actions, transition_plan=tp, current_load_rt=200.0)
        result = await agent.run({"strategy": strategy})
        assert "opinion" in result
        assert result["opinion"]["advocate"] == "reliability"
