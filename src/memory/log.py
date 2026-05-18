"""Memory Log -- stores strategy execution records for reflection and learning."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    """A single memory entry recording a strategy execution."""

    timestamp: float
    strategy_id: str
    trigger_type: str
    current_load_rt: float
    predicted_load_rt: float
    actions: List[Dict[str, Any]] = field(default_factory=list)
    cop_improvement: Optional[float] = None
    energy_saving_kwh: Optional[float] = None
    carbon_saving_kg: Optional[float] = None
    advocate_opinions: List[Dict[str, Any]] = field(default_factory=list)
    arbitration_decision: str = ""
    execution_status: str = "completed"
    safety_passed: bool = True
    notes: str = ""


class MemoryLog:
    """Stores strategy execution records with retrieval capabilities."""

    def __init__(self, max_entries: int = 1000):
        self.entries: List[MemoryEntry] = []
        self.max_entries = max_entries

    def add(self, entry: MemoryEntry) -> None:
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        return self.entries[-n:]

    def get_by_status(self, status: str) -> List[MemoryEntry]:
        return [e for e in self.entries if e.execution_status == status]

    def get_successful(self) -> List[MemoryEntry]:
        return [
            e
            for e in self.entries
            if e.execution_status == "completed" and e.safety_passed
        ]

    def get_failures(self) -> List[MemoryEntry]:
        return [
            e
            for e in self.entries
            if e.execution_status != "completed" or not e.safety_passed
        ]

    def to_dict_list(self) -> List[Dict]:
        return [
            {
                "timestamp": e.timestamp,
                "strategy_id": e.strategy_id,
                "trigger_type": e.trigger_type,
                "current_load_rt": e.current_load_rt,
                "predicted_load_rt": e.predicted_load_rt,
                "cop_improvement": e.cop_improvement,
                "energy_saving_kwh": e.energy_saving_kwh,
                "carbon_saving_kg": e.carbon_saving_kg,
                "arbitration_decision": e.arbitration_decision,
                "execution_status": e.execution_status,
                "safety_passed": e.safety_passed,
            }
            for e in self.entries
        ]

    def __len__(self) -> int:
        return len(self.entries)
