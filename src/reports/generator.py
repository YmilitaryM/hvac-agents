"""Report generator — produces daily and monthly reports."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .kpi_calculator import calculate_kpis, KPIResult


@dataclass
class DailyReport:
    """A daily operational report."""

    date: str = ""  # ISO date string
    kpis: Optional[KPIResult] = None
    summary: str = ""
    alerts_summary: List[str] = field(default_factory=list)
    strategies_executed: List[Dict[str, Any]] = field(default_factory=list)
    top_concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


def generate_daily_report(
    snapshots: List[Dict[str, Any]],
    memory_entries: List[Dict[str, Any]],
    date: str = "",
    electricity_price: float = 0.8,
    carbon_price: float = 0.08,
    design_cop: float = 6.0,
) -> DailyReport:
    """Generate a daily operational report.

    Args:
        snapshots: Plant snapshots for the day.
        memory_entries: Memory log entries for the day.
        date: ISO date string for the report.
        electricity_price: Electricity price per kWh.
        carbon_price: Carbon price per kgCO2.
        design_cop: Design COP for benchmarking.

    Returns:
        DailyReport with KPIs, summary, and recommendations.
    """
    kpis = calculate_kpis(
        snapshots=snapshots,
        memory_entries=memory_entries,
        electricity_price=electricity_price,
        carbon_price=carbon_price,
        design_cop=design_cop,
    )

    # Generate summary
    summary_parts = []
    if kpis.average_cop > 0:
        summary_parts.append(f"Average COP: {kpis.average_cop:.2f}")
    if kpis.average_cop_improvement != 0:
        direction = "improved" if kpis.average_cop_improvement > 0 else "decreased"
        summary_parts.append(
            f"COP {direction} by {abs(kpis.average_cop_improvement):.2%}"
        )
    summary_parts.append(
        f"Energy Star Rating: {kpis.energy_star_rating:.0f}/100"
    )
    summary_parts.append(
        f"Strategies: {kpis.num_strategies_executed} executed, "
        f"{kpis.num_strategies_aborted} aborted"
    )

    # Alerts summary — collect entries with issues
    alerts = []
    for entry in memory_entries:
        status = entry.get("execution_status", "")
        if status == "aborted":
            alerts.append(
                f"Strategy {entry.get('strategy_id', 'unknown')} aborted"
            )
        if not entry.get("safety_passed", True):
            alerts.append(
                f"Strategy {entry.get('strategy_id', 'unknown')} had safety issues"
            )

    # Strategies executed
    strategies = [
        {
            "strategy_id": e.get("strategy_id", ""),
            "trigger_type": e.get("trigger_type", ""),
            "cop_improvement": e.get("cop_improvement"),
            "energy_saving_kwh": e.get("energy_saving_kwh"),
            "execution_status": e.get("execution_status", ""),
        }
        for e in memory_entries
    ]

    # Recommendations based on KPIs
    recommendations = []
    if kpis.average_cop < 4.5:
        recommendations.append(
            "System COP below 4.5 — schedule maintenance check"
        )
    if kpis.num_strategies_aborted > kpis.num_strategies_executed * 0.3:
        recommendations.append(
            "High abort rate — review strategy parameters"
        )
    if kpis.energy_star_rating < 50:
        recommendations.append(
            "Energy Star rating below 50 — investigate chiller efficiency"
        )
    if kpis.average_cop_improvement < -0.05:
        recommendations.append(
            "COP declining — review optimization parameters"
        )
    if not recommendations:
        recommendations.append("System operating normally — no actions required")

    # Top concerns
    concerns = []
    benchmark = kpis.cop_vs_design
    if benchmark < 0.8:
        concerns.append(
            f"COP at {benchmark:.0%} of design — significant efficiency gap"
        )
    if kpis.total_carbon_emissions_kg > 1000:
        concerns.append(
            f"High carbon emissions: {kpis.total_carbon_emissions_kg:.0f} kgCO2"
        )

    return DailyReport(
        date=date,
        kpis=kpis,
        summary="; ".join(summary_parts),
        alerts_summary=alerts,
        strategies_executed=strategies,
        top_concerns=concerns,
        recommendations=recommendations,
    )
