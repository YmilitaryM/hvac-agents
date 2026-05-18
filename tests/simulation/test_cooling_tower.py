import pytest
from src.simulation.cooling_tower import CoolingTower


class TestCoolingTower:
    @pytest.fixture
    def tower(self):
        return CoolingTower(
            name="tower_1",
            design_heat_rejection_kw=500 * 3.517 * 1.3,
            design_flow_lps=80,
            design_wb_temp=28.0,
            design_approach=4.0,
        )

    def test_approach_increases_with_low_fan_speed(self, tower):
        t_out_full = tower.compute_outlet_temp(
            heat_load_kw=2000, water_flow_lps=80,
            fan_speed_hz=50, outdoor_wb=26.0,
        )
        t_out_low = tower.compute_outlet_temp(
            heat_load_kw=2000, water_flow_lps=80,
            fan_speed_hz=25, outdoor_wb=26.0,
        )
        assert t_out_low > t_out_full

    def test_outlet_temp_limited_by_wet_bulb(self, tower):
        t_out = tower.compute_outlet_temp(
            heat_load_kw=500, water_flow_lps=80,
            fan_speed_hz=50, outdoor_wb=26.0,
        )
        assert t_out >= 26.0

    def test_fan_power(self, tower):
        p_50 = tower.compute_fan_power_kw(50)
        p_25 = tower.compute_fan_power_kw(25)
        assert abs(p_25 - p_50 * (25/50)**3) < 0.1
