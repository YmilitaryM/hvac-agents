import pytest
import numpy as np
from src.simulation.chiller import CentrifugalChiller


class TestCentrifugalChiller:
    @pytest.fixture
    def chiller(self):
        return CentrifugalChiller(
            name="chiller_1",
            capacity_rt=500,
            design_cop=6.0,
            design_chw_supply_temp=7.0,
            design_cw_entering_temp=30.0,
            min_plr=0.2,
        )

    def test_full_load_cop(self, chiller):
        cop = chiller.compute_cop(plr=1.0, t_chw=7.0, t_cw=30.0)
        assert abs(cop - 6.0) < 0.1

    def test_cop_decreases_with_high_condenser_temp(self, chiller):
        cop_cool = chiller.compute_cop(plr=1.0, t_chw=7.0, t_cw=30.0)
        cop_hot = chiller.compute_cop(plr=1.0, t_chw=7.0, t_cw=35.0)
        assert cop_hot < cop_cool

    def test_cop_increases_with_higher_chw_temp(self, chiller):
        cop_low = chiller.compute_cop(plr=1.0, t_chw=5.0, t_cw=30.0)
        cop_high = chiller.compute_cop(plr=1.0, t_chw=9.0, t_cw=30.0)
        assert cop_high > cop_low

    def test_cop_curve_has_peak(self, chiller):
        cops = [chiller.compute_cop(plr=p, t_chw=7.0, t_cw=30.0)
                for p in np.linspace(0.3, 1.0, 8)]
        peak_idx = np.argmax(cops)
        assert 1 <= peak_idx <= 6

    def test_below_surge_boundary_returns_zero(self, chiller):
        cop = chiller.compute_cop(plr=0.15, t_chw=7.0, t_cw=30.0)
        assert cop == 0.0

    def test_surge_boundary_increases_with_tcw(self, chiller):
        boundary_cool = chiller.surge_boundary(t_cw=28.0)
        boundary_hot = chiller.surge_boundary(t_cw=35.0)
        assert boundary_hot > boundary_cool

    def test_power_calculation(self, chiller):
        load_rt = 375
        cop = chiller.compute_cop(plr=0.75, t_chw=7.0, t_cw=30.0)
        expected_power = (load_rt * 3.517) / cop
        power = chiller.compute_power_kw(load_rt=load_rt, t_chw=7.0, t_cw=30.0)
        assert abs(power - expected_power) < 0.1

    def test_capacity_range(self, chiller):
        min_cap = chiller.min_capacity_rt(t_cw=30.0)
        max_cap = chiller.max_capacity_rt
        assert min_cap == 100.0
        assert max_cap == 500.0
