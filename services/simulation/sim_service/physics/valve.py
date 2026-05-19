import math


class ControlValve:
    """Control valve with Cv characteristic model."""
    CHARACTERISTICS = ("equal_percentage", "linear", "quick_open")

    def __init__(self, name: str, cv: float = 100, characteristic: str = "equal_percentage",
                 rangeability: float = 50, actuator_speed_s: float = 30, leakage_rate: float = 0.001):
        self.name = name
        self.cv = cv
        self.characteristic = characteristic
        self.rangeability = rangeability
        self.actuator_speed_s = actuator_speed_s
        self.leakage_rate = leakage_rate

    def inherent_characteristic(self, x: float) -> float:
        """x in [0, 1] -- valve opening fraction."""
        x = max(0.0, min(1.0, x))
        if x < self.leakage_rate:
            return 0.0
        if self.characteristic == "equal_percentage":
            return self.rangeability ** (x - 1)
        elif self.characteristic == "linear":
            return x
        elif self.characteristic == "quick_open":
            return math.sqrt(x)
        return x

    def compute_flow_lps(self, x: float, dp_kpa: float, sg: float = 1.0) -> float:
        """Q (L/s) = Cv * f(x) * sqrt(dp[kPa] / SG) / 0.865 (unit conversion)."""
        if dp_kpa <= 0:
            return 0.0
        ich = self.inherent_characteristic(x)
        if ich <= 0:
            return 0.0
        return self.cv * ich * math.sqrt(dp_kpa / sg) / 0.865

    def compute_pressure_drop_kpa(self, x: float, flow_lps: float, sg: float = 1.0) -> float:
        ich = self.inherent_characteristic(x)
        if ich <= 0 or self.cv <= 0:
            return float("inf")
        return sg * (flow_lps * 0.865 / (self.cv * ich)) ** 2


class IsolationValve:
    """On/off isolation valve."""

    def __init__(self, name: str, open_cv: float = 500):
        self.name = name
        self.open_cv = open_cv

    def is_open(self, command: bool) -> bool:
        return command

    def compute_flow_lps(self, is_open: bool, dp_kpa: float, sg: float = 1.0) -> float:
        if not is_open or dp_kpa <= 0:
            return 0.0
        return self.open_cv * math.sqrt(dp_kpa / sg) / 0.865


class CheckValve:
    """Check valve -- allows forward flow only."""

    def __init__(self, name: str, cracking_pressure_kpa: float = 5.0, cv: float = 200):
        self.name = name
        self.cracking_pressure_kpa = cracking_pressure_kpa
        self.cv = cv

    def compute_flow_lps(self, dp_kpa: float, sg: float = 1.0) -> float:
        if dp_kpa < self.cracking_pressure_kpa:
            return 0.0
        effective_dp = dp_kpa - self.cracking_pressure_kpa
        return self.cv * math.sqrt(effective_dp / sg) / 0.865
