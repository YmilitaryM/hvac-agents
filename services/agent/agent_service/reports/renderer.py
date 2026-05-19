"""Report renderer — outputs reports in multiple formats."""

import json
from .generator import DailyReport


def render_report_json(report: DailyReport) -> str:
    """Render a report as JSON string."""
    kpis_dict = {}
    if report.kpis:
        kpis_dict = {
            "average_cop": report.kpis.average_cop,
            "average_eer": report.kpis.average_eer,
            "total_power_consumption_kwh": report.kpis.total_power_consumption_kwh,
            "total_cooling_energy_kwh": report.kpis.total_cooling_energy_kwh,
            "total_carbon_emissions_kg": report.kpis.total_carbon_emissions_kg,
            "total_energy_cost": report.kpis.total_energy_cost,
            "total_carbon_cost": report.kpis.total_carbon_cost,
            "num_strategies_executed": report.kpis.num_strategies_executed,
            "num_strategies_aborted": report.kpis.num_strategies_aborted,
            "energy_star_rating": report.kpis.energy_star_rating,
            "average_cop_improvement": report.kpis.average_cop_improvement,
            "total_energy_saved_kwh": report.kpis.total_energy_saved_kwh,
            "total_carbon_saved_kg": report.kpis.total_carbon_saved_kg,
            "cop_vs_design": report.kpis.cop_vs_design,
        }

    output = {
        "report_type": "daily",
        "date": report.date,
        "summary": report.summary,
        "kpis": kpis_dict,
        "alerts": report.alerts_summary,
        "strategies_executed": report.strategies_executed,
        "top_concerns": report.top_concerns,
        "recommendations": report.recommendations,
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


def render_report_markdown(report: DailyReport) -> str:
    """Render a report as Markdown string."""
    lines = []
    lines.append("# HVAC Chiller Plant Daily Report")
    lines.append(f"**Date:** {report.date}")
    lines.append("")

    lines.append("## Summary")
    lines.append(report.summary)
    lines.append("")

    if report.kpis:
        lines.append("## KPIs")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Average COP | {report.kpis.average_cop:.2f} |")
        lines.append(f"| Average EER | {report.kpis.average_eer:.2f} |")
        lines.append(
            f"| Energy Star Rating | {report.kpis.energy_star_rating:.0f}/100 |"
        )
        lines.append(
            f"| COP vs Design | {report.kpis.cop_vs_design:.1%} |"
        )
        lines.append(
            f"| Total Power | {report.kpis.total_power_consumption_kwh:.0f} kWh |"
        )
        lines.append(
            f"| Total Cooling | {report.kpis.total_cooling_energy_kwh:.0f} kWh |"
        )
        lines.append(
            f"| Carbon Emissions | {report.kpis.total_carbon_emissions_kg:.0f} kgCO2 |"
        )
        lines.append(
            f"| Energy Cost | ${report.kpis.total_energy_cost:.2f} |"
        )
        lines.append(
            f"| Carbon Cost | ${report.kpis.total_carbon_cost:.2f} |"
        )
        lines.append(
            f"| Strategies Executed | {report.kpis.num_strategies_executed} |"
        )
        lines.append(
            f"| Strategies Aborted | {report.kpis.num_strategies_aborted} |"
        )
        lines.append(
            f"| Energy Saved | {report.kpis.total_energy_saved_kwh:.0f} kWh |"
        )
        lines.append(
            f"| Carbon Saved | {report.kpis.total_carbon_saved_kg:.0f} kgCO2 |"
        )
        lines.append("")

    if report.top_concerns:
        lines.append("## Top Concerns")
        for c in report.top_concerns:
            lines.append(f"- {c}")
        lines.append("")

    if report.alerts_summary:
        lines.append("## Alerts")
        for a in report.alerts_summary:
            lines.append(f"- {a}")
        lines.append("")

    if report.recommendations:
        lines.append("## Recommendations")
        for r in report.recommendations:
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines)


def render_report_csv(report: DailyReport) -> str:
    """Render key metrics as CSV string."""
    if not report.kpis:
        return (
            "date,cop,eer,energy_star,power_kwh,cooling_kwh,carbon_kg,"
            "energy_cost,carbon_cost\n"
            f"{report.date},0,0,0,0,0,0,0,0\n"
        )

    k = report.kpis
    return (
        "date,cop,eer,energy_star,power_kwh,cooling_kwh,carbon_kg,"
        "energy_cost,carbon_cost,"
        "strategies_executed,strategies_aborted,energy_saved,carbon_saved\n"
        f"{report.date},{k.average_cop:.2f},{k.average_eer:.2f},"
        f"{k.energy_star_rating:.0f},"
        f"{k.total_power_consumption_kwh:.0f},"
        f"{k.total_cooling_energy_kwh:.0f},"
        f"{k.total_carbon_emissions_kg:.0f},{k.total_energy_cost:.2f},"
        f"{k.total_carbon_cost:.2f},"
        f"{k.num_strategies_executed},{k.num_strategies_aborted},"
        f"{k.total_energy_saved_kwh:.0f},{k.total_carbon_saved_kg:.0f}\n"
    )
