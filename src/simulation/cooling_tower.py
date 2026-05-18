class CoolingTower:
    """Cooling tower model — simplified Merkel theory"""

    def __init__(
        self,
        name: str,
        design_heat_rejection_kw: float,
        design_flow_lps: float = 80.0,
        design_wb_temp: float = 28.0,
        design_approach: float = 4.0,
        rated_fan_power_kw: float = 15.0,
        design_range: float = 5.0,
    ):
        self.name = name
        self.design_heat_rejection_kw = design_heat_rejection_kw
        self.design_flow_lps = design_flow_lps
        self.design_wb_temp = design_wb_temp
        self.design_approach = design_approach
        self.rated_fan_power_kw = rated_fan_power_kw
        self.design_range = design_range

    def compute_outlet_temp(
        self,
        heat_load_kw: float,
        water_flow_lps: float,
        fan_speed_hz: float,
        outdoor_wb: float,
    ) -> float:
        if fan_speed_hz <= 0 or water_flow_lps <= 0:
            return 50.0
        load_ratio = (
            heat_load_kw / self.design_heat_rejection_kw
            if self.design_heat_rejection_kw > 0
            else 1.0
        )
        fan_ratio = fan_speed_hz / 50.0
        flow_ratio = water_flow_lps / self.design_flow_lps
        approach = self.design_approach * load_ratio / (fan_ratio * flow_ratio)
        return max(outdoor_wb, outdoor_wb + approach)

    def compute_fan_power_kw(self, fan_speed_hz: float) -> float:
        if fan_speed_hz <= 0:
            return 0.0
        return self.rated_fan_power_kw * (fan_speed_hz / 50.0) ** 3
