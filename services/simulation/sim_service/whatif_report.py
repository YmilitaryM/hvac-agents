"""Generate comparison reports for what-if scenarios."""
import numpy as np


def generate_comparison_report(scenario_results: list[dict]) -> dict:
    """Compare multiple simulation scenarios.

    Args:
        scenario_results: [{name, snapshots: [{total_power_kw, system_cop, total_cooling_load_rt, ...}]}]

    Returns: comparison report with rankings
    """
    if not scenario_results:
        return {"error": "No scenario results"}

    summaries = []
    for scenario in scenario_results:
        snaps = scenario.get("snapshots", [])
        if not snaps:
            summaries.append({"name": scenario["name"], "error": "No data"})
            continue

        total_power = sum(s.get("total_power_kw", 0) for s in snaps)
        total_cooling = sum(s.get("total_cooling_load_rt", 0) * 3.517 for s in snaps)  # RT->kW
        cops = [s.get("system_cop", 0) for s in snaps if s.get("system_cop", 0) > 0]

        cop_array = np.array(cops) if cops else np.array([0])

        summaries.append({
            "name": scenario["name"],
            "annual_energy_kwh": round(total_power, 0),
            "annual_cooling_kwh": round(total_cooling, 0),
            "avg_cop": round(float(np.mean(cop_array)), 2),
            "cop_p25": round(float(np.percentile(cop_array, 25)), 2),
            "cop_p50": round(float(np.percentile(cop_array, 50)), 2),
            "cop_p75": round(float(np.percentile(cop_array, 75)), 2),
            "cop_min": round(float(np.min(cop_array)), 2),
            "cop_max": round(float(np.max(cop_array)), 2),
            "hours_with_data": len(snaps),
        })

    # Rank by avg COP
    summaries.sort(key=lambda x: x.get("avg_cop", 0), reverse=True)
    for i, s in enumerate(summaries):
        s["rank"] = i + 1

    best = summaries[0] if summaries else None

    return {
        "scenarios": summaries,
        "best_scenario": best,
        "comparison": _build_comparison_table(summaries),
        "recommendation": (
            f"Best scenario: {best['name']} (avg COP: {best.get('avg_cop', 'N/A')})"
            if best
            else "N/A"
        ),
    }


def _build_comparison_table(summaries: list[dict]) -> list[dict]:
    """Build a side-by-side comparison table."""
    if len(summaries) < 2:
        return []

    baseline = next((s for s in summaries if s["name"].lower() == "baseline"), summaries[0])
    table = []
    for s in summaries:
        energy_saving = baseline.get("annual_energy_kwh", 1) - s.get("annual_energy_kwh", 0)
        cop_improvement = s.get("avg_cop", 0) - baseline.get("avg_cop", 0)
        table.append({
            "name": s["name"],
            "rank": s["rank"],
            "annual_energy_kwh": s["annual_energy_kwh"],
            "avg_cop": s["avg_cop"],
            "energy_saving_vs_baseline_kwh": round(energy_saving, 0),
            "energy_saving_pct": round(
                energy_saving / max(baseline.get("annual_energy_kwh", 1), 1) * 100, 1
            ),
            "cop_improvement": round(cop_improvement, 2),
        })
    return table
