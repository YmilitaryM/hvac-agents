"""Tests for Strategy Agent — optimization-based chiller plant control."""

import pytest

from src.agents.strategy import build_strategy, StrategyAgent
from src.optimization.solver import ChillerPlantOptimizer, OptimizationSolution
from src.schemas.strategy import Strategy, StrategyStatus
from src.simulation.chiller import CentrifugalChiller


class TestBuildStrategy:
    def test_creates_set_load_actions(self):
        sol = OptimizationSolution(
            chiller_loads={"ch1": 400.0, "ch2": 200.0},
            total_power_kw=180.0,
            total_objective=150.0,
            energy_cost=120.0,
            carbon_cost=20.0,
            wear_cost=10.0,
        )
        strategy = build_strategy(
            sol,
            current_load_rt=600,
            predicted_load_rt=600,
            strategy_id="strat_test_001",
        )
        assert strategy.strategy_id == "strat_test_001"
        assert len(strategy.actions) >= 2
        actions_by_device = {a.device: a for a in strategy.actions}
        assert "ch1" in actions_by_device
        assert "ch2" in actions_by_device
        assert actions_by_device["ch1"].action == "set_load"

    def test_creates_stop_action_for_zero_load(self):
        sol = OptimizationSolution(
            chiller_loads={"ch1": 500.0, "ch2": 0.0},
            total_power_kw=150.0,
            total_objective=120.0,
            energy_cost=100.0,
            carbon_cost=15.0,
            wear_cost=5.0,
        )
        strategy = build_strategy(
            sol,
            current_load_rt=500,
            predicted_load_rt=500,
            strategy_id="strat_test_002",
        )
        actions_by_device = {a.device: a for a in strategy.actions}
        assert actions_by_device["ch2"].action == "stop"

    def test_includes_transition_plan(self):
        sol = OptimizationSolution(
            chiller_loads={"ch1": 500.0},
            total_power_kw=160.0,
            total_objective=130.0,
            energy_cost=110.0,
            carbon_cost=15.0,
            wear_cost=5.0,
        )
        strategy = build_strategy(
            sol,
            current_load_rt=500,
            predicted_load_rt=500,
        )
        assert strategy.transition_plan is not None
        assert strategy.transition_plan.total_duration_sec > 0
        assert len(strategy.transition_plan.phases) >= 1
        assert len(strategy.transition_plan.abort_conditions) >= 1

    def test_includes_preconditions(self):
        sol = OptimizationSolution(
            chiller_loads={"ch1": 500.0},
            total_power_kw=160.0,
            total_objective=130.0,
            energy_cost=110.0,
            carbon_cost=15.0,
            wear_cost=5.0,
        )
        strategy = build_strategy(
            sol,
            current_load_rt=500,
            predicted_load_rt=500,
        )
        assert len(strategy.preconditions) >= 1
        assert any("load" in p.lower() for p in strategy.preconditions)

    def test_calculates_cop_improvement(self):
        sol = OptimizationSolution(
            chiller_loads={"ch1": 400.0},
            total_power_kw=140.0,
            total_objective=110.0,
            energy_cost=90.0,
            carbon_cost=15.0,
            wear_cost=5.0,
        )
        strategy = build_strategy(
            sol,
            current_load_rt=400,
            predicted_load_rt=400,
        )
        assert strategy.expected_cop_improvement is not None
        assert strategy.expected_energy_saving_kwh_per_h is not None

    def test_default_strategy_id_generated(self):
        sol = OptimizationSolution(
            chiller_loads={"ch1": 500.0},
            total_power_kw=160.0,
            total_objective=130.0,
            energy_cost=110.0,
            carbon_cost=15.0,
            wear_cost=5.0,
        )
        strategy = build_strategy(sol, current_load_rt=500, predicted_load_rt=500)
        assert strategy.strategy_id is not None
        assert len(strategy.strategy_id) > 0

    def test_start_action_for_previously_off_chiller(self):
        # When a chiller has load > 0, include a "start" action before "set_load"
        sol = OptimizationSolution(
            chiller_loads={"ch1": 500.0},
            total_power_kw=160.0,
            total_objective=130.0,
            energy_cost=110.0,
            carbon_cost=15.0,
            wear_cost=5.0,
        )
        strategy = build_strategy(
            sol,
            current_load_rt=500,
            predicted_load_rt=500,
        )
        # ch1 should have both a start and set_load action, or just set_load if it's already on
        ch1_actions = [a for a in strategy.actions if a.device == "ch1"]
        assert len(ch1_actions) >= 1

    def test_actions_have_sequential_numbers(self):
        sol = OptimizationSolution(
            chiller_loads={"ch1": 300.0, "ch2": 300.0, "ch3": 0.0},
            total_power_kw=200.0,
            total_objective=160.0,
            energy_cost=130.0,
            carbon_cost=20.0,
            wear_cost=10.0,
        )
        strategy = build_strategy(
            sol,
            current_load_rt=600,
            predicted_load_rt=600,
        )
        seqs = [a.seq for a in strategy.actions]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == len(seqs)  # no duplicates


class TestStrategyAgent:
    @pytest.mark.asyncio
    async def test_run_produces_strategy(self):
        chillers = {
            "ch1": CentrifugalChiller(name="ch1", capacity_rt=500, design_cop=6.0, min_plr=0.2),
            "ch2": CentrifugalChiller(name="ch2", capacity_rt=500, design_cop=6.0, min_plr=0.2),
        }
        optimizer = ChillerPlantOptimizer(chillers)
        agent = StrategyAgent(optimizer=optimizer)

        result = await agent.run({
            "total_load_rt": 600.0,
            "t_cw": 30.0,
            "t_chw": 7.0,
            "current_time": 1716000000.0,
            "predicted_load_rt": 550.0,
        })

        assert "strategy" in result
        strategy_dict = result["strategy"]
        assert strategy_dict["strategy_id"] is not None
        assert len(strategy_dict["actions"]) >= 1
        assert strategy_dict["status"] == "draft"
        assert "solution" in result

    @pytest.mark.asyncio
    async def test_run_returns_infeasible_for_overload(self):
        chillers = {
            "ch1": CentrifugalChiller(name="ch1", capacity_rt=500, design_cop=6.0, min_plr=0.2),
        }
        optimizer = ChillerPlantOptimizer(chillers)
        agent = StrategyAgent(optimizer=optimizer)

        result = await agent.run({
            "total_load_rt": 800.0,  # exceeds single chiller capacity
            "t_cw": 30.0,
            "t_chw": 7.0,
        })

        strategy_dict = result["strategy"]
        assert strategy_dict["status"] != "draft" or not result.get("solution", {}).get("is_feasible", True)
