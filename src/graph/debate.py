"""Debate orchestration subgraph for the HVAC multi-agent system.

Handles running debate rounds between conflicting advocates and re-arbitrating
after each round until consensus is reached or max rounds are exhausted.
"""

import logging
from typing import Any, Dict, List, Literal

from langgraph.graph import StateGraph, END

from src.agents.coordinator import run_debate_round, arbitrate
from src.schemas.review import AdvocateOpinion, ReviewVerdict
from src.schemas.strategy import Strategy
from src.schemas.state import InvestDebateState

logger = logging.getLogger(__name__)


def create_debate_subgraph():
    """Create a compiled StateGraph subgraph for multi-round advocate debate.

    The subgraph runs debate rounds between conflicting advocates. Each round:
      1. run_debate_round() — advocates exchange arguments and may concede
      2. arbitrate() — coordinator re-arbitrates based on updated opinions

    The subgraph terminates when consensus is reached or max rounds exhausted.
    """
    workflow = StateGraph(InvestDebateState)

    workflow.add_node("debate_round", _debate_round_node)
    workflow.add_node("re_arbitrate", _re_arbitrate_node)

    workflow.set_entry_point("debate_round")

    # After debate round, go to re-arbitration
    workflow.add_edge("debate_round", "re_arbitrate")

    # After re-arbitration, check if debate should continue
    workflow.add_conditional_edges(
        "re_arbitrate",
        _should_continue_debate,
        {
            "continue": "debate_round",
            "end": END,
        },
    )

    return workflow.compile()


def _should_continue_debate(
    state: InvestDebateState,
) -> Literal["continue", "end"]:
    """Check if another debate round is needed."""
    if state.get("consensus_reached", False):
        return "end"
    if state.get("current_round", 0) >= 3:  # max 3 rounds
        return "end"
    return "continue"


async def _debate_round_node(state: InvestDebateState) -> Dict[str, Any]:
    """Run one debate round."""
    opinions_data = state.get("opinions", [])
    opinions = [
        AdvocateOpinion(**o) if isinstance(o, dict) else o for o in opinions_data
    ]
    strategy_id = state.get("strategy_id", "")

    updated_opinions, updated_state = run_debate_round(
        opinions,
        {
            "strategy_id": strategy_id,
            "topic": state.get("topic", ""),
            "current_round": state.get("current_round", 0),
        },
        None,
    )

    return {
        "opinions": [o.model_dump() for o in updated_opinions],
        "current_round": updated_state.get("current_round", 0),
        "consensus_reached": updated_state.get("consensus_reached", False),
    }


async def _re_arbitrate_node(state: InvestDebateState) -> Dict[str, Any]:
    """Re-arbitrate after a debate round."""
    opinions_data = state.get("opinions", [])
    opinions = [
        AdvocateOpinion(**o) if isinstance(o, dict) else o for o in opinions_data
    ]

    arb = arbitrate(opinions, None)

    consensus = all(
        o.verdict in (ReviewVerdict.APPROVE, ReviewVerdict.CONDITIONAL_APPROVAL) for o in opinions
    ) or all(o.verdict == ReviewVerdict.REJECT for o in opinions)

    return {
        "consensus_reached": consensus,
        "final_verdict": arb.decision if consensus else "",
    }


async def run_debate(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run a debate round between conflicting advocates.

    Input state should have:
    - advocate_opinions: List of AdvocateOpinion dicts
    - debate_round: current round number
    - max_debate_rounds: max rounds
    - pending_strategy: the strategy being debated

    Returns updated state with:
    - advocate_opinions: updated after debate
    - debate_round: incremented
    """
    opinions_data: List[Dict] = state.get("advocate_opinions", [])
    opinions: List[AdvocateOpinion] = [
        AdvocateOpinion(**o) if isinstance(o, dict) else o for o in opinions_data
    ]

    strategy_data = state.get("pending_strategy", {})
    strategy: Strategy | None = (
        Strategy(**strategy_data) if isinstance(strategy_data, dict) else None
    )

    debate_state = InvestDebateState(
        strategy_id=strategy.strategy_id if strategy else "",
        topic=state.get("arbitration_result", {}).get("debate_topic", ""),
        current_round=state.get("debate_round", 0),
        opinions=[o.model_dump() for o in opinions],
        consensus_reached=False,
        final_verdict="",
    )

    updated_opinions, updated_debate = run_debate_round(
        opinions, debate_state, strategy
    )

    new_arb = arbitrate(updated_opinions, strategy)

    return {
        "advocate_opinions": [o.model_dump() for o in updated_opinions],
        "debate_round": updated_debate["current_round"],
        "arbitration_result": new_arb.model_dump(),
    }
