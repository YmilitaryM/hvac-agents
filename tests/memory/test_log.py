import pytest
from src.memory.log import MemoryLog, MemoryEntry


class TestMemoryEntry:
    def test_create_entry(self):
        entry = MemoryEntry(
            timestamp=1000.0,
            strategy_id="strat_1",
            trigger_type="scheduled",
            current_load_rt=500,
            predicted_load_rt=480,
            cop_improvement=0.05,
            execution_status="completed",
        )
        assert entry.strategy_id == "strat_1"
        assert entry.cop_improvement == 0.05


class TestMemoryLog:
    @pytest.fixture
    def log(self):
        ml = MemoryLog(max_entries=100)
        for i in range(5):
            ml.add(
                MemoryEntry(
                    timestamp=float(i * 100),
                    strategy_id=f"strat_{i}",
                    trigger_type="scheduled",
                    current_load_rt=500.0,
                    predicted_load_rt=480.0,
                    cop_improvement=0.05 if i < 3 else -0.02,
                    execution_status="completed" if i < 4 else "aborted",
                    safety_passed=i < 4,
                )
            )
        return ml

    def test_add_and_retrieve(self, log):
        assert len(log) == 5

    def test_get_recent(self, log):
        recent = log.get_recent(3)
        assert len(recent) == 3
        assert recent[-1].strategy_id == "strat_4"

    def test_get_successful(self, log):
        successful = log.get_successful()
        assert len(successful) == 4

    def test_get_failures(self, log):
        failures = log.get_failures()
        assert len(failures) == 1
        assert failures[0].execution_status == "aborted"

    def test_max_entries_enforced(self):
        ml = MemoryLog(max_entries=3)
        for i in range(5):
            ml.add(
                MemoryEntry(
                    timestamp=float(i),
                    strategy_id=f"s{i}",
                    trigger_type="scheduled",
                    current_load_rt=100,
                    predicted_load_rt=100,
                )
            )
        assert len(ml) == 3
        assert ml.entries[0].strategy_id == "s2"

    def test_to_dict_list(self, log):
        dlist = log.to_dict_list()
        assert len(dlist) == 5
        assert "strategy_id" in dlist[0]

    def test_get_by_status(self, log):
        completed = log.get_by_status("completed")
        assert len(completed) == 4
        aborted = log.get_by_status("aborted")
        assert len(aborted) == 1
