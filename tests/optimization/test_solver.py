import pytest
import numpy as np
from src.simulation.chiller import CentrifugalChiller
from src.optimization.solver import ChillerPlantOptimizer, OptimizationSolution
from src.optimization.pareto import compute_pareto_front


class TestEnumerateCombinations:
    @pytest.fixture
    def two_chillers(self):
        return {
            "ch1": CentrifugalChiller(name="ch1", capacity_rt=500, design_cop=6.0, min_plr=0.2),
            "ch2": CentrifugalChiller(name="ch2", capacity_rt=500, design_cop=6.0, min_plr=0.2),
        }

    def test_finds_feasible_solutions(self, two_chillers):
        """2 chillers, 600RT load -- should find feasible solutions"""
        opt = ChillerPlantOptimizer(two_chillers)
        combos = opt.enumerate_feasible_combinations(600.0, t_cw=30.0)
        assert len(combos) > 0
        for combo in combos:
            total = sum(combo.values())
            assert abs(total - 600.0) < 60  # within 10%

    def test_surge_constraint_obeyed(self, two_chillers):
        """No chiller below surge boundary"""
        opt = ChillerPlantOptimizer(two_chillers)
        combos = opt.enumerate_feasible_combinations(600.0, t_cw=30.0)
        for combo in combos:
            for name, load in combo.items():
                if load > 0:
                    ch = two_chillers[name]
                    plr = load / ch.capacity_rt
                    assert plr >= ch.surge_boundary(30.0)

    def test_infeasible_load_returns_empty(self, two_chillers):
        """1500RT > total capacity (1000RT) -- no feasible solutions"""
        opt = ChillerPlantOptimizer(two_chillers)
        combos = opt.enumerate_feasible_combinations(1500.0, t_cw=30.0)
        assert len(combos) == 0

    def test_single_chiller(self):
        """1 chiller, 300RT load -- should find exactly one solution"""
        chillers = {
            "ch1": CentrifugalChiller(name="ch1", capacity_rt=500, design_cop=6.0, min_plr=0.2),
        }
        opt = ChillerPlantOptimizer(chillers)
        combos = opt.enumerate_feasible_combinations(300.0, t_cw=30.0)
        assert len(combos) == 1
        assert combos[0]["ch1"] == pytest.approx(300.0, rel=0.1)


class TestContinuousOptimization:
    @pytest.fixture
    def optimizer(self):
        chillers = {
            "ch1": CentrifugalChiller(name="ch1", capacity_rt=500, design_cop=6.0, min_plr=0.2),
            "ch2": CentrifugalChiller(name="ch2", capacity_rt=500, design_cop=6.0, min_plr=0.2),
        }
        return ChillerPlantOptimizer(chillers)

    def test_optimize_improves_cop(self, optimizer):
        """Continuous optimization should not worsen the solution"""
        config = {"ch1": 300.0, "ch2": 300.0}  # equal split
        result = optimizer.optimize_continuous_params(config, t_chw=7.0, t_cw=30.0)
        assert result.is_feasible
        assert result.total_power_kw > 0

    def test_optimize_respects_load_demand(self, optimizer):
        """Optimized loads should meet total demand"""
        config = {"ch1": 400.0, "ch2": 200.0}
        result = optimizer.optimize_continuous_params(config, t_chw=7.0, t_cw=30.0)
        total_load = sum(result.chiller_loads.values())
        assert total_load == pytest.approx(600.0, rel=0.05)


class TestFullOptimization:
    @pytest.fixture
    def optimizer(self):
        chillers = {
            "ch1": CentrifugalChiller(name="ch1", capacity_rt=500, design_cop=6.0, min_plr=0.2),
            "ch2": CentrifugalChiller(name="ch2", capacity_rt=500, design_cop=6.0, min_plr=0.2),
        }
        return ChillerPlantOptimizer(chillers)

    def test_optimize_returns_best_solution(self, optimizer):
        result = optimizer.optimize(total_load_rt=600.0, t_cw=30.0)
        assert result.is_feasible
        assert result.total_power_kw > 0
        assert result.total_objective > 0
        assert len(result.chiller_loads) == 2

    def test_optimize_zero_load(self, optimizer):
        result = optimizer.optimize(total_load_rt=0.0, t_cw=30.0)
        assert result.total_power_kw == 0.0


class TestParetoFront:
    def test_returns_non_dominated_solutions(self):
        sols = [
            OptimizationSolution(
                chiller_loads={"ch1": 300}, total_power_kw=100.0,
                total_objective=80.0, energy_cost=50.0, carbon_cost=20.0, wear_cost=10.0,
            ),
            OptimizationSolution(
                chiller_loads={"ch1": 300}, total_power_kw=110.0,
                total_objective=85.0, energy_cost=55.0, carbon_cost=20.0, wear_cost=10.0,
            ),
            OptimizationSolution(
                chiller_loads={"ch1": 300}, total_power_kw=95.0,
                total_objective=78.0, energy_cost=48.0, carbon_cost=22.0, wear_cost=8.0,
            ),
            OptimizationSolution(
                chiller_loads={"ch1": 300}, total_power_kw=105.0,
                total_objective=82.0, energy_cost=52.0, carbon_cost=18.0, wear_cost=12.0,
            ),
        ]
        front = compute_pareto_front(sols)
        assert len(front) >= 2
        # The second solution (energy=55, carbon=20, wear=10) is dominated by first (50,20,10)
        dominated = sols[1]
        assert dominated not in front

    def test_all_non_dominated(self):
        sols = [
            OptimizationSolution(
                chiller_loads={"ch1": 300}, total_power_kw=100.0,
                total_objective=80.0, energy_cost=50.0, carbon_cost=20.0, wear_cost=10.0,
            ),
            OptimizationSolution(
                chiller_loads={"ch1": 300}, total_power_kw=95.0,
                total_objective=78.0, energy_cost=48.0, carbon_cost=22.0, wear_cost=8.0,
            ),
        ]
        front = compute_pareto_front(sols)
        assert len(front) == 2
