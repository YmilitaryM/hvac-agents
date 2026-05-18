"""Tests for Report Generator."""

import pytest
from src.reports.generator import generate_daily_report, DailyReport


class TestGenerateDailyReport:
    def test_generate_daily_report_empty(self):
        """Empty inputs -> report with zero KPIs"""
        report = generate_daily_report([], [])
        assert isinstance(report, DailyReport)
        assert report.kpis is not None
        assert report.kpis.average_cop == 0.0
        assert report.kpis.num_strategies_executed == 0

    def test_generate_daily_report_with_data(self):
        """Snapshots + memory -> populated report"""
        snapshots = [
            {"total_cooling_load_rt": 500, "total_power_kw": 200},
            {"total_cooling_load_rt": 300, "total_power_kw": 120},
        ]
        memory_entries = [
            {
                "execution_status": "completed",
                "strategy_id": "s1",
                "trigger_type": "load_change",
                "cop_improvement": 0.05,
                "energy_saving_kwh": 100,
                "safety_passed": True,
            },
        ]
        report = generate_daily_report(
            snapshots, memory_entries, date="2025-01-15"
        )
        assert report.date == "2025-01-15"
        assert report.kpis is not None
        assert report.kpis.average_cop > 0
        assert report.kpis.num_strategies_executed == 1
        assert len(report.strategies_executed) == 1
        assert report.strategies_executed[0]["strategy_id"] == "s1"

    def test_report_includes_recommendations(self):
        """Low COP -> recommendations generated"""
        snapshots = [
            {"total_cooling_load_rt": 100, "total_power_kw": 80},
            # COP = (100*3.517)/80 = 4.396, which is < 4.5
        ]
        report = generate_daily_report(snapshots, [], design_cop=6.0)
        assert len(report.recommendations) > 0
        assert any(
            "COP below 4.5" in r or "maintenance" in r.lower()
            for r in report.recommendations
        )

    def test_report_includes_alerts(self):
        """Aborted strategies -> alerts populated"""
        memory_entries = [
            {
                "execution_status": "aborted",
                "strategy_id": "s_bad",
                "trigger_type": "load_change",
                "cop_improvement": 0,
                "energy_saving_kwh": 0,
                "safety_passed": True,
            },
            {
                "execution_status": "completed",
                "strategy_id": "s_good",
                "trigger_type": "scheduled",
                "cop_improvement": 0.03,
                "energy_saving_kwh": 50,
                "safety_passed": False,
            },
        ]
        report = generate_daily_report([], memory_entries)
        assert len(report.alerts_summary) >= 2
        assert any("aborted" in a for a in report.alerts_summary)
        assert any("safety" in a for a in report.alerts_summary)

    def test_report_no_recommendations_when_good(self):
        """Good COP -> 'no actions required'"""
        snapshots = [
            {"total_cooling_load_rt": 300, "total_power_kw": 150},
            # COP = (300*3.517)/150 = 7.034 (good COP)
        ]
        memory_entries = [
            {
                "execution_status": "completed",
                "strategy_id": "s1",
                "trigger_type": "scheduled",
                "cop_improvement": 0.05,
                "energy_saving_kwh": 100,
                "safety_passed": True,
            },
        ]
        report = generate_daily_report(snapshots, memory_entries)
        assert "no actions required" in " ".join(
            r.lower() for r in report.recommendations
        )

    def test_report_summary_contains_key_metrics(self):
        """Summary string contains COP and rating"""
        snapshots = [
            {"total_cooling_load_rt": 300, "total_power_kw": 150},
        ]
        memory_entries = [
            {
                "execution_status": "completed",
                "strategy_id": "s1",
                "trigger_type": "scheduled",
                "cop_improvement": 0.05,
                "energy_saving_kwh": 100,
                "safety_passed": True,
            },
        ]
        report = generate_daily_report(snapshots, memory_entries)
        assert "COP" in report.summary
        assert "Energy Star Rating" in report.summary
        assert "Strategies" in report.summary

    def test_report_top_concerns_when_low_cop_vs_design(self):
        """COP well below design -> concern raised"""
        snapshots = [
            {"total_cooling_load_rt": 100, "total_power_kw": 100},
            # COP = (100*3.517)/100 = 3.517
            # cop_vs_design = 3.517/6.0 = 0.586 < 0.8
        ]
        report = generate_daily_report(snapshots, [], design_cop=6.0)
        assert len(report.top_concerns) > 0
        assert any(
            "efficiency gap" in c.lower() or "COP" in c
            for c in report.top_concerns
        )
