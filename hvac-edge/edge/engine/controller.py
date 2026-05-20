import logging

logger = logging.getLogger(__name__)


class SafetyGate:
    """Rejects control outputs that violate hard limits."""

    def __init__(self, limits: dict[str, tuple[float, float]]):
        self.limits = limits

    def check(self, param: str, value: float) -> bool:
        if param not in self.limits:
            return True
        lo, hi = self.limits[param]
        return lo <= value <= hi


class PIDController:
    """Discrete PID controller."""

    def __init__(self, kp: float, ki: float = 0.0, kd: float = 0.0,
                 setpoint: float = 0.0, output_min: float = -1e6, output_max: float = 1e6):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, measurement: float, dt: float = 1.0) -> float:
        error = self.setpoint - measurement
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error

        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(self.output_min, min(self.output_max, output))

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0


class Interlock:
    """Device interlock engine -- evaluates rules and returns enforcement actions."""

    def __init__(self, rules: list[dict]):
        self.rules = rules

    def evaluate(self, state: dict) -> list[str]:
        actions = []
        for rule in self.rules:
            condition = rule["if"]
            if self._eval_condition(condition, state):
                actions.append(rule["then"])
        return actions

    def _eval_condition(self, cond: str, state: dict) -> bool:
        # Simple parser: "CH-1.status == 'off'"
        parts = cond.split(" == ")
        if len(parts) != 2:
            return False
        key = parts[0].strip()
        expected = parts[1].strip().strip("'\"")
        return str(state.get(key)) == expected
