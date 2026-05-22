"""ISA-18.2 Alarm State Machine.

Implements the full alarm lifecycle per ISA-18.2 / EEMUA 191:
  NORMAL → UNACKNOWLEDGED → ACKNOWLEDGED → (cleared back to NORMAL)

With side-transitions:
  - SHELVE: temporarily hide an alarm; auto-returns after shelved_until
  - SUPPRESS: hide alarm (maintenance, flood protection, chatter prevention)
  - CLEAR: return to NORMAL (alarm condition gone)
"""

from datetime import datetime, timezone
from typing import Optional

from .alarm_models import ISA18Alarm, AlarmState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ISA-18.2 / EEMUA 191 thresholds
CHATTER_WINDOW_SECONDS = 300      # 5 minutes
CHATTER_MAX_COUNT = 3             # > 3 occurrences in window = chatter
FLOOD_WINDOW_SECONDS = 60         # 1 minute
FLOOD_MAX_ALARMS = 10             # > 10 in 1 minute = flood
STALE_THRESHOLD_SECONDS = 86400   # 24 hours


class AlarmManager:
    """Manages the ISA-18.2 alarm lifecycle with in-memory storage.

    Features:
      - Full state machine (raise → ack → shelve → suppress → clear)
      - Chatter detection (auto-suppress repeated alarms)
      - Flood detection (auto-suppress alarm storms)
      - Performance metrics per ISA-18.2 KPIs
      - Rationalization report generation
      - EEMUA 191 HMI-formatted export
    """

    def __init__(self):
        self._alarms: dict[str, ISA18Alarm] = {}
        self._state_history: list[dict] = []

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def raise_alarm(self, alarm: ISA18Alarm) -> ISA18Alarm:
        """Raise a new alarm or re-trigger an existing one.

        Detects chatter and flood conditions, auto-suppressing when thresholds
        are breached per ISA-18.2 guidelines.
        """
        # Check for existing alarm with same tag
        existing = self._find_by_tag(alarm.tag)

        if existing is not None and existing.state != AlarmState.NORMAL:
            # Update occurrence tracking
            existing.occurrence_count += 1
            existing.last_occurrence = _utcnow()

            self._log_transition(
                existing.id, existing.state, existing.state,
                f"Re-occurrence #{existing.occurrence_count}"
            )

            # Chatter detection
            if self._is_chatter(existing):
                existing.state = AlarmState.SUPPRESSED
                existing.suppressed_reason = (
                    f"Chatter: {existing.occurrence_count} occurrences within "
                    f"{CHATTER_WINDOW_SECONDS}s window"
                )
                self._log_transition(
                    existing.id, AlarmState.UNACKNOWLEDGED, AlarmState.SUPPRESSED,
                    existing.suppressed_reason
                )

            return existing

        # Check for flood before adding (count existing + 1 for this alarm)
        if self._is_flood(include_pending=1):
            alarm.state = AlarmState.SUPPRESSED
            alarm.suppressed_reason = (
                f"Flood protection: > {FLOOD_MAX_ALARMS} alarms within "
                f"{FLOOD_WINDOW_SECONDS}s window"
            )
            self._alarms[alarm.id] = alarm
            self._log_transition(
                alarm.id, AlarmState.UNACKNOWLEDGED, AlarmState.SUPPRESSED,
                alarm.suppressed_reason
            )
            return alarm

        # New alarm
        self._alarms[alarm.id] = alarm
        self._log_transition(None, None, alarm.state, f"Alarm raised: {alarm.tag}")
        return alarm

    def acknowledge(self, alarm_id: str, user: str) -> ISA18Alarm:
        """Acknowledge an alarm — operator has seen and accepted it."""
        alarm = self._get(alarm_id)
        if alarm.state not in (AlarmState.UNACKNOWLEDGED,):
            raise ValueError(
                f"Cannot acknowledge alarm in state '{alarm.state.value}'. "
                f"Must be 'unacknowledged'."
            )
        old_state = alarm.state
        alarm.state = AlarmState.ACKNOWLEDGED
        alarm.time_acknowledged = _utcnow()
        alarm.acknowledged_by = user
        self._log_transition(alarm_id, old_state, alarm.state, f"Acknowledged by {user}")
        return alarm

    def shelve(self, alarm_id: str, until: datetime) -> ISA18Alarm:
        """Shelve an alarm — temporarily hide until the given time."""
        alarm = self._get(alarm_id)
        if alarm.state == AlarmState.NORMAL:
            raise ValueError("Cannot shelve a cleared alarm.")
        old_state = alarm.state
        alarm.state = AlarmState.SHELVED
        alarm.shelved_until = until
        self._log_transition(
            alarm_id, old_state, alarm.state,
            f"Shelved until {until.isoformat()}"
        )
        return alarm

    def suppress(self, alarm_id: str, reason: str) -> ISA18Alarm:
        """Suppress an alarm — intentionally hide with a documented reason."""
        alarm = self._get(alarm_id)
        if alarm.state == AlarmState.NORMAL:
            raise ValueError("Cannot suppress a cleared alarm.")
        old_state = alarm.state
        alarm.state = AlarmState.SUPPRESSED
        alarm.suppressed_reason = reason
        self._log_transition(
            alarm_id, old_state, alarm.state,
            f"Suppressed: {reason}"
        )
        return alarm

    def clear(self, alarm_id: str) -> ISA18Alarm:
        """Clear an alarm — the alarm condition no longer exists."""
        alarm = self._get(alarm_id)
        if alarm.state == AlarmState.NORMAL:
            raise ValueError("Alarm is already cleared.")
        old_state = alarm.state
        alarm.state = AlarmState.NORMAL
        alarm.time_cleared = _utcnow()
        self._log_transition(alarm_id, old_state, AlarmState.NORMAL, "Cleared")
        return alarm

    def unshelve(self, alarm_id: str) -> ISA18Alarm:
        """Return a shelved alarm to its previous active state.

        Called automatically when shelved_until has passed, or manually.
        """
        alarm = self._get(alarm_id)
        if alarm.state != AlarmState.SHELVED:
            raise ValueError(f"Alarm is not shelved (current: {alarm.state.value}).")
        old_state = alarm.state
        # Return to unacknowledged (must be re-acknowledged)
        alarm.state = AlarmState.UNACKNOWLEDGED
        alarm.shelved_until = None
        self._log_transition(alarm_id, old_state, alarm.state, "Unshelved")
        return alarm

    def check_shelved(self) -> list[ISA18Alarm]:
        """Auto-return shelved alarms whose shelved_until has passed."""
        now = _utcnow()
        returned = []
        for alarm in self._alarms.values():
            if (
                alarm.state == AlarmState.SHELVED
                and alarm.shelved_until is not None
                and alarm.shelved_until <= now
            ):
                self.unshelve(alarm.id)
                returned.append(alarm)
        return returned

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_alarm(self, alarm_id: str) -> Optional[ISA18Alarm]:
        """Get a single alarm by ID."""
        return self._alarms.get(alarm_id)

    def get_active_alarms(self) -> list[ISA18Alarm]:
        """Get all alarms that are NOT in NORMAL state."""
        return [a for a in self._alarms.values() if a.state != AlarmState.NORMAL]

    def get_alarms_by_state(self, state: AlarmState) -> list[ISA18Alarm]:
        """Get all alarms in a given state."""
        return [a for a in self._alarms.values() if a.state == state]

    def get_alarms_by_severity(self, severity: "AlarmSeverity") -> list[ISA18Alarm]:  # noqa: F821
        """Get all alarms of a given severity."""
        return [a for a in self._alarms.values() if a.severity == severity]

    def get_alarms_by_tag(self, tag: str) -> list[ISA18Alarm]:
        """Get all alarms (including cleared) for a given equipment tag."""
        return [a for a in self._alarms.values() if a.tag == tag]

    # ------------------------------------------------------------------
    # Flood / Chatter detection (ISA-18.2)
    # ------------------------------------------------------------------

    def _is_chatter(self, alarm: ISA18Alarm) -> bool:
        """Detect chattering alarm: same tag repeated within the chat window."""
        return (
            alarm.occurrence_count > CHATTER_MAX_COUNT
            and alarm.last_occurrence is not None
            and (alarm.last_occurrence - alarm.time_activated).total_seconds()
            <= CHATTER_WINDOW_SECONDS
        )

    def _is_flood(self, include_pending: int = 0) -> bool:
        """Detect alarm flood: too many active alarms within the flood window.

        Args:
            include_pending: Number of pending alarms to include in the count
                             (e.g., the alarm currently being raised).
        """
        now = _utcnow()
        recent_count = sum(
            1 for a in self._alarms.values()
            if a.time_activated is not None
            and (now - a.time_activated).total_seconds() <= FLOOD_WINDOW_SECONDS
        )
        return (recent_count + include_pending) > FLOOD_MAX_ALARMS

    # ------------------------------------------------------------------
    # ISA-18.2 Performance Metrics (KPI)
    # ------------------------------------------------------------------

    def get_performance_metrics(self) -> dict:
        """Calculate ISA-18.2 KPIs.

        Returns:
            - average_alarms_per_day: mean alarm rate per 24h
            - peak_alarm_rate_10min: max alarms in any 10-min window
            - stale_alarm_pct: % of unacknowledged alarms > 24h old
            - chatter_count: alarms with > 3 occurrences in 5 min
            - time_to_acknowledge: avg / p95 / max (seconds)
            - total_alarms: total in system
            - active_alarms: current count not in NORMAL state
            - flooded: whether flood condition is currently active
        """
        all_alarms = list(self._alarms.values())
        total = len(all_alarms)
        if total == 0:
            return {
                "average_alarms_per_day": 0.0,
                "peak_alarm_rate_10min": 0,
                "stale_alarm_pct": 0.0,
                "chatter_count": 0,
                "time_to_acknowledge_avg_s": 0.0,
                "time_to_acknowledge_p95_s": 0.0,
                "time_to_acknowledge_max_s": 0.0,
                "total_alarms": 0,
                "active_alarms": 0,
                "flooded": False,
            }

        # Average alarms per day
        if all_alarms:
            earliest = min(a.time_activated for a in all_alarms)
            latest = max(
                (a.time_cleared or a.time_activated) for a in all_alarms
            )
            days = max(1.0, (latest - earliest).total_seconds() / 86400)
            avg_per_day = total / days
        else:
            avg_per_day = 0.0

        # Peak alarm rate per 10 minutes
        peak_10min = self._peak_alarm_rate(all_alarms, window_seconds=600)

        # Stale alarm %
        unacked = [a for a in all_alarms if a.state == AlarmState.UNACKNOWLEDGED]
        now = _utcnow()
        stale_count = sum(
            1 for a in unacked
            if (now - a.time_activated).total_seconds() > STALE_THRESHOLD_SECONDS
        )
        stale_pct = (stale_count / total * 100) if total > 0 else 0.0

        # Chatter count
        chatter_count = sum(
            1 for a in all_alarms
            if a.occurrence_count > CHATTER_MAX_COUNT
            and a.last_occurrence is not None
            and (a.last_occurrence - a.time_activated).total_seconds()
            <= CHATTER_WINDOW_SECONDS
        )

        # Time to acknowledge
        ack_times = [
            (a.time_acknowledged - a.time_activated).total_seconds()
            for a in all_alarms
            if a.time_acknowledged is not None
        ]
        if ack_times:
            ack_times_sorted = sorted(ack_times)
            avg_ack = sum(ack_times) / len(ack_times)
            p95_idx = int(len(ack_times_sorted) * 0.95)
            if p95_idx >= len(ack_times_sorted):
                p95_idx = len(ack_times_sorted) - 1
            p95_ack = ack_times_sorted[p95_idx]
            max_ack = ack_times_sorted[-1]
        else:
            avg_ack = 0.0
            p95_ack = 0.0
            max_ack = 0.0

        active_count = sum(1 for a in all_alarms if a.state != AlarmState.NORMAL)

        return {
            "average_alarms_per_day": round(avg_per_day, 2),
            "peak_alarm_rate_10min": peak_10min,
            "stale_alarm_pct": round(stale_pct, 1),
            "chatter_count": chatter_count,
            "time_to_acknowledge_avg_s": round(avg_ack, 1),
            "time_to_acknowledge_p95_s": round(p95_ack, 1),
            "time_to_acknowledge_max_s": round(max_ack, 1),
            "total_alarms": total,
            "active_alarms": active_count,
            "flooded": self._is_flood(),
        }

    def _peak_alarm_rate(
        self, alarms: list[ISA18Alarm], window_seconds: int = 600
    ) -> int:
        """Calculate the maximum number of alarms raised in any sliding window."""
        times = sorted(a.time_activated for a in alarms)
        if not times:
            return 0
        max_count = 0
        left = 0
        for right in range(len(times)):
            while (times[right] - times[left]).total_seconds() > window_seconds:
                left += 1
            max_count = max(max_count, right - left + 1)
        return max_count

    # ------------------------------------------------------------------
    # Rationalization report
    # ------------------------------------------------------------------

    def get_rationalization_report(self) -> list[dict]:
        """Generate ISA-18.2 rationalization report.

        Lists every alarm with its justification, consequence, and whether
        it has been rationalized (has non-empty rationalization text).

        Returns a list of dicts suitable for audit / compliance review.
        """
        report = []
        for alarm in self._alarms.values():
            report.append({
                "alarm_id": alarm.id,
                "tag": alarm.tag,
                "description": alarm.description,
                "severity": alarm.severity.value,
                "severity_label": alarm.severity_label,
                "priority": alarm.priority,
                "state": alarm.state.value,
                "rationalization": alarm.rationalization,
                "is_rationalized": bool(alarm.rationalization.strip()),
                "consequence_of_inaction": alarm.consequence_of_inaction,
                "time_to_respond_seconds": alarm.time_to_respond_seconds,
                "occurrence_count": alarm.occurrence_count,
                "is_chatter": (
                    alarm.occurrence_count > CHATTER_MAX_COUNT
                    and alarm.last_occurrence is not None
                    and alarm.time_activated is not None
                    and (alarm.last_occurrence - alarm.time_activated).total_seconds()
                    <= CHATTER_WINDOW_SECONDS
                ),
            })
        return report

    def rationalize(self, alarm_id: str, rationalization: str) -> ISA18Alarm:
        """Add or update the rationalization for an alarm."""
        alarm = self._get(alarm_id)
        alarm.rationalization = rationalization
        self._log_transition(
            alarm_id, alarm.state, alarm.state,
            f"Rationalization updated"
        )
        return alarm

    # ------------------------------------------------------------------
    # HMI Export (EEMUA 191)
    # ------------------------------------------------------------------

    def to_hmi_list(self) -> list[dict]:
        """Export all alarms in EEMUA 191 HMI format.

        Sorted by priority (highest first), then by activation time (newest first).
        """
        active = [a.to_hmi_format() for a in self._alarms.values()
                  if a.state != AlarmState.NORMAL]
        active.sort(key=lambda x: (-x["priority"], x["time_activated"]))
        return active

    def to_hmi_detail(self, alarm_id: str) -> Optional[dict]:
        """Export a single alarm in HMI format."""
        alarm = self._alarms.get(alarm_id)
        if alarm is None:
            return None
        return alarm.to_hmi_format()

    def get_hmi_summary(self) -> dict:
        """HMI summary panel data per EEMUA 191.

        Provides counts by severity and state for the operator overview display.
        """
        active = self.get_active_alarms()
        by_severity = {}
        by_state = {}
        for a in active:
            sev = a.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            st = a.state.value
            by_state[st] = by_state.get(st, 0) + 1

        return {
            "total_active": len(active),
            "by_severity": by_severity,
            "by_state": by_state,
            "flooded": self._is_flood(),
            "oldest_unacknowledged_minutes": self._oldest_unacked_minutes(),
        }

    def _oldest_unacked_minutes(self) -> Optional[float]:
        """Minutes since the oldest unacknowledged alarm was raised."""
        unacked = [
            a for a in self._alarms.values()
            if a.state == AlarmState.UNACKNOWLEDGED
        ]
        if not unacked:
            return None
        oldest = min(a.time_activated for a in unacked)
        return (_utcnow() - oldest).total_seconds() / 60

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, alarm_id: str) -> ISA18Alarm:
        """Get alarm by ID, raising KeyError if not found."""
        alarm = self._alarms.get(alarm_id)
        if alarm is None:
            raise KeyError(f"Alarm not found: {alarm_id}")
        return alarm

    def _find_by_tag(self, tag: str) -> Optional[ISA18Alarm]:
        """Find the most recent active alarm for a given tag."""
        matches = [a for a in self._alarms.values()
                   if a.tag == tag and a.state != AlarmState.NORMAL]
        if not matches:
            return None
        # Return the latest (most recently activated)
        return max(matches, key=lambda a: a.time_activated)

    def _log_transition(
        self,
        alarm_id: Optional[str],
        from_state: Optional[AlarmState],
        to_state: AlarmState,
        note: str = "",
    ):
        self._state_history.append({
            "timestamp": _utcnow().isoformat(),
            "alarm_id": alarm_id or "new",
            "from_state": from_state.value if from_state else None,
            "to_state": to_state.value,
            "note": note,
        })
