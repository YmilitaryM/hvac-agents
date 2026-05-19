"""Report Agent — generates daily and monthly operational reports.

Read-only consumer — does not participate in the control decision loop.
"""

from typing import Any, Dict, List, Optional
from .agents.base import BaseAgent
from .reports.generator import generate_daily_report, DailyReport
from .reports.renderer import (
    render_report_json,
    render_report_markdown,
    render_report_csv,
)


class ReportAgent(BaseAgent):
    """Report Agent — generates reports from snapshots and memory entries.

    Input keys:
        snapshots: List of plant snapshot dicts.
        memory_entries: List of MemoryEntry dicts.
        date: ISO date string.
        report_period: "daily" or "monthly" (default: "daily").
        format: "json", "markdown", or "csv" (default: "json").
        electricity_price: Price per kWh (default: 0.8).
        carbon_price: Carbon price per kgCO2 (default: 0.08).
        design_cop: Design COP for benchmarking (default: 6.0).

    Output keys:
        report: Serialized report dict (DailyReport as dict).
        rendered: Rendered report string in requested format.
        format: Output format used.
    """

    def __init__(self, llm=None, context=None):
        super().__init__(name="report", llm=llm, context=context)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        snapshots = input_data.get("snapshots", [])
        memory_entries = input_data.get("memory_entries", [])
        date = input_data.get("date", "")
        report_period = input_data.get("report_period", "daily")
        output_format = input_data.get("format", "json")
        electricity_price = float(input_data.get("electricity_price", 0.8))
        carbon_price = float(input_data.get("carbon_price", 0.08))
        design_cop = float(input_data.get("design_cop", 6.0))

        if report_period == "daily":
            report = generate_daily_report(
                snapshots=snapshots,
                memory_entries=memory_entries,
                date=date,
                electricity_price=electricity_price,
                carbon_price=carbon_price,
                design_cop=design_cop,
            )
        else:
            # Monthly uses the same logic for now
            report = generate_daily_report(
                snapshots=snapshots,
                memory_entries=memory_entries,
                date=date,
                electricity_price=electricity_price,
                carbon_price=carbon_price,
                design_cop=design_cop,
            )

        # Render in requested format
        if output_format == "markdown":
            rendered = render_report_markdown(report)
        elif output_format == "csv":
            rendered = render_report_csv(report)
        else:
            rendered = render_report_json(report)

        return {
            "report": {
                "date": report.date,
                "summary": report.summary,
                "alerts_summary": report.alerts_summary,
                "strategies_executed": report.strategies_executed,
                "top_concerns": report.top_concerns,
                "recommendations": report.recommendations,
                "kpis": {
                    "average_cop": (
                        report.kpis.average_cop if report.kpis else 0.0
                    ),
                    "average_eer": (
                        report.kpis.average_eer if report.kpis else 0.0
                    ),
                    "energy_star_rating": (
                        report.kpis.energy_star_rating if report.kpis else 0.0
                    ),
                    "total_power_consumption_kwh": (
                        report.kpis.total_power_consumption_kwh
                        if report.kpis
                        else 0.0
                    ),
                    "total_carbon_emissions_kg": (
                        report.kpis.total_carbon_emissions_kg
                        if report.kpis
                        else 0.0
                    ),
                    "total_energy_cost": (
                        report.kpis.total_energy_cost if report.kpis else 0.0
                    ),
                    "num_strategies_executed": (
                        report.kpis.num_strategies_executed
                        if report.kpis
                        else 0
                    ),
                    "num_strategies_aborted": (
                        report.kpis.num_strategies_aborted
                        if report.kpis
                        else 0
                    ),
                },
            },
            "rendered": rendered,
            "format": output_format,
        }
