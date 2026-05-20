from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional

import numpy as np
from scipy.optimize import minimize

from .constraints import surge_constraint, capacity_balance
from .objective import (
    compute_carbon_cost,
    compute_energy_cost,
    compute_water_cost,
    total_objective,
)
from .simulation.chiller import CentrifugalChiller


@dataclass
class OptimizationSolution:
    chiller_loads: Dict[str, float]
    total_power_kw: float
    total_objective: float
    energy_cost: float
    carbon_cost: float
    wear_cost: float
    water_cost: float = 0.0
    is_feasible: bool = True
    constraint_violations: List[str] = field(default_factory=list)


class ChillerPlantOptimizer:
    """MINLP solver for chiller plant operation.

    Discrete: which chillers are ON/OFF (enumeration).
    Continuous: PLR for each running chiller (scipy SLSQP).
    """

    def __init__(self, chillers: Dict[str, CentrifugalChiller]):
        self.chillers = chillers
        self._names = list(chillers.keys())

    def enumerate_feasible_combinations(
        self, total_load_rt: float, t_cw: float, t_chw: float = 7.0
    ) -> List[Dict[str, float]]:
        if total_load_rt <= 0:
            return []

        feasible: List[Dict[str, float]] = []
        n = len(self._names)
        total_capacity = sum(c.capacity_rt for c in self.chillers.values())

        if total_load_rt > total_capacity * 1.05:
            return []

        for k in range(1, n + 1):
            for subset in combinations(self._names, k):
                running_cap = sum(self.chillers[name].capacity_rt for name in subset)
                if running_cap < total_load_rt:
                    continue

                loads: Dict[str, float] = {}
                all_ok = True
                for name in subset:
                    ch = self.chillers[name]
                    share = ch.capacity_rt / running_cap
                    load_rt = total_load_rt * share
                    plr = load_rt / ch.capacity_rt
                    ok, _ = surge_constraint(ch, plr, t_cw)
                    if not ok:
                        all_ok = False
                        break
                    loads[name] = load_rt

                if not all_ok:
                    continue

                for name in self._names:
                    if name not in loads:
                        loads[name] = 0.0

                ok, _ = capacity_balance(
                    {name: self.chillers[name].capacity_rt for name in subset},
                    total_load_rt,
                )
                if ok:
                    feasible.append(loads)

        return feasible

    def optimize_continuous_params(
        self, discrete_config: Dict[str, float], t_chw: float, t_cw: float
    ) -> OptimizationSolution:
        running = [name for name, load in discrete_config.items() if load > 0]

        if not running:
            return OptimizationSolution(
                chiller_loads=dict(discrete_config),
                total_power_kw=0.0,
                total_objective=0.0,
                energy_cost=0.0,
                carbon_cost=0.0,
                wear_cost=0.0,
            )

        total_load_rt = sum(discrete_config.values())

        def objective(x):
            total_power = 0.0
            for i, name in enumerate(running):
                ch = self.chillers[name]
                load_rt = x[i] * ch.capacity_rt
                total_power += ch.compute_power_kw(load_rt, t_chw, t_cw)
            return total_power

        bounds = []
        for name in running:
            ch = self.chillers[name]
            lb = ch.surge_boundary(t_cw)
            bounds.append((lb, 1.0))

        x0 = []
        for name in running:
            load_rt = discrete_config[name]
            plr = load_rt / self.chillers[name].capacity_rt
            plr = max(bounds[len(x0)][0], min(bounds[len(x0)][1], plr))
            x0.append(plr)

        constraints = [
            {
                "type": "ineq",
                "fun": lambda x: sum(
                    x[i] * self.chillers[name].capacity_rt
                    for i, name in enumerate(running)
                )
                - total_load_rt,
            },
            {
                "type": "ineq",
                "fun": lambda x: total_load_rt * 1.05
                - sum(
                    x[i] * self.chillers[name].capacity_rt
                    for i, name in enumerate(running)
                ),
            },
        ]

        result = minimize(
            objective, x0, method="SLSQP", bounds=bounds,
            constraints=constraints,
            options={"maxiter": 200, "ftol": 1e-8},
        )

        optimized_loads: Dict[str, float] = {}
        for name in self._names:
            optimized_loads[name] = 0.0

        total_power_kw = 0.0
        if result.success:
            for i, name in enumerate(running):
                plr = result.x[i]
                load_rt = plr * self.chillers[name].capacity_rt
                optimized_loads[name] = load_rt
                total_power_kw += self.chillers[name].compute_power_kw(load_rt, t_chw, t_cw)
        else:
            for name in running:
                optimized_loads[name] = discrete_config[name]
                total_power_kw += self.chillers[name].compute_power_kw(
                    discrete_config[name], t_chw, t_cw
                )

        energy_cost = compute_energy_cost(total_power_kw, 0.8)
        carbon_cost = compute_carbon_cost(total_power_kw, 0.5, 0.08)
        wear_cost = len(running) * 50.0
        water_cost = compute_water_cost(total_power_kw)
        total_obj = total_objective(energy_cost, carbon_cost, wear_cost, water_cost=water_cost)

        return OptimizationSolution(
            chiller_loads=optimized_loads,
            total_power_kw=total_power_kw,
            total_objective=total_obj,
            energy_cost=energy_cost,
            carbon_cost=carbon_cost,
            wear_cost=wear_cost,
            water_cost=water_cost,
        )

    def optimize(
        self,
        total_load_rt: float,
        t_cw: float,
        t_chw: float = 7.0,
        price_per_kwh: float = 0.8,
        grid_carbon_intensity: float = 0.5,
        carbon_price: float = 0.08,
        w_energy: float = 1.0,
        w_carbon: float = 1.0,
        w_wear: float = 1.0,
        water_price_per_m3: float = 3.5,
        w_water: float = 1.0,
    ) -> OptimizationSolution:
        if total_load_rt <= 0:
            loads = {name: 0.0 for name in self._names}
            return OptimizationSolution(
                chiller_loads=loads,
                total_power_kw=0.0,
                total_objective=0.0,
                energy_cost=0.0,
                carbon_cost=0.0,
                wear_cost=0.0,
                water_cost=0.0,
            )

        discrete_combos = self.enumerate_feasible_combinations(total_load_rt, t_cw, t_chw)

        if not discrete_combos:
            return OptimizationSolution(
                chiller_loads={name: 0.0 for name in self._names},
                total_power_kw=0.0,
                total_objective=float("inf"),
                energy_cost=0.0,
                carbon_cost=0.0,
                wear_cost=0.0,
                water_cost=0.0,
                is_feasible=False,
                constraint_violations=["No feasible discrete combination found"],
            )

        best: Optional[OptimizationSolution] = None
        for combo in discrete_combos:
            sol = self.optimize_continuous_params(combo, t_chw, t_cw)
            energy_cost = compute_energy_cost(sol.total_power_kw, price_per_kwh)
            carbon_cost = compute_carbon_cost(
                sol.total_power_kw, grid_carbon_intensity, carbon_price
            )
            n_running = sum(1 for v in sol.chiller_loads.values() if v > 0)
            wear_cost = n_running * 50.0
            water_cost = compute_water_cost(sol.total_power_kw, water_price_per_m3)
            sol.energy_cost = energy_cost
            sol.carbon_cost = carbon_cost
            sol.wear_cost = wear_cost
            sol.water_cost = water_cost
            sol.total_objective = total_objective(
                energy_cost, carbon_cost, wear_cost,
                w_energy, w_carbon, w_wear, water_cost, w_water,
            )

            if best is None or sol.total_objective < best.total_objective:
                best = sol

        return best if best is not None else OptimizationSolution(
            chiller_loads={name: 0.0 for name in self._names},
            total_power_kw=0.0,
            total_objective=float("inf"),
            energy_cost=0.0,
            carbon_cost=0.0,
            wear_cost=0.0,
            water_cost=0.0,
            is_feasible=False,
        )

    def multi_period_optimize(
        self,
        load_schedule: list[float],
        t_cw_schedule: list[float],
        t_chw: float = 7.0,
        price_per_kwh: float = 0.8,
        grid_carbon_intensity: float = 0.5,
        carbon_price: float = 0.08,
        w_energy: float = 1.0,
        w_carbon: float = 1.0,
        w_wear: float = 1.0,
        water_price_per_m3: float = 3.5,
        w_water: float = 1.0,
        min_runtime_s: float = 1800.0,
    ) -> list[OptimizationSolution]:
        """Optimize over multiple time periods with runtime constraints.

        Each period is optimized independently but with carry-over state
        for minimum runtime and start/stop penalty tracking.
        """
        solutions: list[OptimizationSolution] = []
        last_running: set[str] = set()
        last_state_change: dict[str, float] = {}

        for t, (load, t_cw) in enumerate(zip(load_schedule, t_cw_schedule)):
            sol = self.optimize(
                total_load_rt=load,
                t_cw=t_cw,
                t_chw=t_chw,
                price_per_kwh=price_per_kwh,
                grid_carbon_intensity=grid_carbon_intensity,
                carbon_price=carbon_price,
                w_energy=w_energy,
                w_carbon=w_carbon,
                w_wear=w_wear,
                water_price_per_m3=water_price_per_m3,
                w_water=w_water,
            )

            current_running = {
                name for name, ld in sol.chiller_loads.items() if ld > 0
            }

            # Penalize rapid cycling: extra wear cost if state changed recently
            for name in current_running ^ last_running:
                if name in last_state_change:
                    elapsed = t - last_state_change[name]
                    if elapsed * 3600 < min_runtime_s:
                        sol.wear_cost += 100.0
                        sol.total_objective = total_objective(
                            sol.energy_cost, sol.carbon_cost, sol.wear_cost,
                            w_energy, w_carbon, w_wear, sol.water_cost, w_water,
                        )
                last_state_change[name] = t

            last_running = current_running
            solutions.append(sol)

        return solutions
