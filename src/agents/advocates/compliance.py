"""Compliance Advocate — reviews strategies from a regulatory/compliance perspective.

Checks carbon accounting, carbon intensity, standards compliance, and documentation.
Produces an AdvocateOpinion with approve/reject/conditional verdict.
"""

from typing import Any, Dict, Optional

from src.agents.base import AgentContext, BaseAgent
from src.optimization.solver import OptimizationSolution
from src.schemas.review import AdvocateOpinion, ReviewVerdict
from src.schemas.strategy import Strategy


HIGH_CARBON_INTENSITY_THRESHOLD = 0.7
CRITICAL_CARBON_INTENSITY = 0.8
CARBON_COST_RATIO_THRESHOLD = 0.3
CARBON_LIMIT_KG_PER_H = 500.0
DEFAULT_CARBON_PRICE = 0.08


def _has_start_stop_actions(actions) -> bool:
    """Check if strategy has discrete start/stop actions."""
    return any(a.action in ("start", "stop") for a in actions)


def review_compliance(
    strategy: Strategy,
    solution: Optional[OptimizationSolution] = None,
) -> AdvocateOpinion:
    """Review a strategy from the compliance perspective.

    Checks:
    - Carbon accounting (carbon cost ratio)
    - Carbon intensity of grid power
    - Standards compliance (preconditions)
    - Expected carbon savings
    - Regulatory limits
    - Documentation / audit trail

    Args:
        strategy: The optimization strategy to review.
        solution: Optional optimization solution with cost data.

    Returns:
        AdvocateOpinion with verdict, concerns, and suggestions.
    """
    concerns: list[str] = []
    suggestions: list[str] = []
    hard_violations: list[str] = []

    carbon_intensity = strategy.carbon_intensity
    carbon_savings = strategy.expected_carbon_saving_kg_per_h
    preconditions = [p.lower() for p in strategy.preconditions]
    has_start_stop = _has_start_stop_actions(strategy.actions)

    # ---- Carbon savings check ----
    if carbon_savings is not None and carbon_savings < 0:
        hard_violations.append(
            f"Expected carbon savings is negative ({carbon_savings:.2f} kgCO2/h). "
            "This strategy would increase carbon emissions."
        )
        concerns.append(
            f"Strategy projects {carbon_savings:.2f} kgCO2/h carbon savings — "
            "it increases emissions compared to current operation."
        )

    # ---- Carbon accounting (requires solution) ----
    if solution is not None:
        energy_cost = solution.energy_cost
        carbon_cost = solution.carbon_cost

        # Check carbon cost ratio
        if energy_cost > 0 and carbon_cost > energy_cost * CARBON_COST_RATIO_THRESHOLD:
            ratio = carbon_cost / energy_cost
            concerns.append(
                f"Carbon cost ({carbon_cost:.2f}) is {ratio:.1%} of energy cost "
                f"({energy_cost:.2f}) — exceeding {CARBON_COST_RATIO_THRESHOLD:.0%} threshold. "
                "High carbon intensity of operations."
            )
            suggestions.append(
                "Consider shifting load to periods with lower grid carbon intensity, "
                "or prioritize high-efficiency chillers to reduce overall power draw."
            )

        # Check regulatory carbon limit
        total_carbon_kg_per_h = carbon_cost / DEFAULT_CARBON_PRICE
        if total_carbon_kg_per_h > CARBON_LIMIT_KG_PER_H:
            concerns.append(
                f"Total carbon emissions ({total_carbon_kg_per_h:.0f} kgCO2/h) "
                f"exceed the regulatory soft limit of {CARBON_LIMIT_KG_PER_H} kgCO2/h. "
                "May trigger compliance reporting requirements."
            )
            suggestions.append(
                "Reduce plant load or switch to lower-carbon chiller configurations "
                "to stay below the regulatory threshold."
            )

    # ---- Carbon intensity ----
    if carbon_intensity > CRITICAL_CARBON_INTENSITY:
        concerns.append(
            f"Grid carbon intensity is critically high ({carbon_intensity:.2f} kgCO2/kWh). "
            "Strategy should explicitly prioritize low-carbon options."
        )
        suggestions.append(
            "Consider load curtailment, demand response, or deferring non-essential "
            "cooling until grid carbon intensity decreases."
        )
    elif carbon_intensity > HIGH_CARBON_INTENSITY_THRESHOLD:
        concerns.append(
            f"Grid carbon intensity is elevated ({carbon_intensity:.2f} kgCO2/kWh). "
            "Carbon impact should be considered in optimization."
        )

    # ---- Standards compliance (preconditions) ----
    has_temperature_limit = any(
        "temperature" in p or "temp" in p for p in preconditions
    )
    if not has_temperature_limit:
        concerns.append(
            "Preconditions do not include temperature limit checks. "
            "Temperature constraints are critical for safe chiller operation "
            "and regulatory compliance."
        )
        suggestions.append(
            "Add temperature-related preconditions (e.g., CHW supply temp range, "
            "CW return temp limits, outdoor wet-bulb temp bounds)."
        )

    # ---- Documentation / audit trail ----
    if has_start_stop and not strategy.llm_reasoning:
        concerns.append(
            "Strategy includes start/stop actions but has no reasoning recorded "
            "(llm_reasoning is empty). Audit trail is incomplete for operational changes."
        )
        suggestions.append(
            "Add reasoning/justification for start/stop decisions to support "
            "compliance audits and operational reviews."
        )

    # ---- Carbon savings positive ----
    if carbon_savings is not None and carbon_savings > 0:
        # Positive carbon savings — good for compliance
        pass

    # ---- Decision logic ----
    if hard_violations:
        return AdvocateOpinion(
            advocate="compliance",
            verdict=ReviewVerdict.REJECT,
            concerns=concerns,
            suggestions=suggestions,
            confidence=0.90,
        )

    if concerns:
        # Count compliance gaps
        num_gaps = len(concerns)
        if num_gaps >= 2:
            confidence = 0.60
        else:
            confidence = 0.70
        return AdvocateOpinion(
            advocate="compliance",
            verdict=ReviewVerdict.CONDITIONAL_APPROVAL,
            concerns=concerns,
            suggestions=suggestions,
            confidence=confidence,
        )

    # Clean strategy — approve with high confidence
    confidence = 0.88
    if carbon_savings is not None and carbon_savings > 0:
        confidence = 0.92
    return AdvocateOpinion(
        advocate="compliance",
        verdict=ReviewVerdict.APPROVE,
        concerns=concerns,
        suggestions=suggestions,
        confidence=confidence,
    )


class ComplianceAdvocate(BaseAgent):
    """Compliance Advocate — reviews strategies for regulatory compliance.

    Checks carbon accounting, carbon intensity, standards compliance, and
    documentation. Core logic is in review_compliance() — pure Python, no LLM required.
    """

    def __init__(self, llm=None, context: Optional[AgentContext] = None):
        super().__init__(name="compliance", llm=llm, context=context)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Review a strategy and return a compliance opinion.

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

        opinion = review_compliance(strategy, solution)
        result: Dict[str, Any] = {"opinion": opinion.model_dump()}

        if self.llm is not None:
            try:
                narrative = await self._generate_compliance_narrative(opinion, strategy)
                result["llm_narrative"] = narrative
            except Exception:
                self.logger.debug("LLM compliance narrative failed", exc_info=True)

        return result

    async def _generate_compliance_narrative(
        self, opinion: AdvocateOpinion, strategy: Strategy
    ) -> str:
        concerns_text = "; ".join(opinion.concerns) if opinion.concerns else "无"
        prompt = (
            "你是一个碳排放合规专家。请用1-2句中文总结以下对控制策略的合规评审意见：\n\n"
            f"评审结论: {opinion.verdict.value}\n"
            f"置信度: {opinion.confidence:.0%}\n"
            f"关切问题: {concerns_text}\n"
            f"电网碳强度: {strategy.carbon_intensity:.2f} kgCO2/kWh\n"
            f"预计碳减排: {strategy.expected_carbon_saving_kg_per_h or 0:.1f} kgCO2/h\n"
            f"当前负荷: {strategy.current_load_rt:.0f} RT\n"
            "\n请简要总结合规评审的关键发现。"
        )
        response = await self.llm.ainvoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
