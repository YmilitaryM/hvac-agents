"""Safety Agent — pure rule engine for hard safety constraint checking.

This agent is intentionally deterministic — no LLM, no probabilistic logic.
It checks hard safety constraints and either passes or blocks the strategy.
Every check is a pure Python function for testability.

Checks performed:
1. Surge boundary — set_load below surge limit for given T_cw
2. Minimum runtime — stop actions too soon after start
3. Motor start interval — starts too close together
4. Transition plan required — discrete actions without a plan
5. Abort conditions — transition plan missing abort conditions
6. Capacity check — running capacity insufficient for load + margin
7. High ambient temperature warning
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.agents.base import AgentContext, BaseAgent
from src.schemas.strategy import Strategy

_DEFAULT_CAPACITY_RT = 500.0
_DEFAULT_DESIGN_CW_TEMP = 30.0
_DEFAULT_MIN_PLR = 0.2
_SURGE_SLOPE = 0.015
_SURGE_CAP = 0.5


def _compute_surge_boundary_plr(t_cw: float, design_cw: float = _DEFAULT_DESIGN_CW_TEMP) -> float:
    """Compute surge boundary PLR for given condenser water temperature."""
    delta = max(0.0, t_cw - design_cw)
    boundary = _DEFAULT_MIN_PLR + delta * _SURGE_SLOPE
    return min(_SURGE_CAP, max(_DEFAULT_MIN_PLR, boundary))


def _get_chiller_capacity(
    device: str, chillers: Optional[Dict[str, Any]] = None
) -> float:
    """Get chiller capacity in RT from chiller objects or dicts, default 500."""
    if chillers is None:
        return _DEFAULT_CAPACITY_RT
    ch_info = chillers.get(device)
    if ch_info is None:
        return _DEFAULT_CAPACITY_RT
    # Could be a CentrifugalChiller or a dict
    if hasattr(ch_info, "capacity_rt"):
        return ch_info.capacity_rt
    if isinstance(ch_info, dict):
        return ch_info.get("capacity_rt", _DEFAULT_CAPACITY_RT)
    return _DEFAULT_CAPACITY_RT


@dataclass
class SafetyCheckResult:
    """Result of safety checking a strategy."""

    passed: bool
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    blocking: bool = False  # True if any failure is a hard block


def check_safety(
    strategy: Strategy,
    chillers: Optional[Dict[str, Any]] = None,
    t_cw: float = 30.0,
    current_time: float = 0.0,
    device_states: Optional[Dict[str, Dict]] = None,
    recent_motor_starts: Optional[List[Tuple[str, float]]] = None,
) -> SafetyCheckResult:
    """Run all safety checks on a strategy.

    Checks:
    1. Surge boundary: set_load values must be above surge_boundary(t_cw).
    2. Minimum runtime: stop actions must respect min runtime (1800s).
    3. Motor start interval: start actions must be spaced >= 30s apart.
    4. Transition plan: discrete actions require a transition_plan.
    5. Abort conditions: transition_plan must have at least 1 abort condition.
    6. Capacity check: total running capacity must cover load + margin.
    7. High ambient: outdoor_wb_temp > 30C triggers warning.

    Blocking failures: surge violation, motor start interval, missing transition plan.
    Non-blocking warnings: min runtime, missing abort conditions, capacity tight, high ambient.

    Args:
        strategy: The Strategy to check.
        chillers: Optional dict of device_name -> CentrifugalChiller or dict with capacity_rt.
        t_cw: Condenser water entering temperature in degC.
        current_time: Current simulation time in seconds.
        device_states: Optional dict of device_name -> {last_start_time, last_stop_time, status}.
        recent_motor_starts: Optional list of (device_name, start_time) tuples.

    Returns:
        SafetyCheckResult with passed, failures, warnings, blocking flags.
    """
    failures: List[str] = []
    warnings: List[str] = []
    blocking: bool = False

    device_states = device_states or {}
    recent_motor_starts = recent_motor_starts or []

    # Determine which actions are discrete (start/stop)
    has_discrete = any(
        a.action in ("start", "stop", "open_valve", "close_valve")
        for a in strategy.actions
    )

    # --- Check 1: Surge boundary ---
    surge_boundary_plr = _compute_surge_boundary_plr(t_cw)
    for action in strategy.actions:
        if action.action == "set_load" and action.value is not None and action.value > 0:
            capacity = _get_chiller_capacity(action.device, chillers)
            plr = action.value / capacity
            min_allowed_load = surge_boundary_plr * capacity
            if plr < surge_boundary_plr:
                failures.append(
                    f"{action.device}: set_load={action.value:.1f}RT "
                    f"(PLR={plr:.2f}) below surge boundary "
                    f"PLR={surge_boundary_plr:.2f} "
                    f"({min_allowed_load:.0f}RT) at T_cw={t_cw}°C"
                )
                blocking = True

    # --- Check 2: Minimum runtime (stop actions) ---
    for action in strategy.actions:
        if action.action == "stop":
            ds = device_states.get(action.device, {})
            last_start = ds.get("last_start_time")
            if last_start is not None:
                elapsed = current_time - last_start
                if elapsed < 1800.0:
                    warnings.append(
                        f"{action.device}: stop action after only {elapsed:.0f}s "
                        f"of runtime (min 1800s). This may cause short cycling."
                    )

    # --- Check 3: Motor start interval (start actions) ---
    start_actions = [a for a in strategy.actions if a.action == "start"]
    for sa in start_actions:
        for other_name, start_time in recent_motor_starts:
            if other_name != sa.device and (current_time - start_time) < 30.0:
                failures.append(
                    f"{sa.device}: motor start too close to {other_name} "
                    f"({current_time - start_time:.0f}s ago, min 30s interval)"
                )
                blocking = True

    # --- Check 4: Transition plan required for discrete actions ---
    if has_discrete and strategy.transition_plan is None:
        failures.append(
            "Strategy has start/stop actions but no transition_plan. "
            "A transition plan is required for safe sequencing."
        )
        blocking = True

    # --- Check 5: Abort conditions in transition plan ---
    if strategy.transition_plan is not None:
        if not strategy.transition_plan.abort_conditions:
            warnings.append(
                "Transition plan has no abort conditions. "
                "Add at least one abort condition for safety."
            )

    # --- Check 6: Capacity check ---
    running_chiller_loads: Dict[str, float] = {}
    for action in strategy.actions:
        if action.action == "set_load" and action.value is not None and action.value > 0:
            running_chiller_loads[action.device] = action.value

    if running_chiller_loads:
        total_capacity = sum(
            _get_chiller_capacity(name, chillers) for name in running_chiller_loads
        )
        total_load = strategy.current_load_rt or sum(running_chiller_loads.values())
        required = total_load * 1.05
        if total_capacity < required:
            warnings.append(
                f"Capacity tight: {total_capacity:.0f}RT available, "
                f"{required:.0f}RT required (load={total_load:.0f}RT + 5% margin)"
            )

    # --- Check 7: High ambient temperature ---
    if strategy.outdoor_wb_temp > 30.0:
        warnings.append(
            f"High ambient temperature: {strategy.outdoor_wb_temp}°C wet-bulb. "
            f"Condenser performance may be degraded. Monitor approach temperature."
        )

    passed = len(failures) == 0

    return SafetyCheckResult(
        passed=passed,
        failures=failures,
        warnings=warnings,
        blocking=blocking,
    )


class SafetyAgent(BaseAgent):
    """Safety rule engine — deterministic, no LLM.

    Validates strategies against hard safety constraints before execution.
    All checks are pure Python functions for testability and auditability.
    """

    def __init__(self, llm=None, context=None):
        super().__init__(name="safety", llm=llm, context=context)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run safety checks on a strategy.

        Args:
            input_data: dict with:
                - pending_strategy or strategy: Strategy object or dict
                - chillers: optional dict of chiller info
                - t_cw: condenser water temp (default 30.0)
                - current_time: current time in seconds (default 0.0)
                - device_states: optional device state info
                - recent_motor_starts: optional motor start times

        Returns:
            dict with safety_result containing passed, failures, warnings, blocking.
        """
        strategy_data = input_data.get("pending_strategy") or input_data.get("strategy")
        if strategy_data is None:
            return {
                "safety_result": {
                    "passed": False,
                    "failures": ["No strategy provided"],
                    "warnings": [],
                    "blocking": True,
                }
            }

        if isinstance(strategy_data, dict):
            strategy = Strategy(**strategy_data)
        else:
            strategy = strategy_data

        result = check_safety(
            strategy=strategy,
            chillers=input_data.get("chillers"),
            t_cw=input_data.get("t_cw", 30.0),
            current_time=input_data.get("current_time", 0.0),
            device_states=input_data.get("device_states"),
            recent_motor_starts=input_data.get("recent_motor_starts"),
        )

        return {
            "safety_result": {
                "passed": result.passed,
                "failures": result.failures,
                "warnings": result.warnings,
                "blocking": result.blocking,
            }
        }
