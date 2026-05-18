"""Efficiency Advocate — reviews strategies from an energy efficiency perspective.

Checks COP improvement, load distribution, chiller count vs load,
electricity price response, and energy savings.
Produces an AdvocateOpinion with approve/reject/conditional verdict.
"""

from typing import Any, Dict, Optional

from src.agents.base import AgentContext, BaseAgent
from src.optimization.solver import OptimizationSolution
from src.schemas.review import AdvocateOpinion, ReviewVerdict
from src.schemas.strategy import Strategy


TYPICAL_CHILLER_CAPACITY_RT = 500.0
MIN_COP_IMPROVEMENT = 0.05
MIN_LOAD_FOR_MULTI_CHILLER = 200.0  # RT — below this, multiple chillers is wasteful
HIGH_ELECTRICITY_PRICE = 1.0
VERY_HIGH_ELECTRICITY_PRICE = 1.5
MAX_TRANSITION_DURATION_SEC = 900  # 15 minutes
MAX_LOAD_BALANCE_RATIO = 3.0


def _count_running_chillers_from_actions(actions) -> int:
    """Count chillers that are set to run (set_load with value > 0)."""
    running = set()
    for a in actions:
        if a.action == "set_load" and a.value is not None and a.value > 0:
            running.add(a.device)
        elif a.action == "start":
            running.add(a.device)
        elif a.action == "stop":
            running.discard(a.device)
    return len(running)


def _get_running_chiller_loads(actions) -> Dict[str, float]:
    """Extract device -> target load for chillers with set_load > 0."""
    loads: Dict[str, float] = {}
    for a in actions:
        if a.action == "set_load" and a.value is not None and a.value > 0:
            loads[a.device] = a.value
    return loads


def _has_load_reduction_actions(actions) -> bool:
    """Check if strategy attempts to reduce load (stop actions or lower setpoints)."""
    return any(
        a.action in ("stop",) for a in actions
    )


def _count_start_stop_actions(actions) -> int:
    """Count total start + stop actions."""
    return sum(1 for a in actions if a.action in ("start", "stop"))


def review_efficiency(
    strategy: Strategy,
    solution: Optional[OptimizationSolution] = None,
) -> AdvocateOpinion:
    """Review a strategy from the efficiency perspective.

    Checks:
    - COP improvement
    - Load distribution balance
    - Number of running chillers vs load
    - Electricity price response
    - Transition timing vs price windows
    - Energy savings

    Args:
        strategy: The optimization strategy to review.
        solution: Optional optimization solution with chiller loads.

    Returns:
        AdvocateOpinion with verdict, concerns, and suggestions.
    """
    concerns: list[str] = []
    suggestions: list[str] = []
    hard_violations: list[str] = []

    cop_improvement = strategy.expected_cop_improvement
    energy_savings = strategy.expected_energy_saving_kwh_per_h
    electricity_price = strategy.electricity_price
    total_load = strategy.current_load_rt

    # ---- Energy savings check (highest priority) ----
    if energy_savings is not None and energy_savings < 0:
        hard_violations.append(
            f"Expected energy savings is negative ({energy_savings:.2f} kWh/h). "
            "This strategy would increase energy consumption."
        )
        concerns.append(
            f"Strategy projects {energy_savings:.2f} kWh/h energy savings — "
            "it would worsen efficiency compared to current operation."
        )

    # ---- Number of running chillers vs load ----
    num_running_from_actions = _count_running_chillers_from_actions(strategy.actions)
    num_running_from_solution = 0
    if solution is not None:
        num_running_from_solution = sum(
            1 for v in solution.chiller_loads.values() if v > 0
        )

    # Use the larger count (actions may include starters that aren't yet at load)
    num_running = max(num_running_from_actions, num_running_from_solution)

    if total_load < MIN_LOAD_FOR_MULTI_CHILLER and num_running >= 3:
        hard_violations.append(
            f"Total load is only {total_load:.0f}RT but {num_running} chillers are "
            f"running. This is highly inefficient — the load could be served by 1 chiller."
        )
        concerns.append(
            f"{num_running} chillers running for only {total_load:.0f}RT total load. "
            "Each additional chiller adds fixed power overhead."
        )
        suggestions.append(
            f"Consolidate load onto fewer chillers. A single {TYPICAL_CHILLER_CAPACITY_RT}RT "
            f"chiller can easily handle {total_load:.0f}RT."
        )
    elif num_running >= 2 and total_load < TYPICAL_CHILLER_CAPACITY_RT:
        concerns.append(
            f"Total load {total_load:.0f}RT could potentially be served by a single "
            f"{TYPICAL_CHILLER_CAPACITY_RT}RT chiller rather than {num_running}."
        )
        suggestions.append(
            "Consider consolidating to one chiller to reduce fixed power overhead."
        )

    # ---- COP improvement ----
    if cop_improvement is not None:
        if cop_improvement <= 0:
            concerns.append(
                f"Expected COP improvement is {cop_improvement:.3f} — "
                "no efficiency gain over baseline."
            )
            suggestions.append(
                "Review chiller selection and load distribution to achieve positive COP improvement."
            )
        elif cop_improvement > MIN_COP_IMPROVEMENT:
            # Good COP improvement — positive signal
            pass
        else:
            concerns.append(
                f"COP improvement ({cop_improvement:.3f}) is marginal (< {MIN_COP_IMPROVEMENT})."
            )
            suggestions.append(
                "Explore alternative chiller combinations for better COP."
            )

    # ---- Load distribution balance ----
    if solution is not None:
        running_loads = {
            name: load
            for name, load in solution.chiller_loads.items()
            if load > 0
        }
        if len(running_loads) >= 2:
            max_load = max(running_loads.values())
            min_load = min(running_loads.values())
            if min_load > 0 and max_load / min_load > MAX_LOAD_BALANCE_RATIO:
                concerns.append(
                    f"Load distribution is unbalanced: max={max_load:.0f}RT, "
                    f"min={min_load:.0f}RT (ratio={max_load / min_load:.1f})."
                )
                suggestions.append(
                    "Redistribute loads for more even chiller utilization "
                    "to improve overall plant efficiency."
                )

    # ---- Electricity price response ----
    if electricity_price > VERY_HIGH_ELECTRICITY_PRICE:
        concerns.append(
            f"Electricity price is very high ({electricity_price:.2f} CNY/kWh). "
            "Strategy should prioritize load reduction or load shifting."
        )
        suggestions.append(
            "Consider demand response: reduce non-essential cooling, "
            "pre-cool during lower-price periods, or use thermal storage."
        )
    elif electricity_price > HIGH_ELECTRICITY_PRICE:
        concerns.append(
            f"Electricity price is elevated ({electricity_price:.2f} CNY/kWh). "
            "Verify strategy optimizes for current price conditions."
        )

    # ---- Demand management / transition timing ----
    if strategy.transition_plan is not None:
        total_duration = strategy.transition_plan.total_duration_sec
        if total_duration > MAX_TRANSITION_DURATION_SEC:
            concerns.append(
                f"Transition plan duration ({total_duration:.0f}s) exceeds "
                f"{MAX_TRANSITION_DURATION_SEC}s — may miss price windows "
                "or delay efficiency gains."
            )
            suggestions.append(
                "Shorten transition phases or consider parallel execution "
                "to capture price-sensitive windows."
            )

    # ---- Energy savings (positive) ----
    if energy_savings is not None and energy_savings > 0:
        # Positive savings is good — still include as context, not a concern
        pass

    # ---- Decision logic ----
    if hard_violations:
        return AdvocateOpinion(
            advocate="efficiency",
            verdict=ReviewVerdict.REJECT,
            concerns=concerns,
            suggestions=suggestions,
            confidence=0.92,
        )

    if concerns:
        # Conditional — some concerns but may still be worth running
        confidence = 0.65
        # Boost confidence if at least there are positive savings
        if energy_savings is not None and energy_savings > 0:
            confidence = 0.72
        if cop_improvement is not None and cop_improvement > MIN_COP_IMPROVEMENT:
            confidence = max(confidence, 0.70)
        return AdvocateOpinion(
            advocate="efficiency",
            verdict=ReviewVerdict.CONDITIONAL_APPROVAL,
            concerns=concerns,
            suggestions=suggestions,
            confidence=confidence,
        )

    # Clean strategy with positive savings — approve with high confidence
    confidence = 0.88
    if cop_improvement is not None and cop_improvement > MIN_COP_IMPROVEMENT:
        confidence = 0.92
    if energy_savings is not None and energy_savings > 20:
        confidence = 0.95
    return AdvocateOpinion(
        advocate="efficiency",
        verdict=ReviewVerdict.APPROVE,
        concerns=concerns,
        suggestions=suggestions,
        confidence=confidence,
    )


class EfficiencyAdvocate(BaseAgent):
    """Efficiency Advocate — reviews strategies for energy efficiency.

    Checks COP improvement, load distribution, chiller count, and energy savings.
    Core logic is in review_efficiency() — pure Python, no LLM required.
    """

    def __init__(self, llm=None, context: Optional[AgentContext] = None):
        super().__init__(name="efficiency", llm=llm, context=context)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Review a strategy and return an efficiency opinion.

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

        opinion = review_efficiency(strategy, solution)
        return {"opinion": opinion.model_dump()}
