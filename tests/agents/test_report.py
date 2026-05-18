"""Tests for Report Agent."""

import json
import pytest
from src.agents.report import ReportAgent


class TestReportAgent:
    @pytest.mark.asyncio
    async def test_report_agent_json(self):
        """run() with format='json' -> valid JSON string"""
        agent = ReportAgent()
        result = await agent.run({
            "snapshots": [
                {"total_cooling_load_rt": 300, "total_power_kw": 150},
            ],
            "memory_entries": [
                {
                    "execution_status": "completed",
                    "strategy_id": "s1",
                    "trigger_type": "scheduled",
                    "cop_improvement": 0.05,
                    "energy_saving_kwh": 100,
                    "safety_passed": True,
                },
            ],
            "date": "2025-01-15",
            "format": "json",
        })

        assert result["format"] == "json"
        assert "rendered" in result
        assert "report" in result

        # Validate rendered is valid JSON
        parsed = json.loads(result["rendered"])
        assert parsed["date"] == "2025-01-15"
        assert "kpis" in parsed

        # Validate report dict
        assert result["report"]["date"] == "2025-01-15"
        assert "kpis" in result["report"]

    @pytest.mark.asyncio
    async def test_report_agent_markdown(self):
        """run() with format='markdown' -> contains markdown"""
        agent = ReportAgent()
        result = await agent.run({
            "snapshots": [
                {"total_cooling_load_rt": 300, "total_power_kw": 150},
            ],
            "memory_entries": [],
            "date": "2025-01-15",
            "format": "markdown",
        })

        assert result["format"] == "markdown"
        rendered = result["rendered"]
        assert "# HVAC Chiller Plant Daily Report" in rendered
        assert "## Summary" in rendered
        assert "## KPIs" in rendered

    @pytest.mark.asyncio
    async def test_report_agent_csv(self):
        """run() with format='csv' -> contains CSV"""
        agent = ReportAgent()
        result = await agent.run({
            "snapshots": [
                {"total_cooling_load_rt": 300, "total_power_kw": 150},
            ],
            "memory_entries": [],
            "date": "2025-01-15",
            "format": "csv",
        })

        assert result["format"] == "csv"
        rendered = result["rendered"]
        assert "date,cop,eer,energy_star" in rendered
        assert "2025-01-15" in rendered

    @pytest.mark.asyncio
    async def test_report_agent_empty_input(self):
        """Empty snapshots -> still produces report"""
        agent = ReportAgent()
        result = await agent.run({
            "snapshots": [],
            "memory_entries": [],
            "date": "2025-01-15",
            "format": "json",
        })

        assert "rendered" in result
        assert "report" in result
        report = result["report"]
        assert report["kpis"]["average_cop"] == 0.0
        assert report["kpis"]["num_strategies_executed"] == 0

    @pytest.mark.asyncio
    async def test_report_agent_daily_vs_monthly(self):
        """Both periods produce valid reports"""
        agent = ReportAgent()
        input_data = {
            "snapshots": [
                {"total_cooling_load_rt": 300, "total_power_kw": 150},
            ],
            "memory_entries": [],
            "date": "2025-01-15",
            "format": "json",
        }

        daily_result = await agent.run({**input_data, "report_period": "daily"})
        assert daily_result["report"]["date"] == "2025-01-15"
        parsed_daily = json.loads(daily_result["rendered"])
        assert parsed_daily["report_type"] == "daily"

        monthly_result = await agent.run({**input_data, "report_period": "monthly"})
        assert monthly_result["report"]["date"] == "2025-01-15"
        parsed_monthly = json.loads(monthly_result["rendered"])
        assert parsed_monthly["report_type"] == "daily"  # monthly uses same report type for now

    @pytest.mark.asyncio
    async def test_report_agent_default_format(self):
        """Default format is json when not specified"""
        agent = ReportAgent()
        result = await agent.run({
            "snapshots": [
                {"total_cooling_load_rt": 300, "total_power_kw": 150},
            ],
            "memory_entries": [],
            "date": "2025-01-15",
        })
        assert result["format"] == "json"
        # Should still be valid JSON
        json.loads(result["rendered"])

    @pytest.mark.asyncio
    async def test_report_agent_custom_prices(self):
        """Custom electricity and carbon prices affect costs"""
        agent = ReportAgent()
        result_default = await agent.run({
            "snapshots": [
                {"total_cooling_load_rt": 200, "total_power_kw": 100},
            ],
            "memory_entries": [],
            "date": "2025-01-15",
        })
        result_high = await agent.run({
            "snapshots": [
                {"total_cooling_load_rt": 200, "total_power_kw": 100},
            ],
            "memory_entries": [],
            "date": "2025-01-15",
            "electricity_price": 1.6,
            "carbon_price": 0.16,
        })
        assert result_high["report"]["kpis"]["total_energy_cost"] > result_default["report"]["kpis"]["total_energy_cost"]
