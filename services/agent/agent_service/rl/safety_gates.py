"""Safety gates for the RL engine — prevent unsafe RL decisions.

These gates run BEFORE the RL bandit prediction and can:
1. Force human review for extreme conditions
2. Block RL decisions that violate hard constraints
3. Allow RL decision for normal conditions
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SafetyGateResult:
    """Result of safety gate checks."""
    allowed: bool  # Can RL make a decision?
    force_approve: bool = False  # Override: force approval
    force_reject: bool = False  # Override: force rejection
    force_human: bool = False  # Override: require human review
    reason: str = ""
    conditions_triggered: List[str] = field(default_factory=list)


def check_rl_safety_gates(
    strategy: Optional[Dict[str, Any]] = None,
    current_load_rt: float = 0.0,
    outdoor_wb_temp: float = 26.0,
    electricity_price: float = 0.8,
    carbon_intensity: float = 0.5,
    anomaly_detected: bool = False,
    anomaly_details: str = "",
) -> SafetyGateResult:
    """Check if it's safe for the RL bandit to make a decision.

    Gates (checked in order):

    1. CRITICAL ANOMALY: If anomaly_detected and details contain "CRITICAL"
       → force_human = True (don't trust RL during critical faults)

    2. EXTREME WEATHER: If outdoor_wb_temp > 35°C
       → force_human = True (extreme conditions need human judgment)

    3. EXTREME LOAD: If current_load_rt > 1400 RT (near plant capacity of 1500)
       → force_reject = True, reason: "Plant near capacity, reject non-essential changes"

    4. VERY LOW LOAD: If current_load_rt < 50 RT
       → force_reject = True, reason: "Load too low for automated optimization"

    5. PRICE SPIKE: If electricity_price > 3.0
       → force_human = True (extreme pricing needs human review)

    6. ZERO CARBON MANDATE: If carbon_intensity < 0.05 (clean grid)
       → force_approve = True (no carbon concern, let efficiency optimize)

    7. EMERGENCY: If anomaly_detected and anomaly_details contains "EMERGENCY" or "FAULT"
       → force_reject = True (emergency — reject all changes)

    If no gate triggers: allowed = True (RL can decide)
    """
    triggered = []

    # Gate 1: Critical anomaly
    if anomaly_detected and ("CRITICAL" in anomaly_details.upper() if anomaly_details else False):
        return SafetyGateResult(
            allowed=False, force_human=True,
            reason="Critical anomaly requires human review",
            conditions_triggered=["critical_anomaly"],
        )

    # Gate 7 (check first): Emergency — reject all changes
    if anomaly_detected and anomaly_details:
        upper = anomaly_details.upper()
        if "EMERGENCY" in upper or "FAULT" in upper:
            return SafetyGateResult(
                allowed=False, force_reject=True,
                reason="Emergency or fault condition — rejecting all strategy changes",
                conditions_triggered=["emergency_fault"],
            )

    # Gate 2: Extreme weather
    if outdoor_wb_temp > 35.0:
        triggered.append("extreme_weather")
        return SafetyGateResult(
            allowed=False, force_human=True,
            reason=f"Extreme outdoor wet bulb temperature ({outdoor_wb_temp:.1f}°C) requires human review",
            conditions_triggered=triggered,
        )

    # Gate 3: Extreme load
    if current_load_rt > 1400.0:
        triggered.append("extreme_load")
        return SafetyGateResult(
            allowed=False, force_reject=True,
            reason=f"Plant near capacity ({current_load_rt:.0f} RT), rejecting non-essential changes",
            conditions_triggered=triggered,
        )

    # Gate 4: Very low load
    if current_load_rt < 50.0:
        triggered.append("very_low_load")
        return SafetyGateResult(
            allowed=False, force_reject=True,
            reason=f"Load too low ({current_load_rt:.0f} RT) for automated optimization",
            conditions_triggered=triggered,
        )

    # Gate 5: Price spike
    if electricity_price > 3.0:
        triggered.append("price_spike")
        return SafetyGateResult(
            allowed=False, force_human=True,
            reason=f"Electricity price spike ({electricity_price:.2f}/kWh) requires human review",
            conditions_triggered=triggered,
        )

    # Gate 6: Zero carbon mandate
    if carbon_intensity < 0.05:
        triggered.append("clean_grid")
        return SafetyGateResult(
            allowed=True, force_approve=True,
            reason="Clean grid (low carbon intensity), approving efficiency optimization",
            conditions_triggered=triggered,
        )

    # All gates passed — RL can decide
    return SafetyGateResult(
        allowed=True,
        reason="All safety gates passed",
        conditions_triggered=triggered,
    )
