import numpy as np


class ActionMask:
    """Convert MILP output to DRL action masks."""

    @staticmethod
    def from_milp_schedule(schedule: dict[str, dict]) -> dict[str, np.ndarray]:
        masks: dict[str, np.ndarray] = {}
        for device_id, plan in schedule.items():
            if plan.get("on", False):
                masks[device_id] = np.ones(1)
            else:
                masks[device_id] = np.zeros(1)
        return masks

    @staticmethod
    def apply_constraints(
        actions: dict[str, np.ndarray],
        limits: dict[str, dict],
    ) -> dict[str, np.ndarray]:
        for device_id, action in actions.items():
            limit = limits.get(device_id, {})
            lo = limit.get("min", -np.inf)
            hi = limit.get("max", np.inf)
            actions[device_id] = np.clip(action, lo, hi)
        return actions
