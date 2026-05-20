from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class QualityEvent:
    point_id: str
    equipment_id: str
    event_type: str
    severity: str
    value: float | None
    threshold: float | None
    timestamp: datetime | None = None


class RealtimeRules:
    def __init__(self):
        self._bounds: dict[str, tuple[float, float]] = {}
        self._last_comms: dict[str, float] = {}
        self.comm_timeout_sec = 5.0

    def set_bounds(self, point_id: str, min_val: float, max_val: float) -> None:
        self._bounds[point_id] = (min_val, max_val)

    def check_bounds(self, point_id: str, equipment_id: str, value: float) -> QualityEvent | None:
        bounds = self._bounds.get(point_id)
        if bounds is None:
            return None
        lo, hi = bounds
        if value < lo or value > hi:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="out_of_bounds", severity="critical",
                value=value, threshold=hi if value > hi else lo,
                timestamp=datetime.now(timezone.utc)
            )
        return None

    def check_communication(self, point_id: str, equipment_id: str) -> QualityEvent | None:
        now = datetime.now(timezone.utc).timestamp()
        last = self._last_comms.get(point_id)
        if last is not None and now - last > self.comm_timeout_sec:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="communication_lost", severity="critical",
                value=None, threshold=None,
                timestamp=datetime.now(timezone.utc)
            )
        self._last_comms[point_id] = now
        return None
