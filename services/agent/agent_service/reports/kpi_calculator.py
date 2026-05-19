"""KPI Calculator for HVAC chiller plant performance metrics."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Conversion constants
KW_PER_RT = 3.517  # kW of cooling per Refrigeration Ton
KG_CO2_PER_KWH_DEFAULT = 0.5  # default grid carbon intensity


@dataclass
class KPIResult:
    """Standard KPI metrics for a time period."""

    period_start: float = 0.0
    period_end: float = 0.0

    # Energy
    total_cooling_energy_kwh: float = 0.0  # total cooling output in kWh thermal
    total_power_consumption_kwh: float = 0.0  # total electricity consumed
    average_cop: float = 0.0  # average Coefficient of Performance
    average_eer: float = 0.0  # average Energy Efficiency Ratio (BTU/Wh)

    # Carbon
    total_carbon_emissions_kg: float = 0.0  # total CO2 emissions
    carbon_intensity_kg_per_kwh: float = 0.0  # kgCO2 per kWh cooling

    # Cost
    total_energy_cost: float = 0.0
    total_carbon_cost: float = 0.0

    # Operations
    num_strategies_executed: int = 0
    num_strategies_aborted: int = 0
    average_cop_improvement: float = 0.0
    total_energy_saved_kwh: float = 0.0
    total_carbon_saved_kg: float = 0.0
    total_cost_saved: float = 0.0

    # Benchmarking
    cop_vs_design: float = 0.0  # actual COP / design COP
    energy_star_rating: float = 0.0  # simplified 0-100 rating


def compute_cop(cooling_load_rt: float, power_kw: float) -> float:
    """COP = cooling output (kW) / power input (kW)."""
    if power_kw <= 0:
        return 0.0
    return (cooling_load_rt * KW_PER_RT) / power_kw


def compute_eer(cooling_load_rt: float, power_kw: float) -> float:
    """EER = cooling output (BTU/h) / power input (W).
    1 RT = 12000 BTU/h, so EER = COP * 3.412 (since 1 W = 3.412 BTU/h)."""
    cop = compute_cop(cooling_load_rt, power_kw)
    return cop * 3.412


def compute_carbon_intensity(
    total_power_kwh: float, total_carbon_kg: float
) -> float:
    """Carbon intensity = kgCO2 per kWh of cooling output."""
    if total_power_kwh <= 0:
        return 0.0
    return total_carbon_kg / total_power_kwh


def benchmark_against_standard(
    actual_cop: float,
    design_cop: float = 6.0,
    ashrae_minimum_cop: float = 5.0,
) -> Dict[str, Any]:
    """Compare actual COP against design and ASHRAE standards.

    Returns:
        dict with cop_vs_design (ratio), cop_vs_ashrae (ratio),
        energy_star_rating (0-100), and assessment string.
    """
    cop_vs_design = actual_cop / design_cop if design_cop > 0 else 0.0
    cop_vs_ashrae = actual_cop / ashrae_minimum_cop if ashrae_minimum_cop > 0 else 0.0

    # Energy Star simplified rating:
    # >= design COP → 100, >= ASHRAE → 50-80, < ASHRAE → < 50
    if cop_vs_design >= 0.95:
        energy_star = 90.0 + min(10.0, (cop_vs_design - 0.95) * 200)
    elif cop_vs_ashrae >= 1.0:
        energy_star = 50.0 + (cop_vs_design / 0.95) * 40.0
    else:
        energy_star = max(0.0, cop_vs_ashrae * 50.0)

    energy_star = min(100.0, max(0.0, energy_star))

    if cop_vs_design >= 1.0:
        assessment = "Excellent — exceeding design COP"
    elif cop_vs_design >= 0.9:
        assessment = "Good — near design COP"
    elif cop_vs_ashrae >= 1.0:
        assessment = "Adequate — meets ASHRAE minimum"
    else:
        assessment = "Poor — below ASHRAE minimum, investigate"

    return {
        "cop_vs_design": round(cop_vs_design, 4),
        "cop_vs_ashrae": round(cop_vs_ashrae, 4),
        "energy_star_rating": round(energy_star, 1),
        "assessment": assessment,
    }


def calculate_kpis(
    snapshots: List[Dict[str, Any]],
    memory_entries: List[Dict[str, Any]],
    electricity_price: float = 0.8,
    carbon_price: float = 0.08,
    design_cop: float = 6.0,
    period_start: float = 0.0,
    period_end: float = 0.0,
) -> KPIResult:
    """Calculate KPIs from a collection of plant snapshots and memory entries.

    Args:
        snapshots: List of plant snapshot dicts.
        memory_entries: List of MemoryEntry dicts.
        electricity_price: Price per kWh in currency units.
        carbon_price: Carbon price per kgCO2.
        design_cop: Design COP for benchmarking.
        period_start: Start of reporting period (unix timestamp).
        period_end: End of reporting period.

    Returns:
        KPIResult with all computed metrics.
    """
    result = KPIResult(period_start=period_start, period_end=period_end)

    if not snapshots:
        return result

    # Aggregate from snapshots
    total_cooling_kw = 0.0
    total_power_kw = 0.0
    for snap in snapshots:
        load_rt = snap.get("total_cooling_load_rt", 0)
        power = snap.get("total_power_kw", 0)
        total_cooling_kw += load_rt * KW_PER_RT
        total_power_kw += power

    n = len(snapshots)
    avg_cooling_kw = total_cooling_kw / n if n > 0 else 0.0
    avg_power_kw = total_power_kw / n if n > 0 else 0.0

    result.total_cooling_energy_kwh = total_cooling_kw  # simplified (assumes 1h per snapshot)
    result.total_power_consumption_kwh = total_power_kw

    # COP and EER
    result.average_cop = (
        compute_cop(avg_cooling_kw / KW_PER_RT, avg_power_kw)
        if avg_power_kw > 0
        else 0.0
    )
    result.average_eer = (
        compute_eer(avg_cooling_kw / KW_PER_RT, avg_power_kw)
        if avg_power_kw > 0
        else 0.0
    )

    # Carbon
    result.total_carbon_emissions_kg = total_power_kw * KG_CO2_PER_KWH_DEFAULT
    result.carbon_intensity_kg_per_kwh = compute_carbon_intensity(
        total_power_kw, result.total_carbon_emissions_kg
    )

    # Cost
    result.total_energy_cost = total_power_kw * electricity_price
    result.total_carbon_cost = result.total_carbon_emissions_kg * carbon_price

    # Operations from memory
    if memory_entries:
        result.num_strategies_executed = sum(
            1 for e in memory_entries if e.get("execution_status") == "completed"
        )
        result.num_strategies_aborted = sum(
            1 for e in memory_entries if e.get("execution_status") == "aborted"
        )

        cop_improvements = [
            e.get("cop_improvement", 0) or 0 for e in memory_entries
        ]
        result.average_cop_improvement = (
            sum(cop_improvements) / len(cop_improvements)
            if cop_improvements
            else 0.0
        )

        result.total_energy_saved_kwh = sum(
            e.get("energy_saving_kwh", 0) or 0 for e in memory_entries
        )
        result.total_carbon_saved_kg = sum(
            e.get("carbon_saving_kg", 0) or 0 for e in memory_entries
        )

    # Benchmark
    result.total_cost_saved = (
        result.total_energy_saved_kwh * electricity_price
        + result.total_carbon_saved_kg * carbon_price
    )
    benchmark = benchmark_against_standard(result.average_cop, design_cop)
    result.cop_vs_design = benchmark["cop_vs_design"]
    result.energy_star_rating = benchmark["energy_star_rating"]

    return result
