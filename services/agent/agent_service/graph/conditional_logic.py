"""Conditional routing functions for LangGraph's add_conditional_edges.

Each function receives the full AgentState and returns a string literal that
determines the next node to route to.
"""

from typing import Literal

from .schemas.state import AgentState


def should_continue_after_monitor(state: AgentState) -> Literal["predict", "end"]:
    """If anomaly is critical, skip to end. Otherwise continue to predict."""
    if state.get("anomaly_detected") and state.get("execution_status") == "fault":
        return "end"
    return "predict"


def should_generate_strategy(state: AgentState) -> Literal["strategy", "end"]:
    """If predicted load ~ current load (within 5%) and no trigger, skip strategy."""
    predicted = state.get("predicted_load_rt", 0) or 0
    current_strategy = state.get("current_strategy") or {}
    current_load = (
        current_strategy.get("current_load_rt", 0)
        if isinstance(current_strategy, dict)
        else 0
    )
    if current_load > 0 and abs(predicted - current_load) / current_load < 0.05:
        if state.get("trigger_type") not in ("fault", "manual"):
            return "end"
    return "strategy"


def should_enter_debate(state: AgentState) -> Literal["debate", "safety"]:
    """Check if arbitration result requires debate."""
    arb = state.get("arbitration_result") or {}
    if isinstance(arb, dict) and arb.get("debate_needed"):
        return "debate"
    return "safety"


def should_execute(state: AgentState) -> Literal["execute", "end"]:
    """Check if safety passed and strategy is approved."""
    arb = state.get("arbitration_result") or {}
    safety_result = state.get("safety_result") or {}
    if isinstance(arb, dict):
        decision = arb.get("decision", "")
        if decision == "rejected":
            return "end"
    if isinstance(safety_result, dict):
        if safety_result.get("blocking"):
            return "end"
    return "execute"


def after_execute(state: AgentState) -> Literal["reflect", "end"]:
    """After execution, reflect or end."""
    return "end"
