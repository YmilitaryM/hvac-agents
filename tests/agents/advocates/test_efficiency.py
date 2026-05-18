"""Tests for the Efficiency Advocate Agent."""

import pytest
from src.agents.advocates.efficiency import review_efficiency, EfficiencyAdvocate
from src.optimization.solver import OptimizationSolution
from src.schemas.review import ReviewVerdict
from src.schemas.strategy import (
    Strategy,
    StrategyAction,
    TransitionPhase,
    TransitionPlan,
    TriggerType,
)


def make_transition_plan(duration_sec: float = 600.0) -> TransitionPlan:
    """Helper to create a valid transition plan."""
    return TransitionPlan(
        total_duration_sec=duration_sec,
        phases=[
            TransitionPhase(
                seq=1,
                duration_sec=duration_sec,
                description="Ramp to target",
            )
        ],
        abort_conditions=["Any chiller enters FAULT state"],
    )


def make_strategy(
    actions: list,
    *,
    trigger_type: TriggerType = TriggerType.SCHEDULED,
    transition_plan: TransitionPlan | None = None,
    expected_cop_improvement: float | None = None,
    expected_energy_saving_kwh_per_h: float | None = None,
    electricity_price: float = 0.8,
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
        expected_cop_improvement=expected_cop_improvement,
        expected_energy_saving_kwh_per_h=expected_energy_saving_kwh_per_h,
        electricity_price=electricity_price,
        **kwargs,
    )


def make_solution(chiller_loads: dict, energy_cost: float = 10.0,
                  carbon_cost: float = 2.0, total_power_kw: float = 100.0) -> OptimizationSolution:
    """Helper to create an OptimizationSolution."""
    return OptimizationSolution(
        chiller_loads=chiller_loads,
        total_power_kw=total_power_kw,
        total_objective=50.0,
        energy_cost=energy_cost,
        carbon_cost=carbon_cost,
        wear_cost=100.0,
    )


class TestReviewEfficiency:
    """Tests for the review_efficiency core function."""

    def test_approve_efficient_strategy(self):
        """COP improvement > 0.05, energy savings positive should APPROVE."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_cop_improvement=0.10,
            expected_energy_saving_kwh_per_h=50.0,
            current_load_rt=200.0,
        )
        opinion = review_efficiency(strategy)
        assert opinion.verdict == ReviewVerdict.APPROVE
        assert opinion.confidence >= 0.85

    def test_reject_negative_savings(self):
        """Negative expected_energy_saving_kwh_per_h should REJECT."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_energy_saving_kwh_per_h=-10.0,
            current_load_rt=200.0,
        )
        opinion = review_efficiency(strategy)
        assert opinion.verdict == ReviewVerdict.REJECT
        assert opinion.confidence >= 0.9

    def test_reject_too_many_chillers(self):
        """Load 150RT but 3 chillers running should REJECT."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="start"),
            StrategyAction(seq=2, device="chiller_1", action="set_load", value=50.0),
            StrategyAction(seq=3, device="chiller_2", action="start"),
            StrategyAction(seq=4, device="chiller_2", action="set_load", value=50.0),
            StrategyAction(seq=5, device="chiller_3", action="start"),
            StrategyAction(seq=6, device="chiller_3", action="set_load", value=50.0),
        ]
        strategy = make_strategy(actions, current_load_rt=150.0)
        opinion = review_efficiency(strategy)
        assert opinion.verdict == ReviewVerdict.REJECT

    def test_conditional_low_cop_improvement(self):
        """COP improvement near 0 should be CONDITIONAL_APPROVAL."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_cop_improvement=0.0,
            expected_energy_saving_kwh_per_h=5.0,
            current_load_rt=200.0,
        )
        opinion = review_efficiency(strategy)
        assert opinion.verdict == ReviewVerdict.CONDITIONAL_APPROVAL

    def test_high_price_concern(self):
        """Electricity price > 1.5 should flag concern."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_energy_saving_kwh_per_h=10.0,
            electricity_price=1.8,
            current_load_rt=200.0,
        )
        opinion = review_efficiency(strategy)
        # High price should generate concerns
        assert len(opinion.concerns) > 0
        assert any("price" in c.lower() or "electricity" in c.lower() for c in opinion.concerns)

    def test_unbalanced_loads(self):
        """max/min ratio > 3 among running chillers should flag concern."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=100.0),
            StrategyAction(seq=2, device="chiller_2", action="set_load", value=400.0),
        ]
        strategy = make_strategy(
            actions,
            expected_energy_saving_kwh_per_h=20.0,
            current_load_rt=500.0,
        )
        solution = make_solution(
            chiller_loads={"chiller_1": 100.0, "chiller_2": 400.0},
        )
        opinion = review_efficiency(strategy, solution)
        # Load ratio 400/100 = 4 > 3, should have concern
        assert len(opinion.concerns) > 0
        assert any("balance" in c.lower() or "load" in c.lower() for c in opinion.concerns)

    def test_positive_savings_high_confidence(self):
        """Clear savings should APPROVE with high confidence."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=250.0),
        ]
        strategy = make_strategy(
            actions,
            expected_cop_improvement=0.08,
            expected_energy_saving_kwh_per_h=40.0,
            current_load_rt=250.0,
        )
        opinion = review_efficiency(strategy)
        assert opinion.verdict == ReviewVerdict.APPROVE
        assert opinion.confidence >= 0.85

    def test_long_transition_misses_price_window(self):
        """Transition > 900s should flag demand management concern."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        tp = make_transition_plan(duration_sec=1200.0)
        strategy = make_strategy(
            actions,
            transition_plan=tp,
            expected_energy_saving_kwh_per_h=10.0,
            current_load_rt=200.0,
        )
        opinion = review_efficiency(strategy)
        assert any(
            "transition" in c.lower() or "price" in c.lower() or "window" in c.lower() or "demand" in c.lower()
            for c in opinion.concerns
        )


class TestEfficiencyAdvocate:
    """Tests for the EfficiencyAdvocate agent class."""

    @pytest.mark.asyncio
    async def test_run_with_dict_input(self):
        """Agent run should accept dict input and return serialized opinion."""
        agent = EfficiencyAdvocate()
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_cop_improvement=0.10,
            expected_energy_saving_kwh_per_h=50.0,
            current_load_rt=200.0,
        )
        result = await agent.run({"strategy": strategy.model_dump()})
        assert "opinion" in result
        opinion = result["opinion"]
        assert opinion["advocate"] == "efficiency"
        assert opinion["verdict"] in ("approve", "conditional_approval", "reject", "abstain")
