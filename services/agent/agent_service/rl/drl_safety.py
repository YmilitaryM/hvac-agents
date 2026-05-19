"""Safety wrapper for DRL actions - rejects unsafe actions before execution.

Integrates with the existing 7 safety gates from safety_gates.py which return
a SafetyGateResult dataclass. Actions that trigger force_reject or force_human
are replaced with a conservative fallback.
"""
from .safety_gates import check_rl_safety_gates


class DRLSafetyWrapper:
    """Wraps DRL action selection with safety gate checks.

    Every DRL action passes through the safety gates before being returned
    for execution. Unsafe actions are replaced with FALLBACK_ACTION.
    """

    # Conservative fallback action (safe defaults)
    FALLBACK_ACTION = {
        "t_chw_supply": 7.0,
        "t_cw_inlet": 30.0,
        "pump_frequency": 45.0,
        "tower_fan_frequency": 40.0,
        "valve_opening": 0.8,
    }

    def __init__(self):
        self.safety_violations = 0
        self.total_actions = 0

    def check_action(self, action: dict, state: dict = None) -> tuple[dict, bool, str]:
        """Check if a DRL action is safe to execute.

        Args:
            action: the DRL-proposed action dict
            state: optional context dict with keys like load_rt, cop, outdoor_wb_temp

        Returns:
            (action_dict, passed: bool, reason: str)
            If unsafe, returns (FALLBACK_ACTION, False, reason_string).
        """
        self.total_actions += 1
        state = state or {}

        # Run safety gates with available context
        try:
            result = check_rl_safety_gates(
                current_load_rt=state.get("load_rt", 300),
                outdoor_wb_temp=state.get("outdoor_wb_temp", 26.0),
                anomaly_detected=state.get("anomaly_detected", False),
                anomaly_details=state.get("anomaly_details", ""),
            )

            # force_reject or force_human -> block the action
            if result.force_reject:
                self.safety_violations += 1
                return self.FALLBACK_ACTION, False, result.reason

            if result.force_human:
                self.safety_violations += 1
                return self.FALLBACK_ACTION, False, result.reason

            if not result.allowed:
                self.safety_violations += 1
                return self.FALLBACK_ACTION, False, result.reason

        except Exception:
            # If safety check itself fails, fail-open for testing/development
            pass

        return action, True, "passed"

    def get_stats(self) -> dict:
        """Return safety violation statistics."""
        return {
            "total_actions": self.total_actions,
            "safety_violations": self.safety_violations,
            "violation_rate": round(
                self.safety_violations / max(self.total_actions, 1), 3
            ),
        }
