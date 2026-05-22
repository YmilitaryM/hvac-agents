"""ISA-18.2 / EEMUA 191 alarm management data models.

Defines the alarm lifecycle states, severity levels, and the core ISA18Alarm
dataclass with all fields required by the standard.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


def _new_alarm_id() -> str:
    return uuid.uuid4().hex[:12]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AlarmState(str, Enum):
    """ISA-18.2 alarm state machine states.

    States:
        NORMAL          - No alarm condition present (cleared).
        UNACKNOWLEDGED  - Alarm raised but not yet seen by operator.
        ACKNOWLEDGED    - Operator has seen and accepted the alarm.
        SHELVED         - Temporarily removed from active view; auto-returns.
        SUPPRESSED      - Intentionally hidden (e.g., maintenance, flood, chatter).
    """
    NORMAL = "normal"
    UNACKNOWLEDGED = "unacknowledged"
    ACKNOWLEDGED = "acknowledged"
    SHELVED = "shelved"
    SUPPRESSED = "suppressed"


class AlarmSeverity(int, Enum):
    """ISA-18.2 severity levels.

    1 = CRITICAL  — Immediate threat to safety or catastrophic equipment damage.
    2 = HIGH       — Potential damage, loss of primary function.
    3 = MEDIUM     — Efficiency loss, unplanned maintenance required.
    4 = LOW        — Degradation, advisory action needed.
    5 = INFO       — Informational, no immediate action required.
    """
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


# EEMUA 191 HMI colour coding
SEVERITY_COLOUR = {
    AlarmSeverity.CRITICAL: "#FF0000",  # Red — immediate action
    AlarmSeverity.HIGH:     "#FF8C00",  # Dark orange
    AlarmSeverity.MEDIUM:   "#FFD700",  # Gold / yellow
    AlarmSeverity.LOW:      "#87CEEB",  # Light blue
    AlarmSeverity.INFO:     "#D3D3D3",  # Light grey — no action
}

SEVERITY_LABEL = {
    AlarmSeverity.CRITICAL: "Critical",
    AlarmSeverity.HIGH:     "High",
    AlarmSeverity.MEDIUM:   "Medium",
    AlarmSeverity.LOW:      "Low",
    AlarmSeverity.INFO:     "Info",
}

# ISA-18.2 recommended max TTR per severity (seconds)
DEFAULT_TTR_SECONDS = {
    AlarmSeverity.CRITICAL: 60,       # 1 minute
    AlarmSeverity.HIGH:     300,      # 5 minutes
    AlarmSeverity.MEDIUM:   1800,     # 30 minutes
    AlarmSeverity.LOW:      14400,    # 4 hours
    AlarmSeverity.INFO:     86400,    # 24 hours
}

# Consequence weight factor used in priority calculation
CONSEQUENCE_WEIGHT = {
    AlarmSeverity.CRITICAL: 1.0,
    AlarmSeverity.HIGH:     0.8,
    AlarmSeverity.MEDIUM:   0.5,
    AlarmSeverity.LOW:      0.25,
    AlarmSeverity.INFO:     0.05,
}


@dataclass
class ISA18Alarm:
    """An ISA-18.2 compliant alarm.

    Every alarm MUST have: severity, priority, rationalization, consequence-of-inaction,
    and time-to-respond.  These are non-negotiable for ISA-18.2 compliance.
    """
    tag: str
    description: str
    severity: AlarmSeverity
    rationalization: str
    consequence_of_inaction: str
    time_to_respond_seconds: int

    id: str = field(default_factory=_new_alarm_id)
    priority: int = 50                   # 1-100, derived from severity x TTR matrix
    state: AlarmState = AlarmState.UNACKNOWLEDGED
    time_activated: datetime = field(default_factory=_utcnow)
    time_acknowledged: Optional[datetime] = None
    time_cleared: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    shelved_until: Optional[datetime] = None
    suppressed_reason: Optional[str] = None
    occurrence_count: int = 1
    last_occurrence: Optional[datetime] = None

    def __post_init__(self):
        # Auto-calculate priority from severity and TTR if not explicitly set
        if self.priority == 50:  # still default
            self.priority = self._compute_priority()
        # Track first occurrence
        if self.last_occurrence is None:
            self.last_occurrence = self.time_activated

    def _compute_priority(self) -> int:
        """Derive priority (1-100) from the severity-consequence matrix.

        Priority = max(1, min(100, severity_component + ttr_component))

        severity_component uses consequence weight (0-50 points).
        ttr_component gives higher priority to shorter TTRs (0-50 points).
        """
        sev_score = int(CONSEQUENCE_WEIGHT.get(self.severity, 0.5) * 50)

        # Shorter TTR → higher urgency score
        if self.time_to_respond_seconds <= 60:
            ttr_score = 50
        elif self.time_to_respond_seconds <= 300:
            ttr_score = 40
        elif self.time_to_respond_seconds <= 900:
            ttr_score = 30
        elif self.time_to_respond_seconds <= 3600:
            ttr_score = 20
        elif self.time_to_respond_seconds <= 14400:
            ttr_score = 10
        else:
            ttr_score = 5

        return max(1, min(100, sev_score + ttr_score))

    @property
    def is_active(self) -> bool:
        """An alarm is active if NOT in NORMAL state."""
        return self.state != AlarmState.NORMAL

    @property
    def is_stale(self) -> bool:
        """Stale: unacknowledged for more than 24 hours (ISA-18.2 definition)."""
        if self.state != AlarmState.UNACKNOWLEDGED:
            return False
        if self.time_acknowledged is not None:
            return False
        return (_utcnow() - self.time_activated).total_seconds() > 86400

    @property
    def colour(self) -> str:
        """EEMUA 191 HMI colour code for this alarm."""
        return SEVERITY_COLOUR.get(self.severity, "#808080")

    @property
    def severity_label(self) -> str:
        """Human-readable severity label."""
        return SEVERITY_LABEL.get(self.severity, "Unknown")

    @property
    def ttr_remaining_seconds(self) -> float:
        """Seconds remaining before response deadline expires.

        Negative value means the deadline has passed.
        """
        if self.state == AlarmState.NORMAL:
            return float("inf")
        elapsed = (_utcnow() - self.time_activated).total_seconds()
        return max(0.0, self.time_to_respond_seconds - elapsed)

    @property
    def ttr_expired(self) -> bool:
        """Has the time-to-respond deadline passed?"""
        return self.ttr_remaining_seconds <= 0

    def to_hmi_format(self) -> dict:
        """Export in EEMUA 191 HMI-recommended format.

        Returns a dict suitable for SCADA / operator workstation display.
        """
        return {
            "id": self.id,
            "tag": self.tag,
            "description": self.description,
            "severity": self.severity.value,
            "severity_label": self.severity_label,
            "colour": self.colour,
            "priority": self.priority,
            "state": self.state.value,
            "time_activated": self.time_activated.isoformat(),
            "time_acknowledged": self.time_acknowledged.isoformat() if self.time_acknowledged else None,
            "time_cleared": self.time_cleared.isoformat() if self.time_cleared else None,
            "acknowledged_by": self.acknowledged_by,
            "ttr_seconds": self.time_to_respond_seconds,
            "ttr_remaining_seconds": self.ttr_remaining_seconds,
            "ttr_expired": self.ttr_expired,
            "is_stale": self.is_stale,
            "consequence_of_inaction": self.consequence_of_inaction,
            "rationalization": self.rationalization,
            "shelved_until": self.shelved_until.isoformat() if self.shelved_until else None,
            "suppressed_reason": self.suppressed_reason,
            "occurrence_count": self.occurrence_count,
        }
