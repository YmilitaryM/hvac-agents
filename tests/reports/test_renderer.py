"""Tests for Report Renderer."""

import json
import pytest
from src.reports.generator import generate_daily_report, DailyReport
from src.reports.renderer import (
    render_report_json,
    render_report_markdown,
    render_report_csv,
)


class TestRenderJson:
    def test_render_json(self):
        """Produces valid JSON with expected keys"""
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
        report = generate_daily_report(
            snapshots, memory_entries, date="2025-01-15"
        )
        output = render_report_json(report)

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["report_type"] == "daily"
        assert parsed["date"] == "2025-01-15"
        assert "kpis" in parsed
        assert "summary" in parsed
        assert "recommendations" in parsed
        assert "alerts" in parsed

    def test_render_json_roundtrip(self):
        """JSON output can be parsed back to dict"""
        report = generate_daily_report(
            [
                {"total_cooling_load_rt": 300, "total_power_kw": 150},
            ],
            [],
            date="2025-01-15",
        )
        output = render_report_json(report)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        assert parsed["date"] == report.date
        assert parsed["summary"] == report.summary
        assert parsed["kpis"]["average_cop"] == report.kpis.average_cop


class TestRenderMarkdown:
    def test_render_markdown(self):
        """Contains markdown headers and KPI table"""
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
        report = generate_daily_report(
            snapshots, memory_entries, date="2025-01-15"
        )
        output = render_report_markdown(report)

        assert "# HVAC Chiller Plant Daily Report" in output
        assert "## Summary" in output
        assert "## KPIs" in output
        assert "| Metric | Value |" in output
        assert "| Average COP |" in output


class TestRenderCsv:
    def test_render_csv(self):
        """Contains CSV header and data row"""
        snapshots = [
            {"total_cooling_load_rt": 300, "total_power_kw": 150},
        ]
        report = generate_daily_report(snapshots, [], date="2025-01-15")
        output = render_report_csv(report)

        assert "date,cop,eer,energy_star" in output
        assert "2025-01-15" in output
        lines = output.strip().split("\n")
        assert len(lines) >= 1  # at least header


class TestRenderEmptyReport:
    def test_render_empty_json(self):
        """JSON handles empty report"""
        report = generate_daily_report([], [])
        output = render_report_json(report)
        parsed = json.loads(output)
        assert "kpis" in parsed
        assert parsed["kpis"]["average_cop"] == 0.0
        assert parsed["kpis"]["num_strategies_executed"] == 0

    def test_render_empty_markdown(self):
        """Markdown handles empty report"""
        report = generate_daily_report([], [])
        output = render_report_markdown(report)
        assert "# HVAC Chiller Plant Daily Report" in output
        assert "## Summary" in output

    def test_render_empty_csv(self):
        """CSV handles empty report"""
        report = generate_daily_report([], [])
        output = render_report_csv(report)
        assert "date,cop" in output
        lines = output.strip().split("\n")
        assert len(lines) >= 1
