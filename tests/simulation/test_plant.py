import pytest
from src.simulation.chiller import CentrifugalChiller
from src.simulation.cooling_tower import CoolingTower
from src.simulation.pump import Pump
from src.simulation.plant import ChillerPlant


class TestChillerPlant:
    @pytest.fixture
    def plant(self):
        chillers = [
            CentrifugalChiller(name=f"chiller_{i+1}", capacity_rt=500)
            for i in range(3)
        ]
        towers = [
            CoolingTower(
                name=f"tower_{i+1}",
                design_heat_rejection_kw=500 * 3.517 * 1.3,
            )
            for i in range(3)
        ]
        chw_pumps = [Pump(name=f"chw_pump_{i+1}", rated_power_kw=37) for i in range(3)]
        cw_pumps = [Pump(name=f"cw_pump_{i+1}", rated_power_kw=30) for i in range(3)]
        return ChillerPlant(
            chillers=chillers, cooling_towers=towers,
            chw_pumps=chw_pumps, cw_pumps=cw_pumps,
        )

    def test_single_chiller_operation(self, plant):
        config = {
            "chiller_loads": {"chiller_1": 375},
            "chiller_t_chw": {"chiller_1": 7.0},
            "chiller_t_cw": {"chiller_1": 30.0},
            "tower_fan_speeds": {"tower_1": 50.0},
            "chw_pump_speeds": {"chw_pump_1": 45.0},
            "cw_pump_speeds": {"cw_pump_1": 40.0},
        }
        snap = plant.snapshot(config, outdoor_wb=26.0, outdoor_db=33.0)
        assert snap.total_cooling_load_rt == 375
        assert snap.system_cop > 0

    def test_two_chiller_operation(self, plant):
        config = {
            "chiller_loads": {"chiller_1": 300, "chiller_2": 300},
            "chiller_t_chw": {"chiller_1": 7.0, "chiller_2": 7.0},
            "chiller_t_cw": {"chiller_1": 30.0, "chiller_2": 30.0},
            "tower_fan_speeds": {"tower_1": 50.0, "tower_2": 50.0},
            "chw_pump_speeds": {"chw_pump_1": 45.0, "chw_pump_2": 45.0},
            "cw_pump_speeds": {"cw_pump_1": 40.0, "cw_pump_2": 40.0},
        }
        snap = plant.snapshot(config, outdoor_wb=26.0, outdoor_db=33.0)
        assert snap.total_cooling_load_rt == 600
        assert len(snap.running_chillers) == 2

    def test_below_surge_raises_error(self, plant):
        config = {
            "chiller_loads": {"chiller_1": 50},
            "chiller_t_chw": {"chiller_1": 7.0},
            "chiller_t_cw": {"chiller_1": 30.0},
            "tower_fan_speeds": {"tower_1": 50.0},
            "chw_pump_speeds": {"chw_pump_1": 45.0},
            "cw_pump_speeds": {"cw_pump_1": 40.0},
        }
        with pytest.raises(ValueError, match="surge"):
            plant.snapshot(config, outdoor_wb=26.0, outdoor_db=33.0)
