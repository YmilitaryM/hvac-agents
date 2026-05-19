import numpy as np

_F_LOAD_AT_FULL = 1.0 - 1.2 * (1.0 - 0.75) ** 2  # 0.925


class CentrifugalChiller:
    """Centrifugal chiller physics model — reverse Carnot + empirical corrections"""

    def __init__(
        self,
        name: str,
        capacity_rt: float,
        design_cop: float = 6.0,
        design_chw_supply_temp: float = 7.0,
        design_cw_entering_temp: float = 30.0,
        min_plr: float = 0.2,
    ):
        self.name = name
        self.capacity_rt = capacity_rt
        self.design_cop = design_cop
        self.design_chw_supply_temp = design_chw_supply_temp
        self.design_cw_entering_temp = design_cw_entering_temp
        self.min_plr_base = min_plr

    def surge_boundary(self, t_cw: float) -> float:
        """Surge boundary — higher condensing temp raises min allowed PLR"""
        delta_t = max(0, (t_cw - self.design_cw_entering_temp))
        boundary = self.min_plr_base + delta_t * 0.015
        return min(0.5, max(self.min_plr_base, boundary))

    def min_capacity_rt(self, t_cw: float) -> float:
        return self.surge_boundary(t_cw) * self.capacity_rt

    @property
    def max_capacity_rt(self) -> float:
        return self.capacity_rt

    def compute_cop(self, plr: float, t_chw: float, t_cw: float) -> float:
        """Compute COP at given operating conditions

        COP(P, T_e, T_c) = COP_design * f_load(P) * f_evap(T_e) * f_cond(T_c)

        where:
          f_load: part-load correction, peaks around 75% PLR
          f_evap: evaporator temp correction, higher T_chw → higher COP
          f_cond: condenser temp correction, higher T_cw → lower COP
        """
        if plr < self.surge_boundary(t_cw):
            return 0.0

        f_load = (1.0 - 1.2 * (plr - 0.75) ** 2) / _F_LOAD_AT_FULL

        f_evap = 1.0 + 0.03 * (t_chw - self.design_chw_supply_temp)

        f_cond = 1.0 - 0.025 * (t_cw - self.design_cw_entering_temp)

        cop = self.design_cop * f_load * f_evap * f_cond
        return max(0.0, cop)

    def compute_power_kw(self, load_rt: float, t_chw: float, t_cw: float) -> float:
        """Compute power kW = cooling(kW) / COP"""
        if load_rt <= 0:
            return 0.0
        plr = load_rt / self.capacity_rt if self.capacity_rt > 0 else 0
        cop = self.compute_cop(plr=plr, t_chw=t_chw, t_cw=t_cw)
        if cop <= 0:
            return float("inf")
        return (load_rt * 3.517) / cop
