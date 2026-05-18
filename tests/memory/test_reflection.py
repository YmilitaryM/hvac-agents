import pytest
from src.memory.log import MemoryLog, MemoryEntry
from src.memory.reflection import reflect_on_history, ReflectionResult


def _make_entry(
    strategy_id: str,
    execution_status: str = "completed",
    safety_passed: bool = True,
    cop_improvement: float | None = 0.05,
    current_load_rt: float = 500.0,
    advocate_opinions: list | None = None,
) -> MemoryEntry:
    return MemoryEntry(
        timestamp=1000.0,
        strategy_id=strategy_id,
        trigger_type="scheduled",
        current_load_rt=current_load_rt,
        predicted_load_rt=480.0,
        cop_improvement=cop_improvement,
        execution_status=execution_status,
        safety_passed=safety_passed,
        advocate_opinions=advocate_opinions or [],
    )


class TestReflection:
    def test_empty_log(self):
        """Empty log returns single insight about no history."""
        log = MemoryLog()
        result = reflect_on_history(log)
        assert isinstance(result, ReflectionResult)
        assert len(result.insights) == 1
        assert "No execution history" in result.insights[0]

    def test_successful_log(self):
        """All successful log -> success_rate = 1.0."""
        log = MemoryLog()
        for i in range(5):
            log.add(_make_entry(f"s{i}"))
        result = reflect_on_history(log)
        assert result.success_rate == 1.0
        assert result.average_cop_improvement == 0.05
        assert any("Success rate: 100.0%" in ins for ins in result.insights)

    def test_mixed_log(self):
        """Mixed success/failure calculates success rate and identifies patterns."""
        log = MemoryLog()
        for i in range(4):
            log.add(_make_entry(f"s{i}"))  # success
        log.add(
            _make_entry("s4", execution_status="aborted", safety_passed=False)
        )  # failure
        result = reflect_on_history(log)
        assert result.success_rate == 0.8
        assert any("Average load at failure" in ins for ins in result.insights)
        # With 80% success rate (< 0.8 is threshold, but exactly 0.8 is not < 0.8)
        # So no "High failure rate" pattern for exactly 80%

    def test_cop_trend_positive(self):
        """Entries with increasing COP trend should detect positive trend."""
        log = MemoryLog()
        # 6 entries: first 3 with low COP, last 3 with higher COP
        for i in range(3):
            log.add(_make_entry(f"s{i}", cop_improvement=0.01))
        for i in range(3):
            log.add(_make_entry(f"s{i+3}", cop_improvement=0.10))
        result = reflect_on_history(log, lookback=6)
        assert any(
            "COP improvement trend is positive" in ins for ins in result.insights
        )

    def test_no_cop_data(self):
        """Entries without COP data are handled gracefully."""
        log = MemoryLog()
        for i in range(5):
            log.add(_make_entry(f"s{i}", cop_improvement=None))
        result = reflect_on_history(log)
        assert result.average_cop_improvement == 0.0
        assert any(
            "Average COP improvement: 0.0000" in ins for ins in result.insights
        )
