"""Tests for the Coordinator Agent."""

import pytest
from unittest.mock import patch

from src.agents.coordinator import arbitrate, run_debate_round, CoordinatorAgent
from src.schemas.review import AdvocateOpinion, ReviewVerdict
from src.schemas.strategy import (
    Strategy,
    StrategyAction,
    TransitionPhase,
    TransitionPlan,
    TriggerType,
)


def make_opinion(advocate, verdict, confidence=0.8, concerns=None, suggestions=None):
    return AdvocateOpinion(
        advocate=advocate,
        verdict=verdict,
        confidence=confidence,
        concerns=concerns or [],
        suggestions=suggestions or [],
    )


def make_test_strategy():
    return Strategy(
        strategy_id="test-1",
        trigger_type=TriggerType.SCHEDULED,
        actions=[
            StrategyAction(seq=1, device="chiller_1", action="set_load", value=400.0)
        ],
        transition_plan=TransitionPlan(
            total_duration_sec=600,
            phases=[TransitionPhase(seq=1, duration_sec=600, description="Ramp")],
            abort_conditions=["Fault"],
        ),
    )


def make_debate_state(current_round=0):
    return {
        "strategy_id": "s1",
        "topic": "test debate",
        "current_round": current_round,
        "opinions": [],
        "consensus_reached": False,
        "final_verdict": "",
        "max_rounds": 2,
    }


class TestArbitrate:
    def test_unanimous_approval(self):
        opinions = [
            make_opinion("reliability", ReviewVerdict.APPROVE),
            make_opinion("efficiency", ReviewVerdict.APPROVE),
            make_opinion("compliance", ReviewVerdict.APPROVE),
        ]
        result = arbitrate(opinions)
        assert result.decision == "approved"
        assert result.has_conflict is False
        assert result.debate_needed is False

    def test_single_rejection_triggers_debate(self):
        opinions = [
            make_opinion("reliability", ReviewVerdict.REJECT, confidence=0.7),
            make_opinion("efficiency", ReviewVerdict.APPROVE),
            make_opinion("compliance", ReviewVerdict.APPROVE),
        ]
        result = arbitrate(opinions)
        assert result.decision == "under_debate"
        assert result.debate_needed is True
        assert result.has_conflict is True

    def test_double_rejection(self):
        opinions = [
            make_opinion("reliability", ReviewVerdict.REJECT),
            make_opinion("efficiency", ReviewVerdict.REJECT),
            make_opinion("compliance", ReviewVerdict.APPROVE),
        ]
        result = arbitrate(opinions)
        assert result.decision == "rejected"
        assert result.debate_needed is False

    def test_conditional_approval(self):
        opinions = [
            make_opinion("reliability", ReviewVerdict.APPROVE),
            make_opinion(
                "efficiency",
                ReviewVerdict.CONDITIONAL_APPROVAL,
                concerns=["High energy use"],
            ),
            make_opinion(
                "compliance",
                ReviewVerdict.CONDITIONAL_APPROVAL,
                concerns=["Missing report"],
            ),
        ]
        result = arbitrate(opinions)
        assert result.decision == "approved_with_conditions"
        assert len(result.conditions) == 2
        assert "High energy use" in result.conditions
        assert "Missing report" in result.conditions

    def test_weighted_voting_reliability_priority(self):
        opinions = [
            make_opinion(
                "reliability", ReviewVerdict.REJECT, concerns=["Surge risk"]
            ),
            make_opinion("efficiency", ReviewVerdict.APPROVE),
            make_opinion("compliance", ReviewVerdict.APPROVE),
        ]
        result = arbitrate(opinions)
        assert result.decision == "under_debate"
        assert result.debate_needed is True
        assert "reliability" in result.reasoning.lower()

    def test_abstain_ignored(self):
        opinions = [
            make_opinion("reliability", ReviewVerdict.ABSTAIN),
            make_opinion("efficiency", ReviewVerdict.APPROVE),
            make_opinion("compliance", ReviewVerdict.APPROVE),
        ]
        result = arbitrate(opinions)
        assert result.decision == "approved"
        assert result.has_conflict is False


class TestDebateRound:
    def test_debate_round_increments(self):
        opinions = [
            make_opinion("reliability", ReviewVerdict.REJECT, confidence=0.6),
            make_opinion("efficiency", ReviewVerdict.APPROVE),
            make_opinion("compliance", ReviewVerdict.APPROVE),
        ]
        debate_state = make_debate_state(current_round=0)
        strategy = make_test_strategy()
        new_opinions, new_state = run_debate_round(opinions, debate_state, strategy)
        assert new_state["current_round"] == 1

    def test_debate_max_rounds_finalizes(self):
        opinions = [
            make_opinion("reliability", ReviewVerdict.REJECT, confidence=0.6),
            make_opinion("efficiency", ReviewVerdict.APPROVE),
            make_opinion("compliance", ReviewVerdict.APPROVE),
        ]
        debate_state = make_debate_state(current_round=2)
        strategy = make_test_strategy()
        new_opinions, new_state = run_debate_round(opinions, debate_state, strategy)
        assert new_state["consensus_reached"] is True

    def test_debate_single_objector_may_concede(self):
        opinions = [
            make_opinion("reliability", ReviewVerdict.REJECT, confidence=0.3),
            make_opinion("efficiency", ReviewVerdict.APPROVE),
            make_opinion("compliance", ReviewVerdict.APPROVE),
        ]
        debate_state = make_debate_state(current_round=0)
        strategy = make_test_strategy()
        with patch("random.random", return_value=0.1):
            new_opinions, new_state = run_debate_round(opinions, debate_state, strategy)
        assert new_state["consensus_reached"] is True
        assert new_opinions[0].verdict == ReviewVerdict.CONDITIONAL_APPROVAL
        assert new_state["final_verdict"] == "conditional_approval"


class TestCoordinatorAgent:
    async def test_coordinator_agent_run(self):
        opinions_data = [
            {
                "advocate": "reliability",
                "verdict": "approve",
                "confidence": 0.9,
                "concerns": [],
                "suggestions": [],
            },
            {
                "advocate": "efficiency",
                "verdict": "approve",
                "confidence": 0.85,
                "concerns": [],
                "suggestions": [],
            },
            {
                "advocate": "compliance",
                "verdict": "approve",
                "confidence": 0.95,
                "concerns": [],
                "suggestions": [],
            },
        ]
        agent = CoordinatorAgent()
        result = await agent.run(
            {
                "advocate_opinions": opinions_data,
                "pending_strategy": make_test_strategy(),
            }
        )
        assert "arbitration_result" in result
        assert result["arbitration_result"]["decision"] == "approved"
