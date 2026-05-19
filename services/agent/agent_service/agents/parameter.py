"""Parameter Agent — fine-tunes strategy parameters in real time.

Applies deadband, rate limiting, and oscillation detection to prevent
hunting, smooth transitions, and maintain stable chiller plant operation.

All core logic is pure Python functions for testability.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .agents.base import AgentContext, BaseAgent

_DEFAULT_CAPACITY_RT = 500.0
_DEVIATION_THRESHOLD_PCT = 0.05  # 5% of capacity


@dataclass
class ParameterAdjustment:
    """A single parameter fine-tuning adjustment."""

    device: str
    param: str  # parameter name being adjusted
    original_value: float
    adjusted_value: float
    reason: str = ""


@dataclass
class ParameterResult:
    """Result of parameter adjustment across all devices."""

    adjustments: List[ParameterAdjustment] = field(default_factory=list)
    needs_new_strategy: bool = False
    new_strategy_reason: str = ""
    deadband_active: bool = False
    rate_limited: bool = False


def apply_deadband(
    value: float, setpoint: float, deadband: float = 0.3
) -> Tuple[float, bool]:
    """Check if value is within deadband of setpoint.

    If |value - setpoint| <= deadband, return setpoint (no change needed).
    This prevents hunting around the setpoint.

    Args:
        value: Target value (desired).
        setpoint: Current setpoint (actual).
        deadband: Allowed tolerance band.

    Returns:
        (adjusted_value, was_in_deadband)
    """
    if abs(value - setpoint) <= deadband:
        return setpoint, True
    return value, False


def apply_rate_limit(
    current_value: float, target_value: float, max_rate: float = 0.1
) -> Tuple[float, bool]:
    """Limit the rate of change to max_rate units per minute.

    If the change from current to target exceeds max_rate, cap the change.
    Works symmetrically for both positive and negative changes.

    Args:
        current_value: Current actual value.
        target_value: Desired target value.
        max_rate: Maximum allowed change per minute.

    Returns:
        (rate_limited_value, was_limited)
    """
    diff = target_value - current_value
    if abs(diff) <= max_rate:
        return target_value, False

    direction = 1.0 if diff > 0 else -1.0
    limited = current_value + direction * max_rate
    return limited, True


def detect_oscillation(
    history: List[Dict[str, float]], window_size: int = 5, threshold: float = 0.5
) -> bool:
    """Detect if a parameter is oscillating by checking direction changes.

    Looks at the recent history of a parameter value and counts how many
    times the direction of change reverses. >=3 direction changes in the
    window indicates oscillation.

    Args:
        history: List of {param_name: value} dicts, most recent last.
        window_size: Number of recent entries to examine.
        threshold: Minimum ratio of direction changes to transitions (unused,
                   kept for API compatibility; logic uses absolute count >=3).

    Returns:
        True if oscillation detected.
    """
    if len(history) < 3:
        return False

    # Take the last window_size entries
    recent = history[-window_size:] if len(history) >= window_size else history

    if len(recent) < 3:
        return False

    # Extract the first available key from the dicts
    extract_key = None
    for entry in recent:
        if entry:
            extract_key = next(iter(entry.keys()))
            break

    if extract_key is None:
        return False

    # Get the values
    values = [entry.get(extract_key, 0.0) for entry in recent]

    # Count direction changes
    direction_changes = 0
    for i in range(1, len(values) - 1):
        diff1 = values[i] - values[i - 1]
        diff2 = values[i + 1] - values[i]
        # Direction change if signs differ (and neither is zero)
        if diff1 * diff2 < 0:
            direction_changes += 1

    return direction_changes >= 3


def _detect_oscillation_for_device(
    load_history: List[Dict[str, float]],
    device: str,
    window_size: int = 5,
) -> bool:
    """Detect oscillation for a specific device in the load history."""
    if not load_history or len(load_history) < 3:
        return False

    recent = load_history[-window_size:] if len(load_history) >= window_size else load_history
    if len(recent) < 3:
        return False

    values = [entry.get(device, 0.0) for entry in recent]

    direction_changes = 0
    for i in range(1, len(values) - 1):
        diff1 = values[i] - values[i - 1]
        diff2 = values[i + 1] - values[i]
        if diff1 * diff2 < 0:
            direction_changes += 1

    return direction_changes >= 3


def adjust_parameters(
    target_loads: Dict[str, float],
    current_loads: Dict[str, float],
    capacity_rt: Dict[str, float],
    load_history: Optional[List[Dict[str, float]]] = None,
    deadband_rt: float = 15.0,
    max_rate_rt_per_min: float = 25.0,
) -> ParameterResult:
    """Apply deadband, rate limiting, and oscillation detection to target loads.

    For each chiller:
    1. Check deadband: if |target - current| <= deadband_rt, keep current.
    2. Apply rate limit: if |target - current| > max_rate, limit to max_rate.
    3. Check oscillation: if load_history shows oscillation, flag needs_new_strategy.
    4. If any load deviates > 5% of capacity from target after deadband, flag
       for new strategy.

    Args:
        target_loads: Desired chiller loads from strategy (device -> RT).
        current_loads: Current actual chiller loads (device -> RT).
        capacity_rt: Device capacity in RT (device -> RT).
        load_history: Optional recent history for oscillation detection.
        deadband_rt: Deadband in RT (~3% of 500RT = 15RT).
        max_rate_rt_per_min: Max ramp rate in RT/min.

    Returns:
        ParameterResult with adjustments and flags.
    """
    result = ParameterResult()
    load_history = load_history or []

    for device, target_load in target_loads.items():
        cap = capacity_rt.get(device, _DEFAULT_CAPACITY_RT)
        current_load = current_loads.get(device, 0.0)

        # Step 1: Apply deadband
        adjusted, was_in_deadband = apply_deadband(target_load, current_load, deadband_rt)
        if was_in_deadband and abs(target_load - current_load) > 1e-6:
            result.deadband_active = True

        # Step 2: Apply rate limit
        rate_limited_val, was_limited = apply_rate_limit(
            current_load, adjusted, max_rate_rt_per_min
        )
        if was_limited:
            result.rate_limited = True
        adjusted = rate_limited_val

        # Record adjustment if value changed from target
        if abs(adjusted - target_load) > 1e-6:
            reason_parts = []
            if was_in_deadband:
                reason_parts.append(f"deadband (target {target_load:.1f} within {deadband_rt:.1f}RT of current {current_load:.1f})")
            if was_limited:
                reason_parts.append(f"rate-limited (max {max_rate_rt_per_min:.1f}RT/min)")

            adjustment = ParameterAdjustment(
                device=device,
                param="load",
                original_value=target_load,
                adjusted_value=adjusted,
                reason="; ".join(reason_parts) if reason_parts else "unknown",
            )
            result.adjustments.append(adjustment)

            # Check if deviation exceeds 5% of capacity
            deviation_pct = abs(adjusted - target_load) / cap
            if deviation_pct > _DEVIATION_THRESHOLD_PCT:
                result.needs_new_strategy = True
                if not result.new_strategy_reason:
                    result.new_strategy_reason = (
                        f"{device}: adjusted load ({adjusted:.1f}) deviates "
                        f"{deviation_pct:.1%} from target ({target_load:.1f}), "
                        f"exceeding {_DEVIATION_THRESHOLD_PCT:.0%} of capacity ({cap:.0f}RT)"
                    )

        # Step 3: Check oscillation for this device
        if load_history and _detect_oscillation_for_device(load_history, device):
            result.needs_new_strategy = True
            if not result.new_strategy_reason:
                result.new_strategy_reason = (
                    f"{device}: oscillation detected in recent load history"
                )

    return result


class ParameterAgent(BaseAgent):
    """Parameter fine-tuning agent — applies deadband, rate limiting, oscillation detection.

    This agent sits between safety approval and execution. It takes the
    approved strategy's target loads and adjusts them in real-time to prevent
    hunting, ensure smooth ramps, and detect oscillations that warrant a
    new strategy.

    All core logic is in pure Python functions for testability.
    """

    def __init__(self, llm=None, context=None):
        super().__init__(name="parameter", llm=llm, context=context)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply parameter adjustments to target loads.

        Args:
            input_data: dict with:
                - target_loads: Dict[str, float] — desired chiller loads
                - current_loads: Dict[str, float] — current chiller loads
                - capacity_rt: Dict[str, float] — device capacities
                - load_history: Optional list of load snapshots
                - deadband_rt: float (default 15.0)
                - max_rate_rt_per_min: float (default 25.0)

        Returns:
            dict with adjustments, needs_new_strategy, new_strategy_reason,
            deadband_active, rate_limited.
        """
        target_loads = input_data.get("target_loads", {})
        current_loads = input_data.get("current_loads", {})
        capacity_rt = input_data.get("capacity_rt", {})
        load_history = input_data.get("load_history")

        result = adjust_parameters(
            target_loads=target_loads,
            current_loads=current_loads,
            capacity_rt=capacity_rt,
            load_history=load_history,
            deadband_rt=input_data.get("deadband_rt", 15.0),
            max_rate_rt_per_min=input_data.get("max_rate_rt_per_min", 25.0),
        )

        return {
            "adjustments": [
                {
                    "device": a.device,
                    "param": a.param,
                    "original_value": a.original_value,
                    "adjusted_value": a.adjusted_value,
                    "reason": a.reason,
                }
                for a in result.adjustments
            ],
            "needs_new_strategy": result.needs_new_strategy,
            "new_strategy_reason": result.new_strategy_reason,
            "deadband_active": result.deadband_active,
            "rate_limited": result.rate_limited,
        }
