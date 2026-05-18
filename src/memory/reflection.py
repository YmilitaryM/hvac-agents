"""Reflection -- analyzes past strategy executions to generate insights."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .log import MemoryLog, MemoryEntry


@dataclass
class ReflectionResult:
    """Result of reflecting on past strategy executions."""

    insights: List[str] = field(default_factory=list)
    patterns_identified: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    average_cop_improvement: float = 0.0
    success_rate: float = 0.0
    reflection_text: str = ""


def reflect_on_history(
    log: MemoryLog,
    lookback: int = 20,
    llm=None,  # optional LLM for richer reflection
) -> ReflectionResult:
    """Analyze recent strategy executions and generate insights.

    Pure Python analysis (no LLM required):
    - Calculate average COP improvement
    - Calculate success rate
    - Identify patterns: load ranges where strategies fail, advocate rejection patterns

    If LLM is provided, also generate natural language reflection.
    """
    recent = log.get_recent(lookback)
    if not recent:
        return ReflectionResult(insights=["No execution history available"])

    successful = log.get_successful()
    total = len(recent)
    success_count = len([e for e in recent if e in successful])
    success_rate = success_count / total if total > 0 else 0.0

    cop_improvements = [
        e.cop_improvement for e in recent if e.cop_improvement is not None
    ]
    avg_cop = sum(cop_improvements) / len(cop_improvements) if cop_improvements else 0.0

    insights: List[str] = []
    patterns: List[str] = []
    recommendations: List[str] = []

    # Pattern 1: COP trend
    if len(cop_improvements) >= 5:
        half = len(cop_improvements) // 2
        first_half = sum(cop_improvements[:half]) / half
        second_half = sum(cop_improvements[half:]) / (len(cop_improvements) - half)
        if second_half > first_half * 1.1:
            insights.append("COP improvement trend is positive")
        elif second_half < first_half * 0.9:
            insights.append("COP improvement trend is declining")
            recommendations.append(
                "Review recent strategy parameters for degradation"
            )

    # Pattern 2: Success rate
    insights.append(
        f"Success rate: {success_rate:.1%} over last {total} executions"
    )
    if success_rate < 0.8:
        patterns.append("High failure rate detected")
        recommendations.append("Investigate common failure causes")

    # Pattern 3: Load ranges at failure
    failed = [e for e in recent if e not in successful]
    if failed:
        failed_loads = [e.current_load_rt for e in failed]
        avg_failed_load = sum(failed_loads) / len(failed_loads)
        insights.append(
            f"Average load at failure: {avg_failed_load:.0f} RT"
        )

    # Pattern 4: Advocate rejection patterns
    rejection_reasons: Dict[str, int] = {}
    for e in recent:
        for op in e.advocate_opinions:
            if isinstance(op, dict) and op.get("verdict") == "reject":
                advocate = op.get("advocate", "unknown")
                rejection_reasons[advocate] = (
                    rejection_reasons.get(advocate, 0) + 1
                )
    if rejection_reasons:
        top_rejector = max(rejection_reasons, key=rejection_reasons.get)
        patterns.append(
            f"Most rejections from: {top_rejector} "
            f"({rejection_reasons[top_rejector]} times)"
        )

    # Average COP
    insights.append(f"Average COP improvement: {avg_cop:.4f}")

    return ReflectionResult(
        insights=insights,
        patterns_identified=patterns,
        recommendations=recommendations,
        average_cop_improvement=avg_cop,
        success_rate=success_rate,
    )
