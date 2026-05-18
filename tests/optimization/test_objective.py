import pytest
from src.optimization.objective import (
    compute_energy_cost,
    compute_carbon_cost,
    compute_wear_cost,
    total_objective,
)


class TestEnergyCost:
    def test_energy_cost_calculation(self):
        total_power_kw = 500.0
        price_per_kwh = 0.8
        duration_hours = 1.0
        cost = compute_energy_cost(total_power_kw, price_per_kwh, duration_hours)
        assert abs(cost - 400.0) < 0.01  # 500 * 0.8 * 1.0 = 400

    def test_energy_cost_zero_power(self):
        cost = compute_energy_cost(0.0, 0.8, 1.0)
        assert cost == 0.0


class TestCarbonCost:
    def test_carbon_cost_calculation(self):
        total_power_kw = 500.0
        grid_carbon_intensity = 0.5  # kgCO2/kWh
        carbon_price = 0.08  # yuan/kgCO2
        duration_hours = 1.0
        cost = compute_carbon_cost(
            total_power_kw, grid_carbon_intensity, carbon_price, duration_hours
        )
        expected = 500 * 0.5 * 0.08 * 1.0  # = 20.0
        assert abs(cost - expected) < 0.01

    def test_carbon_cost_zero_emission(self):
        cost = compute_carbon_cost(500.0, 0.0, 0.08, 1.0)
        assert cost == 0.0


class TestWearCost:
    def test_no_starts_no_cost(self):
        cost = compute_wear_cost(
            start_actions={"chiller_1": 0, "chiller_2": 0},
            wear_costs={"chiller": 150.0, "pump": 30.0},
        )
        assert cost == 0.0

    def test_wear_cost_accumulation(self):
        cost = compute_wear_cost(
            start_actions={"chiller_1": 2, "pump_1": 3},
            wear_costs={"chiller": 150.0, "pump": 30.0},
        )
        expected = 2 * 150.0 + 3 * 30.0  # = 390.0
        assert abs(cost - expected) < 0.01


class TestTotalObjective:
    def test_total_objective_sum(self):
        energy = 400.0
        carbon = 20.0
        wear = 390.0
        total = total_objective(energy, carbon, wear)
        assert abs(total - 810.0) < 0.01

    def test_total_objective_with_weights(self):
        total = total_objective(
            energy_cost=400.0,
            carbon_cost=20.0,
            wear_cost=390.0,
            w_energy=1.0,
            w_carbon=2.0,
            w_wear=0.5,
        )
        expected = 1.0 * 400 + 2.0 * 20 + 0.5 * 390  # = 635.0
        assert abs(total - expected) < 0.01
