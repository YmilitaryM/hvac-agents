from datetime import datetime, timezone

from agent_service.carbon.carbon_market import GenericCarbonMarket
from agent_service.carbon.carbon_optimizer import CarbonOptimizer
from agent_service.carbon.cea_adapter import CEAAdapter
from agent_service.carbon.emission_calculator import EmissionCalculator
from agent_service.optimization.network_flow import (
    effective_capacity,
    estimate_delivery_loss,
)
from agent_service.optimization.station_dispatch import (
    StationStatus,
    inter_station_dispatch,
)


def test_inter_station_dispatch():
    stations = [
        StationStatus("s1", 500.0, 0.35, 200.0, 6.0, 0.1),
        StationStatus("s2", 300.0, 0.28, 100.0, 6.5, 0.08),
        StationStatus("s3", 200.0, 0.45, 50.0, 5.2, 0.12),
    ]
    result = inter_station_dispatch(stations, 400.0)
    # Cheapest station s2 gets allocated first
    assert result.stations["s2"] == 300.0
    assert result.stations["s1"] == 100.0
    assert result.stations["s3"] == 0.0
    assert result.unused_capacity == 600.0  # 1000 - 400


def test_inter_station_dispatch_over_capacity():
    stations = [StationStatus("s1", 100.0, 0.5, 0.0, 5.0, 0.1)]
    result = inter_station_dispatch(stations, 200.0)
    assert result.stations["s1"] == 100.0
    assert result.unused_capacity == -100.0  # negative = overload


def test_network_flow_delivery_loss():
    loss = estimate_delivery_loss(5.0, flow_temp=7.0, ambient_temp=30.0)
    assert loss > 0
    assert loss < 1.0  # less than 100% loss


def test_network_flow_effective_capacity():
    cap = effective_capacity(1000.0, 3.0)
    assert cap < 1000.0  # loss reduces capacity


def test_emission_calculator_from_power():
    tco2 = EmissionCalculator.from_power(500.0, 2.0, 0.50)
    assert tco2 == 0.5  # 500kW * 2h = 1MWh * 0.50 = 0.5 tCO2


def test_emission_calculator_from_cooling():
    tco2 = EmissionCalculator.from_cooling(100.0)
    assert tco2 == 6.5  # 100GJ * 0.065


def test_emission_calculator_from_fuel():
    tco2 = EmissionCalculator.from_fuel(1000.0, 3.0)
    assert tco2 == 3000.0


def test_generic_carbon_market():
    now = datetime.now(timezone.utc)
    m = GenericCarbonMarket("test", 100.0, 0.50, 1000.0, now, now)
    cost = m.emission_cost(500.0, 2.0)  # 1MWh -> 0.5 tCO2
    assert cost == 50.0  # 0.5 * 100
    assert m.allowance_remaining() == 999.5


def test_carbon_market_overage():
    now = datetime.now(timezone.utc)
    m = GenericCarbonMarket("test", 100.0, 0.50, 1.0, now, now)
    m.emission_cost(2000.0, 1.0)  # 2MWh -> 1.0 tCO2
    assert m.allowance_remaining() == 0.0
    cost = m.emission_cost(1000.0, 2.0)  # another 2MWh -> 1.0 tCO2 with overage
    # 1.0 * 100 (base) + 1.0 * 100 * 2.0 (overage penalty) = 300
    assert cost > 100.0


def test_carbon_market_purchase_deficit():
    now = datetime.now(timezone.utc)
    m = GenericCarbonMarket("test", 100.0, 0.50, 100.0, now, now)
    cost = m.purchase_deficit(10.0)
    assert cost == 1100.0  # 10 * 100 * 1.1


def test_cea_adapter():
    now = datetime.now(timezone.utc)
    adapter = CEAAdapter("south", 80.0, 500.0, now, now)
    assert adapter.emission_factor == 0.389
    assert adapter.carbon_price == 80.0
    allowance = CEAAdapter.cooling_allowance(100.0)
    assert allowance == 6.5


def test_carbon_optimizer():
    stations = [
        {"id": "s1", "capacity_rt": 500},
        {"id": "s2", "capacity_rt": 300},
        {"id": "s3", "capacity_rt": 200},
    ]
    alloc = CarbonOptimizer.optimal_carbon_allocation(stations, 1000.0)
    assert alloc["s1"] == 500.0
    assert alloc["s2"] == 300.0
    assert alloc["s3"] == 200.0


def test_carbon_optimizer_zero_capacity():
    stations = [{"id": "s1", "capacity_rt": 0}, {"id": "s2", "capacity_rt": 0}]
    alloc = CarbonOptimizer.optimal_carbon_allocation(stations, 100.0)
    assert alloc["s1"] == 50.0
    assert alloc["s2"] == 50.0
