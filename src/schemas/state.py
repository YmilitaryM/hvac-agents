"""Agent state schemas for LangGraph-based multi-agent orchestration.

AgentState extends LangGraph's MessagesState pattern and serves as the
shared state flowing through all agents in the HVAC chiller plant system.
InvestDebateState and RiskDebateState are TypedDicts for debate sub-graphs.
"""

from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState

# Default values for AgentState fields (excluding 'messages' which is
# provided by MessagesState).
_AGENT_STATE_DEFAULTS: Dict[str, Any] = {
    "current_time": 0.0,
    "trigger_type": "",
    "debug": False,
    "plant_snapshot": None,
    "predicted_load_rt": None,
    "load_forecast_15min": None,
    "load_forecast_1h": None,
    "load_forecast_6h": None,
    "weather_data": {},
    "current_strategy": None,
    "pending_strategy": None,
    "strategy_history": [],
    "advocate_opinions": [],
    "arbitration_result": None,
    "debate_round": 0,
    "max_debate_rounds": 2,
    "execution_status": "idle",
    "active_transition": None,
    "alerts": [],
    "health_scores": {},
    "anomaly_detected": False,
    "anomaly_details": "",
    "report_requested": False,
    "report_period": "",
    "needs_new_strategy": False,
    "parameter_adjustments": [],
    "reoptimization_count": 0,
    "rl_override": None,
    "rag_context": [],
}


class AgentState(dict):
    """Main shared state flowing through all agents in the LangGraph.

    Extends MessagesState which provides the 'messages' list semantics.
    Implemented as a dict subclass with TypedDict-compatible metadata so
    LangGraph can introspect the state schema. All fields have sensible
    defaults so callers only need to supply 'messages'.
    """

    # TypedDict compatibility — LangGraph uses these to detect TypedDict-like
    # schemas and set up channels.
    __required_keys__: frozenset[str] = frozenset(
        {"messages"}
        | set(_AGENT_STATE_DEFAULTS.keys())
    )
    __optional_keys__: frozenset[str] = frozenset()
    __total__: bool = True

    # Class-level annotations so LangGraph's get_type_hints() can extract
    # channel definitions (including the add_messages reducer).
    messages: Annotated[list, add_messages]
    current_time: float
    trigger_type: str
    debug: bool
    plant_snapshot: Optional[Dict]
    predicted_load_rt: Optional[float]
    load_forecast_15min: Optional[float]
    load_forecast_1h: Optional[float]
    load_forecast_6h: Optional[float]
    weather_data: Dict
    current_strategy: Optional[Dict]
    pending_strategy: Optional[Dict]
    strategy_history: List[Dict]
    advocate_opinions: List[Dict]
    arbitration_result: Optional[Dict]
    debate_round: int
    max_debate_rounds: int
    execution_status: str
    active_transition: Optional[Dict]
    alerts: List[Dict]
    health_scores: Dict[str, float]
    anomaly_detected: bool
    anomaly_details: str
    report_requested: bool
    report_period: str
    needs_new_strategy: bool
    parameter_adjustments: List[Dict]
    reoptimization_count: int
    rl_override: Optional[Dict]
    rag_context: List[str]

    def __init__(self, **kwargs: Any) -> None:
        """Create a new AgentState, filling in defaults for any missing keys."""
        full_kwargs: Dict[str, Any] = dict(_AGENT_STATE_DEFAULTS)
        full_kwargs.update(kwargs)
        super().__init__(**full_kwargs)


class InvestDebateState(TypedDict):
    """State for investment/optimization debate between advocates.

    Used when Reliability vs Efficiency vs Compliance advocates
    debate a proposed strategy.
    """

    strategy_id: str
    topic: str
    current_round: int
    opinions: List[Dict]  # List of AdvocateOpinion serialized
    consensus_reached: bool
    final_verdict: str  # ReviewVerdict value


class RiskDebateState(TypedDict):
    """State for risk/safety debate.

    Used when a safety concern is raised during strategy review.
    """

    risk_type: str  # surge, overload, maintenance, compliance
    severity: str  # low, medium, high, critical
    source_advocate: str
    affected_devices: List[str]
    resolution: str  # resolved, escalated, mitigated
    resolution_notes: str
