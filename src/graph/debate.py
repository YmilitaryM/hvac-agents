"""Debate orchestration subgraph for the HVAC multi-agent system.

Handles running debate rounds between conflicting advocates and re-arbitrating
after each round until consensus is reached or max rounds are exhausted.
"""

from typing import Any, Dict, List

from src.agents.coordinator import run_debate_round, arbitrate
from src.schemas.review import AdvocateOpinion
from src.schemas.strategy import Strategy
from src.schemas.state import InvestDebateState


def create_debate_subgraph():
    """Create a subgraph for advocate debate.

    This is a simple subgraph that runs debate rounds between conflicting advocates.
    It will be used as a node in the main graph.
    """
    # For now, return a simple async function that simulates debate
    pass


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
