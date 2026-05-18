"""Tests for KPI Calculator."""

import pytest
from src.reports.kpi_calculator import (
    compute_cop,
    compute_eer,
    compute_carbon_intensity,
    benchmark_against_standard,
    calculate_kpis,
    KPIResult,
    KW_PER_RT,
)


class TestComputeCop:
    def test_compute_cop_normal(self):
        """500RT load, 100kW -> COP = (500*3.517)/100 = 17.585"""
        cop = compute_cop(cooling_load_rt=500, power_kw=100)
        assert cop == pytest.approx(17.585, rel=0.001)

    def test_compute_cop_zero_power(self):
        """power=0 -> COP=0"""
        cop = compute_cop(cooling_load_rt=500, power_kw=0)
        assert cop == 0.0

    def test_compute_cop_negative_power(self):
        """Negative power -> COP=0"""
        cop = compute_cop(cooling_load_rt=500, power_kw=-10)
        assert cop == 0.0


class TestComputeEer:
    def test_compute_eer(self):
        """COP=5.0 -> EER = 5.0 * 3.412 = 17.06"""
        # Choose load_rt and power_kw to produce COP = 5.0
        # COP = (load_rt * 3.517) / power_kw = 5.0
        # power_kw = (load_rt * 3.517) / 5.0
        # For load_rt = 500: power_kw = (500 * 3.517) / 5.0 = 351.7
        eer = compute_eer(cooling_load_rt=500, power_kw=351.7)
        assert eer == pytest.approx(17.06, rel=0.01)

    def test_compute_eer_zero_power(self):
        """Zero power -> EER = 0"""
        eer = compute_eer(cooling_load_rt=500, power_kw=0)
        assert eer == 0.0


class TestComputeCarbonIntensity:
    def test_compute_carbon_intensity(self):
        """1000 kWh, 500 kg -> 0.5"""
        ci = compute_carbon_intensity(1000, 500)
        assert ci == 0.5

    def test_compute_carbon_intensity_zero_power(self):
        """Zero power -> 0"""
        ci = compute_carbon_intensity(0, 500)
        assert ci == 0.0

    def test_compute_carbon_intensity_negative_power(self):
        """Negative power -> 0"""
        ci = compute_carbon_intensity(-100, 50)
        assert ci == 0.0


class TestBenchmarkAgainstStandard:
    def test_benchmark_excellent(self):
        """COP=6.5, design=6.0 -> energy_star >= 95"""
        result = benchmark_against_standard(actual_cop=6.5, design_cop=6.0)
        assert result["energy_star_rating"] >= 95
        assert "Excellent" in result["assessment"]

    def test_benchmark_poor(self):
        """COP=4.0, design=6.0 -> energy_star < 50"""
        result = benchmark_against_standard(actual_cop=4.0, design_cop=6.0)
        assert result["energy_star_rating"] < 50
        assert "Poor" in result["assessment"]

    def test_benchmark_adequate(self):
        """COP=5.5, design=6.0 -> assessment includes Adequate or Good"""
        result = benchmark_against_standard(actual_cop=5.5, design_cop=6.0)
        assert (
            "Adequate" in result["assessment"]
            or "Good" in result["assessment"]
        )

    def test_benchmark_perfect(self):
        """COP exactly equals design -> Excellent"""
        result = benchmark_against_standard(actual_cop=6.0, design_cop=6.0)
        assert result["cop_vs_design"] == pytest.approx(1.0)
        assert "Excellent" in result["assessment"]

    def test_benchmark_zero_design_cop(self):
        """Design COP zero -> does not crash"""
        result = benchmark_against_standard(actual_cop=5.0, design_cop=0.0)
        assert "energy_star_rating" in result


class TestCalculateKpis:
    def test_calculate_kpis_empty(self):
        """Empty lists -> default KPIResult"""
        result = calculate_kpis([], [])
        assert isinstance(result, KPIResult)
        assert result.average_cop == 0.0
        assert result.average_eer == 0.0
        assert result.num_strategies_executed == 0
        assert result.num_strategies_aborted == 0

    def test_calculate_kpis_with_data(self):
        """2 snapshots + 2 memory entries -> correct aggregations"""
        snapshots = [
            {"total_cooling_load_rt": 500, "total_power_kw": 200},
            {"total_cooling_load_rt": 300, "total_power_kw": 120},
        ]
        memory_entries = [
            {
                "execution_status": "completed",
                "cop_improvement": 0.05,
                "energy_saving_kwh": 100,
                "carbon_saving_kg": 50,
            },
            {
                "execution_status": "aborted",
                "cop_improvement": -0.02,
                "energy_saving_kwh": 0,
                "carbon_saving_kg": 0,
            },
        ]
        result = calculate_kpis(snapshots, memory_entries)

        # Total cooling: (500+300)*3.517 = 2813.6 kWh
        assert result.total_cooling_energy_kwh == pytest.approx(2813.6, rel=0.001)
        # Total power: 200+120 = 320 kWh
        assert result.total_power_consumption_kwh == 320.0
        # COP = total_cooling_kw / total_power_kw = 2813.6/320 = 8.7925
        assert result.average_cop == pytest.approx(8.7925, rel=0.01)
        # Strategies: 1 completed, 1 aborted
        assert result.num_strategies_executed == 1
        assert result.num_strategies_aborted == 1
        # Average cop improvement: (0.05 + (-0.02))/2 = 0.015
        assert result.average_cop_improvement == pytest.approx(0.015)
        # Energy saved: 100 + 0 = 100
        assert result.total_energy_saved_kwh == 100.0
        # Carbon saved: 50 + 0 = 50
        assert result.total_carbon_saved_kg == 50.0

    def test_calculate_kpis_cost_saved(self):
        """Energy saved * price + carbon saved * carbon_price = cost saved"""
        snapshots = [
            {"total_cooling_load_rt": 500, "total_power_kw": 200},
        ]
        memory_entries = [
            {
                "execution_status": "completed",
                "cop_improvement": 0.05,
                "energy_saving_kwh": 100,
                "carbon_saving_kg": 50,
            },
        ]
        result = calculate_kpis(
            snapshots,
            memory_entries,
            electricity_price=0.8,
            carbon_price=0.08,
        )
        expected_cost_saved = 100 * 0.8 + 50 * 0.08  # 80 + 4 = 84
        assert result.total_cost_saved == pytest.approx(expected_cost_saved)

    def test_calculate_kpis_carbon_emissions(self):
        """Verify carbon emissions calculation"""
        snapshots = [
            {"total_cooling_load_rt": 200, "total_power_kw": 100},
        ]
        result = calculate_kpis(snapshots, [])
        # 100 kWh * 0.5 kgCO2/kWh = 50 kg
        assert result.total_carbon_emissions_kg == 50.0

    def test_calculate_kpis_prices_affect_cost(self):
        """Different electricity and carbon prices produce different costs"""
        snapshots = [
            {"total_cooling_load_rt": 200, "total_power_kw": 100},
        ]
        result_default = calculate_kpis(snapshots, [])
        result_high = calculate_kpis(
            snapshots, [], electricity_price=1.6, carbon_price=0.16
        )
        # Higher prices -> roughly double the costs
        assert result_high.total_energy_cost > result_default.total_energy_cost
        assert result_high.total_carbon_cost > result_default.total_carbon_cost

    def test_calculate_kpis_ignores_none_values(self):
        """Memory entries with None values should not crash"""
        snapshots = [
            {"total_cooling_load_rt": 500, "total_power_kw": 200},
        ]
        memory_entries = [
            {
                "execution_status": "completed",
                "cop_improvement": None,
                "energy_saving_kwh": None,
                "carbon_saving_kg": None,
            },
        ]
        result = calculate_kpis(snapshots, memory_entries)
        assert result.average_cop_improvement == 0.0
        assert result.total_energy_saved_kwh == 0.0
        assert result.total_carbon_saved_kg == 0.0

    def test_calculate_kpis_with_periods(self):
        """period_start and period_end are passed through"""
        result = calculate_kpis(
            [], [], period_start=1000.0, period_end=2000.0
        )
        assert result.period_start == 1000.0
        assert result.period_end == 2000.0
