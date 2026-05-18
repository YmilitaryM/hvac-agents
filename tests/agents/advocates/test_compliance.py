"""Tests for the Compliance Advocate Agent."""

import pytest
from src.agents.advocates.compliance import review_compliance, ComplianceAdvocate
from src.optimization.solver import OptimizationSolution
from src.schemas.review import ReviewVerdict
from src.schemas.strategy import (
    Strategy,
    StrategyAction,
    TransitionPhase,
    TransitionPlan,
    TriggerType,
)


def make_transition_plan() -> TransitionPlan:
    """Helper to create a valid transition plan."""
    return TransitionPlan(
        total_duration_sec=600.0,
        phases=[
            TransitionPhase(
                seq=1,
                duration_sec=600.0,
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
    expected_carbon_saving_kg_per_h: float | None = None,
    carbon_intensity: float = 0.5,
    preconditions: list | None = None,
    llm_reasoning: str = "",
    **kwargs,
) -> Strategy:
    """Helper to create a Strategy with common defaults."""
    if transition_plan is None and trigger_type != TriggerType.FAULT and actions:
        transition_plan = make_transition_plan()

    return Strategy(
        strategy_id="test_strat_1",
        trigger_type=trigger_type,
        actions=actions,
        transition_plan=transition_plan,
        expected_carbon_saving_kg_per_h=expected_carbon_saving_kg_per_h,
        carbon_intensity=carbon_intensity,
        preconditions=preconditions or [],
        llm_reasoning=llm_reasoning,
        **kwargs,
    )


def make_solution(energy_cost: float = 100.0, carbon_cost: float = 20.0,
                  total_power_kw: float = 100.0) -> OptimizationSolution:
    """Helper to create an OptimizationSolution."""
    return OptimizationSolution(
        chiller_loads={"chiller_1": 300.0},
        total_power_kw=total_power_kw,
        total_objective=50.0,
        energy_cost=energy_cost,
        carbon_cost=carbon_cost,
        wear_cost=100.0,
    )


class TestReviewCompliance:
    """Tests for the review_compliance core function."""

    def test_approve_low_carbon(self):
        """Low carbon, positive carbon savings should APPROVE."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=10.0,
            carbon_intensity=0.3,
            preconditions=["Temperature within limits", "All pumps available"],
            current_load_rt=200.0,
        )
        solution = make_solution(energy_cost=100.0, carbon_cost=20.0)
        opinion = review_compliance(strategy, solution)
        assert opinion.verdict == ReviewVerdict.APPROVE

    def test_reject_negative_carbon_savings(self):
        """Negative expected_carbon_saving_kg_per_h should REJECT."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=-5.0,
            current_load_rt=200.0,
        )
        opinion = review_compliance(strategy)
        assert opinion.verdict == ReviewVerdict.REJECT

    def test_conditional_high_carbon_intensity(self):
        """Grid carbon > 0.8 should be CONDITIONAL_APPROVAL."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=5.0,
            carbon_intensity=0.85,
            current_load_rt=200.0,
        )
        opinion = review_compliance(strategy)
        assert opinion.verdict == ReviewVerdict.CONDITIONAL_APPROVAL
        assert any("carbon" in c.lower() for c in opinion.concerns)

    def test_conditional_missing_temp_preconditions(self):
        """Preconditions don't mention temperature should flag compliance gap."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=5.0,
            preconditions=["All pumps available"],  # no temperature mention
            current_load_rt=200.0,
        )
        opinion = review_compliance(strategy)
        assert opinion.verdict == ReviewVerdict.CONDITIONAL_APPROVAL
        assert any(
            "temperature" in c.lower() or "precondition" in c.lower()
            for c in opinion.concerns
        )

    def test_high_carbon_cost_ratio(self):
        """carbon_cost > 0.3 * energy_cost should flag concern."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=5.0,
            carbon_intensity=0.5,
            preconditions=["Temperature limits observed"],
            current_load_rt=200.0,
        )
        # carbon_cost=40, energy_cost=100 => ratio = 40/100 = 0.4 > 0.3
        solution = make_solution(energy_cost=100.0, carbon_cost=40.0)
        opinion = review_compliance(strategy, solution)
        assert any("carbon" in c.lower() for c in opinion.concerns)

    def test_missing_reasoning_for_complex_strategy(self):
        """Has start/stop but no llm_reasoning should be CONDITIONAL_APPROVAL."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="stop"),
            StrategyAction(seq=2, device="chiller_2", action="start"),
            StrategyAction(seq=3, device="chiller_2", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=5.0,
            preconditions=["Temperature limits observed"],
            llm_reasoning="",  # empty
            current_load_rt=200.0,
        )
        opinion = review_compliance(strategy)
        # Either CONDITIONAL_APPROVAL due to missing reasoning for complex strategy
        assert opinion.verdict == ReviewVerdict.CONDITIONAL_APPROVAL
        assert any(
            "reasoning" in c.lower() or "audit" in c.lower() or "document" in c.lower()
            for c in opinion.concerns
        )

    def test_empty_strategy_clean(self):
        """Minimal valid strategy should APPROVE."""
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=5.0,
            carbon_intensity=0.3,
            preconditions=["Temperature limits observed"],
            current_load_rt=200.0,
        )
        opinion = review_compliance(strategy)
        assert opinion.verdict == ReviewVerdict.APPROVE


class TestComplianceAdvocate:
    """Tests for the ComplianceAdvocate agent class."""

    @pytest.mark.asyncio
    async def test_run_with_dict_input(self):
        """Agent run should accept dict input and return serialized opinion."""
        agent = ComplianceAdvocate()
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=10.0,
            carbon_intensity=0.3,
            preconditions=["Temperature limits observed"],
            current_load_rt=200.0,
        )
        result = await agent.run({"strategy": strategy.model_dump()})
        assert "opinion" in result
        opinion = result["opinion"]
        assert opinion["advocate"] == "compliance"
        assert opinion["verdict"] in ("approve", "conditional_approval", "reject", "abstain")

    @pytest.mark.asyncio
    async def test_run_with_strategy_object(self):
        """Agent run should accept Strategy object directly."""
        agent = ComplianceAdvocate()
        actions = [
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=200.0),
        ]
        strategy = make_strategy(
            actions,
            expected_carbon_saving_kg_per_h=10.0,
            carbon_intensity=0.3,
            preconditions=["Temperature limits observed"],
            current_load_rt=200.0,
        )
        result = await agent.run({"strategy": strategy})
        assert "opinion" in result
        assert result["opinion"]["advocate"] == "compliance"
