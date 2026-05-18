import pytest
from src.schemas.strategy import (
    Strategy, StrategyAction, StrategyStatus,
    TransitionPlan, TransitionPhase, TriggerType,
)
from src.schemas.review import AdvocateOpinion, ReviewVerdict, ArbitrationResult


class TestStrategyAction:
    def test_discrete_action(self):
        a = StrategyAction(
            seq=1, device="chiller_2", action="stop"
        )
        assert a.is_discrete is True
        assert a.is_continuous is False

    def test_continuous_action(self):
        a = StrategyAction(
            seq=2, device="pump_3", action="set_frequency", value=35.0
        )
        assert a.is_continuous is True
        assert a.value == 35.0


class TestTransitionPlan:
    def test_minimal_transition(self):
        plan = TransitionPlan(
            total_duration_sec=300,
            phases=[
                TransitionPhase(
                    seq=1, duration_sec=120,
                    description="Ramp down chiller_2 to 30%",
                    actions=[
                        StrategyAction(seq=1, device="chiller_2",
                                       action="ramp_load", value=0.3, rate=0.0025)
                    ],
                ),
                TransitionPhase(
                    seq=2, duration_sec=180,
                    description="Stability check",
                    actions=[],
                    stability_check={"metric": "chw_supply_temp",
                                     "max_deviation": 0.3, "window_sec": 60},
                ),
            ],
            abort_conditions=["chw_supply_temp deviation > 1.5°C"],
        )
        assert plan.total_duration_sec == 300
        assert len(plan.phases) == 2


class TestStrategy:
    def test_strategy_lifecycle(self):
        s = Strategy(
            strategy_id="test_001",
            trigger_type=TriggerType.SCHEDULED,
            trigger_time=1716000000.0,
            current_load_rt=850,
            predicted_load_rt=520,
            actions=[
                StrategyAction(seq=1, device="chiller_2", action="stop"),
            ],
            transition_plan=TransitionPlan(
                total_duration_sec=120,
                phases=[
                    TransitionPhase(
                        seq=1, duration_sec=120,
                        description="Stop chiller_2",
                        actions=[
                            StrategyAction(seq=1, device="chiller_2", action="stop"),
                        ],
                    ),
                ],
                abort_conditions=[],
            ),
            preconditions=["total_load < 550RT"],
            expected_cop_improvement=0.12,
            expected_energy_saving_kwh_per_h=120,
        )
        assert s.status == StrategyStatus.DRAFT
        s.status = StrategyStatus.UNDER_REVIEW
        assert s.status == StrategyStatus.UNDER_REVIEW
        s.status = StrategyStatus.APPROVED
        assert s.is_approved
        s.status = StrategyStatus.REJECTED
        assert s.is_terminal

    def test_strategy_requires_transition_for_load_following(self):
        with pytest.raises(ValueError, match="transition_plan"):
            Strategy(
                strategy_id="test_002",
                trigger_type=TriggerType.LOAD_CHANGE,
                trigger_time=1716000000.0,
                current_load_rt=850,
                predicted_load_rt=520,
                actions=[
                    StrategyAction(seq=1, device="chiller_2", action="stop"),
                ],
            )


class TestAdvocateOpinion:
    def test_approval_opinion(self):
        op = AdvocateOpinion(
            advocate="reliability",
            verdict=ReviewVerdict.CONDITIONAL_APPROVAL,
            concerns=["需监控出水温度"],
            confidence=0.82,
        )
        assert op.is_positive
        assert not op.is_rejection

    def test_rejection_opinion(self):
        op = AdvocateOpinion(
            advocate="compliance",
            verdict=ReviewVerdict.REJECT,
            concerns=["碳排放超标", "不符合配额要求"],
            confidence=0.78,
        )
        assert op.is_rejection


class TestArbitrationResult:
    def test_unanimous_approval(self):
        opinions = [
            AdvocateOpinion(advocate="reliability", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.9),
            AdvocateOpinion(advocate="efficiency", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.85),
            AdvocateOpinion(advocate="compliance", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.88),
        ]
        result = ArbitrationResult.from_opinions(opinions)
        assert result.decision == "approved"
        assert result.has_conflict is False

    def test_conflicting_opinions(self):
        opinions = [
            AdvocateOpinion(advocate="reliability", verdict=ReviewVerdict.REJECT,
                           concerns=["安全风险"], confidence=0.9),
            AdvocateOpinion(advocate="efficiency", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.85),
            AdvocateOpinion(advocate="compliance", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.7),
        ]
        result = ArbitrationResult.from_opinions(opinions)
        assert result.has_conflict is True
        assert "reliability" in result.conflicting_parties
