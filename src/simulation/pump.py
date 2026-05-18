class Pump:
    """Pump model — affinity laws"""

    def __init__(
        self,
        name: str,
        rated_power_kw: float = 37.0,
        rated_flow_lps: float = 100.0,
        rated_head_m: float = 32.0,
    ):
        self.name = name
        self.rated_power_kw = rated_power_kw
        self.rated_flow_lps = rated_flow_lps
        self.rated_head_m = rated_head_m

    def compute_power_kw(self, speed_hz: float) -> float:
        if speed_hz <= 0:
            return 0.0
        return self.rated_power_kw * (speed_hz / 50.0) ** 3

    def compute_flow_lps(self, speed_hz: float) -> float:
        if speed_hz <= 0:
            return 0.0
        return self.rated_flow_lps * (speed_hz / 50.0)
