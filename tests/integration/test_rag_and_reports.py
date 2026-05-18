"""Integration tests for RAG document retrieval and report generation."""

import json
import pytest

from src.rag.loader import chunk_text, DocumentChunk, load_text_document
from src.rag.retriever import DocumentStore, create_hvac_knowledge_base, RetrievalResult
from src.reports.kpi_calculator import (
    calculate_kpis,
    KPIResult,
    compute_cop,
    compute_eer,
    benchmark_against_standard,
)
from src.reports.generator import generate_daily_report, DailyReport
from src.reports.renderer import (
    render_report_json,
    render_report_markdown,
    render_report_csv,
)
from src.memory.log import MemoryEntry


# ---------------------------------------------------------------------------
# TestRAGIntegration
# ---------------------------------------------------------------------------

class TestRAGIntegration:
    """Document retrieval from HVAC knowledge base."""

    @pytest.fixture
    def kb(self):
        """Pre-built HVAC knowledge base."""
        return create_hvac_knowledge_base()

    def test_knowledge_base_not_empty(self, kb):
        """Knowledge base is pre-loaded with HVAC snippets."""
        assert len(kb) > 0
        assert len(kb) >= 8  # at least 8 snippets

    def test_search_surge_prevention(self, kb):
        """Search for 'surge prevention' returns relevant results."""
        results = kb.search("surge prevention", top_k=3)
        assert len(results) > 0

        # Results should be ranked by score
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

        # At least one result should mention surge
        surge_mentions = [
            r for r in results
            if "surge" in r.chunk.text.lower()
        ]
        assert len(surge_mentions) > 0

    def test_search_energy_efficiency_ashrae(self, kb):
        """Search for 'energy efficiency' returns ASHRAE results."""
        results = kb.search("energy efficiency ASHRAE", top_k=5)
        assert len(results) > 0

        # Should find ASHRAE standard content
        ashrae_results = [
            r for r in results
            if "ashrae" in r.chunk.source.lower()
               or "ashrae" in r.chunk.text.lower()
        ]
        assert len(ashrae_results) > 0

    def test_search_carbon_accounting(self, kb):
        """Search for carbon-related topics returns relevant results."""
        results = kb.search("carbon emissions trading", top_k=3)
        assert len(results) > 0

        # At least one result from carbon_accounting source
        carbon_results = [
            r for r in results
            if "carbon" in r.chunk.source.lower()
               or "carbon" in r.chunk.text.lower()
        ]
        assert len(carbon_results) > 0

    def test_search_returns_retrieval_result_objects(self, kb):
        """Search results are properly typed RetrievalResult objects."""
        results = kb.search("chiller", top_k=2)
        for r in results:
            assert isinstance(r, RetrievalResult)
            assert isinstance(r.chunk, DocumentChunk)
            assert 0.0 <= r.score <= 1.0
            assert r.rank >= 1
            assert r.chunk.text  # non-empty

    def test_search_with_min_score_threshold(self, kb):
        """Search with min_score filters out low-confidence results."""
        results_all = kb.search("pump", top_k=10, min_score=0.0)
        results_filtered = kb.search("pump", top_k=10, min_score=0.1)

        # Filtered should be <= all results
        assert len(results_filtered) <= len(results_all)

        # All filtered results should have score >= min_score
        for r in results_filtered:
            assert r.score >= 0.1

    def test_search_by_source(self, kb):
        """Search within a specific document source."""
        results = kb.search_by_source("ashrae_90.1", "chiller COP", top_k=3)
        for r in results:
            assert r.chunk.source == "ashrae_90.1"

    def test_search_no_results_for_irrelevant_query(self, kb):
        """Irrelevant queries may return low-score results or none."""
        results = kb.search("zzzxyznonexistent topic 12345", top_k=5)
        # Should return results but with very low scores (< 0.1)
        for r in results:
            assert r.score < 0.1

    def test_get_chunk_by_id(self, kb):
        """Retrieve a specific chunk by its ID."""
        # First search to get a chunk ID
        results = kb.search("surge", top_k=1)
        if results:
            chunk_id = results[0].chunk.chunk_id
            chunk = kb.get_chunk_by_id(chunk_id)
            assert chunk is not None
            assert chunk.chunk_id == chunk_id

    def test_document_store_clear(self, kb):
        """Clear removes all chunks."""
        assert len(kb) > 0
        kb.clear()
        assert len(kb) == 0
        results = kb.search("chiller")
        assert len(results) == 0

    def test_chunk_text_basic(self):
        """chunk_text splits text into overlapping chunks."""
        text = "This is sentence one. This is sentence two. This is sentence three. And a fourth sentence here."
        chunks = chunk_text(text, source="test", chunk_size=60, chunk_overlap=10)
        assert len(chunks) >= 1

        for c in chunks:
            assert isinstance(c, DocumentChunk)
            assert c.source == "test"
            assert c.chunk_id.startswith("test_chunk_")
            assert c.text  # non-empty

    def test_chunk_text_empty_input(self):
        """chunk_text handles empty input gracefully."""
        chunks = chunk_text("", source="test")
        assert len(chunks) == 0

        chunks2 = chunk_text("   ", source="test")
        assert len(chunks2) == 0

    def test_empty_store_search(self):
        """Empty store returns empty results on search."""
        store = DocumentStore()
        results = store.search("anything")
        assert len(results) == 0

    def test_document_store_add_and_search(self):
        """Adding chunks to store enables search."""
        store = DocumentStore()
        chunks = chunk_text("Centrifugal chillers use a vapor compression cycle for cooling.", source="test")
        store.add_chunks(chunks)

        results = store.search("centrifugal chiller")
        assert len(results) > 0
        assert results[0].score > 0.0


# ---------------------------------------------------------------------------
# TestReportGeneration
# ---------------------------------------------------------------------------

class TestReportGeneration:
    """Report generation from pipeline data."""

    def test_compute_cop(self):
        """COP = cooling output (kW) / power input (kW)."""
        # 500RT * 3.517 kW/RT = 1758.5 kW cooling
        # power = 300 kW -> COP = 5.86
        cop = compute_cop(500.0, 300.0)
        assert cop == pytest.approx(5.8617, rel=0.01)

        # Zero power -> COP = 0
        assert compute_cop(500.0, 0.0) == 0.0

    def test_compute_eer(self):
        """EER = COP * 3.412."""
        eer = compute_eer(500.0, 300.0)
        expected = 5.8617 * 3.412
        assert eer == pytest.approx(expected, rel=0.01)

    def test_benchmark_excellent_cop(self):
        """COP >= design_cop gets excellent assessment."""
        b = benchmark_against_standard(actual_cop=6.5, design_cop=6.0)
        assert b["cop_vs_design"] >= 1.0
        assert b["energy_star_rating"] >= 95.0
        assert "Excellent" in b["assessment"] or "exceeding" in b["assessment"].lower()

    def test_benchmark_poor_cop(self):
        """COP below ASHRAE minimum gets poor assessment."""
        b = benchmark_against_standard(actual_cop=3.0, design_cop=6.0, ashrae_minimum_cop=5.0)
        assert b["cop_vs_design"] < 0.8
        assert "Poor" in b["assessment"]

    def test_benchmark_good_cop(self):
        """COP near design gets good assessment."""
        b = benchmark_against_standard(actual_cop=5.7, design_cop=6.0)
        assert 0.9 <= b["cop_vs_design"] < 1.0
        assert "Good" in b["assessment"]

    def test_calculate_kpis_from_snapshots(self):
        """KPIs are calculated correctly from snapshots."""
        snapshots = [
            {"total_cooling_load_rt": 500.0, "total_power_kw": 300.0},
            {"total_cooling_load_rt": 600.0, "total_power_kw": 340.0},
            {"total_cooling_load_rt": 400.0, "total_power_kw": 250.0},
        ]

        memory_entries = [
            {
                "strategy_id": "s1", "execution_status": "completed",
                "cop_improvement": 0.10, "energy_saving_kwh": 50.0,
                "carbon_saving_kg": 25.0,
            },
            {
                "strategy_id": "s2", "execution_status": "aborted",
                "cop_improvement": 0.0, "energy_saving_kwh": 0.0,
                "carbon_saving_kg": 0.0,
            },
        ]

        kpis = calculate_kpis(
            snapshots=snapshots,
            memory_entries=memory_entries,
            electricity_price=0.8,
            carbon_price=0.08,
            design_cop=6.0,
        )

        assert isinstance(kpis, KPIResult)

        # Average load: (500+600+400)/3 = 500 RT
        # Average power: (300+340+250)/3 = 296.67 kW
        # COP = (500*3.517)/296.67 = ~5.93
        assert kpis.average_cop == pytest.approx(5.93, rel=0.05)
        assert kpis.num_strategies_executed == 1
        assert kpis.num_strategies_aborted == 1
        assert kpis.average_cop_improvement == pytest.approx(0.05, rel=0.01)
        assert kpis.total_energy_saved_kwh == 50.0
        assert kpis.total_carbon_saved_kg == 25.0

    def test_calculate_kpis_empty_input(self):
        """KPIs with no data return zeros."""
        kpis = calculate_kpis(snapshots=[], memory_entries=[])
        assert kpis.average_cop == 0.0
        assert kpis.total_power_consumption_kwh == 0.0
        assert kpis.num_strategies_executed == 0

    def test_generate_daily_report(self):
        """Daily report includes KPIs, summary, and recommendations."""
        snapshots = [
            {"total_cooling_load_rt": 500.0, "total_power_kw": 300.0},
            {"total_cooling_load_rt": 600.0, "total_power_kw": 350.0},
        ]

        memory_entries = [
            {
                "strategy_id": "s1", "execution_status": "completed",
                "trigger_type": "scheduled", "cop_improvement": 0.08,
                "energy_saving_kwh": 40.0, "safety_passed": True,
            },
        ]

        report = generate_daily_report(
            snapshots=snapshots,
            memory_entries=memory_entries,
            date="2026-05-19",
            electricity_price=0.8,
            carbon_price=0.08,
            design_cop=6.0,
        )

        assert isinstance(report, DailyReport)
        assert report.date == "2026-05-19"
        assert report.kpis is not None
        assert len(report.summary) > 0
        assert "Average COP" in report.summary
        assert len(report.strategies_executed) == 1
        assert len(report.recommendations) > 0

    def test_daily_report_with_alerts(self):
        """Report captures alerts from aborted strategies."""
        snapshots = [
            {"total_cooling_load_rt": 500.0, "total_power_kw": 300.0},
        ]

        memory_entries = [
            {
                "strategy_id": "s_fail", "execution_status": "aborted",
                "trigger_type": "fault", "cop_improvement": 0.0,
                "energy_saving_kwh": 0.0, "safety_passed": False,
            },
        ]

        report = generate_daily_report(
            snapshots=snapshots,
            memory_entries=memory_entries,
            date="2026-05-19",
        )

        assert len(report.alerts_summary) >= 1
        # Should mention the aborted strategy
        abort_alert = [a for a in report.alerts_summary if "aborted" in a.lower() or "safety" in a.lower()]
        assert len(abort_alert) >= 1

    def test_render_report_json(self):
        """JSON renderer produces valid JSON."""
        snapshots = [
            {"total_cooling_load_rt": 500.0, "total_power_kw": 300.0},
        ]
        memory_entries = [
            {
                "strategy_id": "s1", "execution_status": "completed",
                "trigger_type": "scheduled", "cop_improvement": 0.1,
                "energy_saving_kwh": 50.0, "safety_passed": True,
            },
        ]
        report = generate_daily_report(
            snapshots=snapshots, memory_entries=memory_entries, date="2026-05-19",
        )

        json_str = render_report_json(report)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Should parse as valid JSON
        parsed = json.loads(json_str)
        assert parsed["report_type"] == "daily"
        assert parsed["date"] == "2026-05-19"
        assert "kpis" in parsed
        assert "average_cop" in parsed["kpis"]

    def test_render_report_markdown(self):
        """Markdown renderer produces well-formed output."""
        snapshots = [
            {"total_cooling_load_rt": 500.0, "total_power_kw": 300.0},
        ]
        memory_entries = []
        report = generate_daily_report(
            snapshots=snapshots, memory_entries=memory_entries, date="2026-05-19",
        )

        md = render_report_markdown(report)
        assert isinstance(md, str)
        assert len(md) > 0

        # Should start with a heading
        assert md.startswith("# ")
        # Should contain KPI table
        assert "## KPIs" in md
        assert "| Metric | Value |" in md
        # Should contain recommendations
        assert "## Recommendations" in md

    def test_render_report_csv(self):
        """CSV renderer produces valid CSV output."""
        snapshots = [
            {"total_cooling_load_rt": 500.0, "total_power_kw": 300.0},
        ]
        memory_entries = []
        report = generate_daily_report(
            snapshots=snapshots, memory_entries=memory_entries, date="2026-05-19",
        )

        csv_str = render_report_csv(report)
        assert isinstance(csv_str, str)
        assert len(csv_str) > 0

        # Should have header row and data row
        lines = csv_str.strip().split("\n")
        assert len(lines) == 2  # header + data

        # Date should be in the data row
        assert "2026-05-19" in csv_str

    def test_render_csv_without_kpis(self):
        """CSV renderer handles report without KPIs."""
        report = DailyReport(date="2026-05-19")
        csv_str = render_report_csv(report)
        assert "2026-05-19" in csv_str
        # All metric values should be 0
        parts = csv_str.strip().split("\n")[1].split(",")
        # date should be first field
        assert parts[0] == "2026-05-19"

    def test_all_three_formats_produce_output(self):
        """JSON, Markdown, and CSV all produce non-empty output."""
        snapshots = [
            {"total_cooling_load_rt": 600.0, "total_power_kw": 350.0},
            {"total_cooling_load_rt": 550.0, "total_power_kw": 330.0},
        ]
        memory_entries = [
            {
                "strategy_id": "s1", "execution_status": "completed",
                "trigger_type": "scheduled", "cop_improvement": 0.12,
                "energy_saving_kwh": 60.0, "safety_passed": True,
            },
        ]

        report = generate_daily_report(
            snapshots=snapshots, memory_entries=memory_entries, date="2026-05-19",
        )

        json_output = render_report_json(report)
        md_output = render_report_markdown(report)
        csv_output = render_report_csv(report)

        assert len(json_output) > 0
        assert len(md_output) > 0
        assert len(csv_output) > 0

        # All should contain the date
        for output in (json_output, md_output, csv_output):
            assert "2026-05-19" in output

    def test_daily_report_positive_recommendation_when_normal(self):
        """Normal operation yields 'no actions required' recommendation."""
        snapshots = [
            {"total_cooling_load_rt": 500.0, "total_power_kw": 280.0},
            {"total_cooling_load_rt": 500.0, "total_power_kw": 280.0},
            {"total_cooling_load_rt": 500.0, "total_power_kw": 280.0},
        ]
        memory_entries = [
            {
                "strategy_id": "s1", "execution_status": "completed",
                "trigger_type": "scheduled", "cop_improvement": 0.15,
                "energy_saving_kwh": 80.0, "safety_passed": True,
            },
        ]

        report = generate_daily_report(
            snapshots=snapshots, memory_entries=memory_entries, date="2026-05-19",
        )

        assert "no actions required" in " ".join(report.recommendations).lower()
