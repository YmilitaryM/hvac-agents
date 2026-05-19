"""Reliability Advocate — reviews strategies from an equipment safety perspective.

Checks safety margins, surge risk, equipment health, and transition safety.
Produces an AdvocateOpinion with approve/reject/conditional verdict.
"""

from typing import Any, Dict, Optional

from src.agents.base import AgentContext, BaseAgent
from src.optimization.solver import OptimizationSolution
from src.schemas.review import AdvocateOpinion, ReviewVerdict
from src.schemas.strategy import Strategy


TYPICAL_CHILLER_CAPACITY_RT = 500.0
SURGE_RISK_THRESHOLD_RT = 150.0   # 30% of 500RT
SURGE_REJECT_THRESHOLD_RT = 100.0  # 20% of 500RT
MAX_START_ACTIONS = 2


def _count_start_actions(actions) -> int:
    """Count the number of 'start' actions in a strategy."""
    return sum(1 for a in actions if a.action == "start")


def _count_stop_actions(actions) -> int:
    """Count the number of 'stop' actions in a strategy."""
    return sum(1 for a in actions if a.action == "stop")


def _has_start_stop_actions(actions) -> bool:
    """Check if the strategy has any start or stop (discrete) actions."""
    return any(a.action in ("start", "stop") for a in actions)


def _get_running_chiller_loads(actions) -> Dict[str, float]:
    """Extract a dict of device -> target load for chillers that end up running.

    A chiller is running if it has a set_load action with a positive value.
    If a chiller has both a stop action and later a start+set_load, it's
    still running (but flagged as a start/stop concern separately).
    """
    loads: Dict[str, float] = {}
    for a in actions:
        if a.action == "set_load" and a.value is not None and a.value > 0:
            loads[a.device] = a.value
    return loads


def _get_started_and_stopped_devices(actions) -> tuple:
    """Return sets of devices that are started and stopped in the strategy."""
    started = {a.device for a in actions if a.action == "start"}
    stopped = {a.device for a in actions if a.action == "stop"}
    return started, stopped


def review_reliability(
    strategy: Strategy,
    solution: Optional[OptimizationSolution] = None,
) -> AdvocateOpinion:
    """Review a strategy from the reliability perspective.

    Checks:
    - Safety margins (capacity headroom)
    - Equipment health (excessive starts/stops)
    - Surge risk (low load operation)
    - Transition safety (abort conditions, plan existence)
    - Risk mitigations

    Args:
        strategy: The optimization strategy to review.
        solution: Optional optimization solution with chiller loads.

    Returns:
        AdvocateOpinion with verdict, concerns, and suggestions.
    """
    concerns: list[str] = []
    suggestions: list[str] = []
    hard_violations: list[str] = []

    actions = strategy.actions
    running_loads = _get_running_chiller_loads(actions)
    num_running = len(running_loads)
    total_running_capacity = num_running * TYPICAL_CHILLER_CAPACITY_RT
    total_load = strategy.current_load_rt

    num_starts = _count_start_actions(actions)
    num_stops = _count_stop_actions(actions)
    has_discrete = _has_start_stop_actions(actions)
    started_devices, stopped_devices = _get_started_and_stopped_devices(actions)

    # ---- Safety margins (capacity headroom) ----
    if total_running_capacity > 0 and total_running_capacity < total_load * 1.1:
        concerns.append(
            f"Tight capacity margin: {total_running_capacity:.0f}RT running capacity "
            f"vs {total_load:.0f}RT load (headroom < 10%)"
        )
        suggestions.append(
            "Consider running an additional chiller to improve safety margin"
        )

    # ---- Excessive starts/stops ----
    if num_starts > MAX_START_ACTIONS:
        concerns.append(
            f"Excessive chiller starts: {num_starts} start actions in one strategy. "
            "Frequent starts increase wear and reduce equipment life."
        )
        suggestions.append(
            "Reduce the number of simultaneous chiller starts; "
            "stagger startups to limit inrush current and mechanical stress."
        )

    # ---- Surge risk ----
    for device, load_rt in sorted(running_loads.items()):
        if load_rt < SURGE_REJECT_THRESHOLD_RT:
            hard_violations.append(
                f"Chiller {device} load={load_rt:.1f}RT is below 20% of nominal capacity "
                f"({TYPICAL_CHILLER_CAPACITY_RT}RT) — high surge risk, must reject."
            )
            concerns.append(
                f"Chiller {device} operating at {load_rt:.1f}RT — severe surge risk "
                f"(<{SURGE_REJECT_THRESHOLD_RT}RT)"
            )
        elif load_rt < SURGE_RISK_THRESHOLD_RT:
            concerns.append(
                f"Chiller {device} load={load_rt:.1f}RT is below 30% of nominal capacity "
                f"({TYPICAL_CHILLER_CAPACITY_RT}RT) — elevated surge risk."
            )
            suggestions.append(
                f"Increase chiller {device} load above {SURGE_RISK_THRESHOLD_RT}RT "
                "or redistribute load to fewer chillers."
            )

    # ---- Start/stop frequency (same chiller stopped and started) ----
    churn_devices = started_devices & stopped_devices
    if churn_devices:
        devices_str = ", ".join(sorted(churn_devices))
        concerns.append(
            f"Chiller(s) {devices_str} are both stopped and started in the same strategy. "
            "Unnecessary cycling causes thermal stress and wear."
        )
        suggestions.append(
            f"Avoid stopping and immediately restarting {devices_str}; "
            "consider keeping them running at minimum load instead."
        )

    # ---- Transition safety ----
    if has_discrete and strategy.transition_plan is None:
        hard_violations.append(
            "Strategy has start/stop actions but no transition plan — "
            "unsafe to execute without controlled sequencing."
        )
        concerns.append(
            "Missing transition plan for start/stop operations. "
            "Without a plan, equipment may be damaged during abrupt changes."
        )
        suggestions.append(
            "Add a TransitionPlan with phased ramp-up/down, "
            "stability checks, and abort conditions."
        )
    elif strategy.transition_plan is not None:
        if not strategy.transition_plan.abort_conditions:
            concerns.append(
                "Transition plan exists but has no abort conditions. "
                "If equipment malfunctions during transition, there is no automatic halt."
            )
            suggestions.append(
                "Add abort conditions to the transition plan (e.g., FAULT state, "
                "COP drop, temperature excursion limits)."
            )
        if len(strategy.transition_plan.phases) == 0:
            concerns.append("Transition plan has no phases defined.")

    # ---- Risk mitigations ----
    if strategy.risk_mitigations:
        # Mitigations are positive — reduce concern severity
        pass  # considered in decision logic below

    # ---- Decision logic ----
    if hard_violations:
        return AdvocateOpinion(
            advocate="reliability",
            verdict=ReviewVerdict.REJECT,
            concerns=concerns,
            suggestions=suggestions,
            confidence=0.90,
        )

    if concerns:
        # Conditional approval with moderate-high confidence
        mitigation_bonus = 0.05 if strategy.risk_mitigations else 0.0
        return AdvocateOpinion(
            advocate="reliability",
            verdict=ReviewVerdict.CONDITIONAL_APPROVAL,
            concerns=concerns,
            suggestions=suggestions,
            confidence=min(0.60 + mitigation_bonus, 0.78),
        )

    # Clean strategy — approve with high confidence
    mitigation_bonus = 0.03 if strategy.risk_mitigations else 0.0
    return AdvocateOpinion(
        advocate="reliability",
        verdict=ReviewVerdict.APPROVE,
        concerns=concerns,
        suggestions=suggestions,
        confidence=min(0.85 + mitigation_bonus, 0.95),
    )


class ReliabilityAdvocate(BaseAgent):
    """Reliability Advocate — reviews strategies for equipment safety.

    Checks safety margins, surge risk, equipment wear, and transition safety.
    Core logic is in review_reliability() — pure Python, no LLM required.
    """

    def __init__(self, llm=None, context: Optional[AgentContext] = None):
        super().__init__(name="reliability", llm=llm, context=context)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Review a strategy and return a reliability opinion.

        Args:
            input_data: dict with "strategy" (Strategy object or dict)
                        and optional "solution" (OptimizationSolution or dict).

        Returns:
            dict with "opinion" key containing the serialized AdvocateOpinion.
        """
        strategy_data = input_data.get("strategy", {})
        if isinstance(strategy_data, dict):
            strategy = Strategy(**strategy_data)
        else:
            strategy = strategy_data

        solution = input_data.get("solution")

        opinion = review_reliability(strategy, solution)
        result: Dict[str, Any] = {"opinion": opinion.model_dump()}

        if self.llm is not None:
            try:
                narrative = await self._generate_reliability_narrative(opinion, strategy)
                result["llm_narrative"] = narrative
            except Exception:
                self.logger.debug("LLM reliability narrative failed", exc_info=True)

        return result

    async def _generate_reliability_narrative(
        self, opinion: AdvocateOpinion, strategy: Strategy
    ) -> str:
        concerns_text = "; ".join(opinion.concerns) if opinion.concerns else "无"
        suggestions_text = "; ".join(opinion.suggestions) if opinion.suggestions else "无"
        prompt = (
            "你是一个冷水机组可靠性工程师。请用1-2句中文总结以下对控制策略的可靠性评审意见：\n\n"
            f"评审结论: {opinion.verdict.value}\n"
            f"置信度: {opinion.confidence:.0%}\n"
            f"关切问题: {concerns_text}\n"
            f"改进建议: {suggestions_text}\n"
            f"当前负荷: {strategy.current_load_rt:.0f} RT\n"
            f"动作数量: {len(strategy.actions)}\n"
            "\n请简要总结可靠性评审的关键发现。"
        )
        response = await self.llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
