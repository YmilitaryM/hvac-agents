"""Tests for ISA-18.2 alarm state machine (AlarmManager).

Covers:
  - Alarm lifecycle: raise → acknowledge → clear
  - Shelving: shelve → auto-return after time expires
  - Suppression: manual and automatic (chatter, flood)
  - Chatter detection: same alarm 4x in 5 min → suppressed
  - Flood detection: > 10 alarms in 1 min → auto-suppress
  - Performance metrics calculation
  - HMI export format
  - Rationalization report
  - State transition log (audit trail)
"""

from datetime import datetime, timedelta, timezone

import pytest

from agent_service.alarm_models import (
    ISA18Alarm,
    AlarmState,
    AlarmSeverity,
    SEVERITY_COLOUR,
    DEFAULT_TTR_SECONDS,
)
from agent_service.alarm_manager import AlarmManager


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Alarm lifecycle: raise → acknowledge → clear
# ---------------------------------------------------------------------------

def test_raise_alarm_creates_unacknowledged():
    """A newly raised alarm starts in UNACKNOWLEDGED state."""
    mgr = AlarmManager()
    alarm = ISA18Alarm(
        tag="CH-01",
        description="Chiller-1 high discharge pressure",
        severity=AlarmSeverity.HIGH,
        rationalization="Pressure > 900 kPa risks compressor damage per FMEA-042",
        consequence_of_inaction="Compressor failure, 72h downtime, $50k repair",
        time_to_respond_seconds=300,
    )
    result = mgr.raise_alarm(alarm)
    assert result.state == AlarmState.UNACKNOWLEDGED
    assert result.id in mgr._alarms
    assert len(mgr.get_active_alarms()) == 1


def test_acknowledge_transitions_to_acknowledged():
    """Acknowledging an UNACKNOWLEDGED alarm moves it to ACKNOWLEDGED."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)

    result = mgr.acknowledge(alarm.id, "operator-1")

    assert result.state == AlarmState.ACKNOWLEDGED
    assert result.acknowledged_by == "operator-1"
    assert result.time_acknowledged is not None


def test_cannot_acknowledge_cleared_alarm():
    """Acknowledging a cleared alarm should raise ValueError."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)
    mgr.acknowledge(alarm.id, "op")
    mgr.clear(alarm.id)

    with pytest.raises(ValueError, match="Cannot acknowledge"):
        mgr.acknowledge(alarm.id, "op")


def test_clear_transitions_to_normal():
    """Clearing an acknowledged alarm returns it to NORMAL."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)
    mgr.acknowledge(alarm.id, "op")

    result = mgr.clear(alarm.id)

    assert result.state == AlarmState.NORMAL
    assert result.time_cleared is not None


def test_cannot_clear_already_cleared():
    """Clearing an already NORMAL alarm should raise ValueError."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)
    mgr.clear(alarm.id)

    with pytest.raises(ValueError, match="already cleared"):
        mgr.clear(alarm.id)


def test_full_lifecycle_audit_trail():
    """The state history log should capture every transition."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)
    mgr.acknowledge(alarm.id, "op")
    mgr.clear(alarm.id)

    history = mgr._state_history
    assert len(history) >= 3  # raise + ack + clear


# ---------------------------------------------------------------------------
# Shelving
# ---------------------------------------------------------------------------

def test_shelve_and_auto_unshelve():
    """A shelved alarm should auto-return when shelved_until passes."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)
    mgr.acknowledge(alarm.id, "op")

    # Shelve for 1 second from now
    until = _utcnow() + timedelta(seconds=1)
    mgr.shelve(alarm.id, until)
    assert alarm.state == AlarmState.SHELVED

    # Before expiry — still shelved
    returned = mgr.check_shelved()
    assert len(returned) == 0

    # After expiry — auto-returns
    import time
    time.sleep(1.1)
    returned = mgr.check_shelved()
    assert len(returned) == 1
    assert alarm.state == AlarmState.UNACKNOWLEDGED


def test_cannot_shelve_cleared_alarm():
    """Shelving a NORMAL alarm should raise ValueError."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)
    mgr.clear(alarm.id)

    with pytest.raises(ValueError, match="Cannot shelve"):
        mgr.shelve(alarm.id, _utcnow() + timedelta(hours=1))


def test_shelve_preserves_alarm_data():
    """Shelving should not lose alarm metadata."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)

    until = _utcnow() + timedelta(hours=2)
    mgr.shelve(alarm.id, until)

    retrieved = mgr.get_alarm(alarm.id)
    assert retrieved is not None
    assert retrieved.tag == "CH-01"
    assert retrieved.severity == AlarmSeverity.HIGH
    assert retrieved.rationalization != ""


def test_manual_unshelve():
    """Unshelving manually returns alarm to UNACKNOWLEDGED state."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)

    until = _utcnow() + timedelta(hours=2)
    mgr.shelve(alarm.id, until)
    assert alarm.state == AlarmState.SHELVED

    mgr.unshelve(alarm.id)
    assert alarm.state == AlarmState.UNACKNOWLEDGED
    assert alarm.shelved_until is None


def test_cannot_unshelve_non_shelved():
    """Unshelving a non-shelved alarm should raise ValueError."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)

    with pytest.raises(ValueError, match="not shelved"):
        mgr.unshelve(alarm.id)


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------

def test_suppress_sets_state_and_reason():
    """Suppressing an alarm records the reason."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)

    result = mgr.suppress(alarm.id, "Scheduled maintenance window")

    assert result.state == AlarmState.SUPPRESSED
    assert result.suppressed_reason == "Scheduled maintenance window"


def test_cannot_suppress_cleared():
    """Suppressing a cleared alarm should raise ValueError."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)
    mgr.clear(alarm.id)

    with pytest.raises(ValueError, match="Cannot suppress"):
        mgr.suppress(alarm.id, "test")


# ---------------------------------------------------------------------------
# Chatter detection — same alarm 4x in 5 min → suppressed
# ---------------------------------------------------------------------------

def test_chatter_detection_auto_suppresses():
    """Same alarm raised > 3 times within 5 minutes → auto-suppressed."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")

    # First occurrence
    mgr.raise_alarm(alarm)

    # Simulate re-triggers (same tag)
    for i in range(3):
        re_trigger = _make_alarm("CH-01")
        result = mgr.raise_alarm(re_trigger)

    # The 4th re-trigger should be suppressed via chatter detection
    assert result.state == AlarmState.SUPPRESSED
    assert "Chatter" in (result.suppressed_reason or "")
    assert result.occurrence_count > CHATTER_MAX_COUNT


def test_chatter_not_triggered_below_threshold():
    """Two occurrences in 5 min should NOT trigger chatter suppression."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)

    # Only one re-trigger (2 total)
    re_trigger = _make_alarm("CH-01")
    result = mgr.raise_alarm(re_trigger)

    # Should still be UNACKNOWLEDGED (or ACKNOWLEDGED if already handled)
    assert result.state != AlarmState.SUPPRESSED


# ---------------------------------------------------------------------------
# Flood detection — > 10 alarms in 1 min → auto-suppress
# ---------------------------------------------------------------------------

def test_flood_detection_auto_suppresses():
    """More than 10 alarms within 1 minute → new alarms auto-suppressed."""
    mgr = AlarmManager()

    # Raise 11 alarms quickly (tags must differ to be "new" alarms)
    for i in range(11):
        alarm = ISA18Alarm(
            tag=f"CH-{i:02d}",
            description=f"Test flood alarm {i}",
            severity=AlarmSeverity.MEDIUM,
            rationalization=f"Flood test rationalization #{i}",
            consequence_of_inaction="Test consequence",
            time_to_respond_seconds=1800,
        )
        result = mgr.raise_alarm(alarm)

    # The 11th+ alarm should be suppressed
    # (10th may pass, 11th triggers flood)
    suppressed = [a for a in mgr._alarms.values() if a.state == AlarmState.SUPPRESSED]
    assert len(suppressed) >= 1
    assert "Flood" in (suppressed[0].suppressed_reason or "")


def test_flood_not_triggered_below_threshold():
    """9 alarms in 1 min should NOT trigger flood suppression."""
    mgr = AlarmManager()

    for i in range(9):
        alarm = ISA18Alarm(
            tag=f"CH-{i:02d}",
            description=f"Test non-flood alarm {i}",
            severity=AlarmSeverity.LOW,
            rationalization=f"Non-flood rationalization #{i}",
            consequence_of_inaction="Test",
            time_to_respond_seconds=14400,
        )
        result = mgr.raise_alarm(alarm)
        assert result.state != AlarmState.SUPPRESSED


# ---------------------------------------------------------------------------
# Alarm re-trigger with same tag increments occurrence count
# ---------------------------------------------------------------------------

def test_re_trigger_increments_occurrence_count():
    """Raising an alarm with the same tag increments occurrence_count."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)

    assert alarm.occurrence_count == 1

    # Re-trigger
    re_trigger = _make_alarm("CH-01")
    mgr.raise_alarm(re_trigger)

    # The existing alarm should have been updated
    existing = mgr.get_alarm(alarm.id)
    assert existing is not None
    assert existing.occurrence_count == 2
    assert existing.last_occurrence is not None


# ---------------------------------------------------------------------------
# Performance metrics (ISA-18.2 KPIs)
# ---------------------------------------------------------------------------

def test_performance_metrics_empty_manager():
    """An empty alarm manager should return zero metrics."""
    mgr = AlarmManager()
    metrics = mgr.get_performance_metrics()

    assert metrics["total_alarms"] == 0
    assert metrics["active_alarms"] == 0
    assert metrics["average_alarms_per_day"] == 0.0
    assert metrics["stale_alarm_pct"] == 0.0
    assert metrics["chatter_count"] == 0


def test_performance_metrics_with_alarms():
    """Metrics should be calculated correctly with alarms present."""
    mgr = AlarmManager()
    for i in range(5):
        alarm = _make_alarm(f"CH-{i:02d}")
        mgr.raise_alarm(alarm)

    metrics = mgr.get_performance_metrics()

    assert metrics["total_alarms"] == 5
    assert metrics["active_alarms"] == 5  # all unacknowledged
    assert metrics["average_alarms_per_day"] > 0
    assert metrics["peak_alarm_rate_10min"] == 5
    assert "time_to_acknowledge_avg_s" in metrics
    assert "time_to_acknowledge_p95_s" in metrics
    assert "time_to_acknowledge_max_s" in metrics
    assert isinstance(metrics["flooded"], bool)


def test_acknowledge_time_tracking():
    """Time-to-acknowledge metrics should be computed from actual ack times."""
    mgr = AlarmManager()
    alarm = _make_alarm("CH-01")
    mgr.raise_alarm(alarm)
    mgr.acknowledge(alarm.id, "op")

    metrics = mgr.get_performance_metrics()

    # Time to ack should be very small (just raised)
    assert metrics["time_to_acknowledge_avg_s"] >= 0
    assert metrics["time_to_acknowledge_max_s"] >= 0


# ---------------------------------------------------------------------------
# HMI Export (EEMUA 191)
# ---------------------------------------------------------------------------

def test_to_hmi_format_includes_required_fields():
    """HMI export should include all EEMUA 191 required display fields."""
    alarm = _make_alarm("CH-01", severity=AlarmSeverity.CRITICAL)
    mgr = AlarmManager()
    mgr.raise_alarm(alarm)

    hmi = alarm.to_hmi_format()

    assert hmi["id"] == alarm.id
    assert hmi["tag"] == "CH-01"
    assert hmi["severity"] == 1  # CRITICAL
    assert hmi["severity_label"] == "Critical"
    assert hmi["colour"] == SEVERITY_COLOUR[AlarmSeverity.CRITICAL]
    assert "priority" in hmi
    assert hmi["state"] == "unacknowledged"
    assert hmi["ttr_seconds"] == DEFAULT_TTR_SECONDS[AlarmSeverity.CRITICAL]
    assert "ttr_remaining_seconds" in hmi
    assert "ttr_expired" in hmi
    assert "is_stale" in hmi
    assert hmi["consequence_of_inaction"] != ""
    assert hmi["rationalization"] != ""
    assert "occurrence_count" in hmi


def test_hmi_list_sorted_by_priority():
    """HMI list should sort by priority (highest first)."""
    mgr = AlarmManager()

    # Low priority alarm
    low = ISA18Alarm(
        tag="CT-01",
        description="Cooling tower low flow",
        severity=AlarmSeverity.LOW,
        rationalization="Flow below setpoint, check strainer",
        consequence_of_inaction="Minor efficiency loss",
        time_to_respond_seconds=14400,
    )
    # Critical alarm
    crit = ISA18Alarm(
        tag="CH-01",
        description="Chiller surge detected",
        severity=AlarmSeverity.CRITICAL,
        rationalization="Surge can destroy compressor bearings in seconds",
        consequence_of_inaction="Catastrophic compressor failure, $100k+ damage",
        time_to_respond_seconds=60,
    )

    mgr.raise_alarm(low)
    mgr.raise_alarm(crit)

    hmi_list = mgr.to_hmi_list()
    assert hmi_list[0]["priority"] >= hmi_list[1]["priority"]


def test_hmi_summary_counts():
    """HMI summary should provide correct counts by severity and state."""
    mgr = AlarmManager()
    mgr.raise_alarm(_make_alarm("CH-01", severity=AlarmSeverity.CRITICAL))
    mgr.raise_alarm(_make_alarm("CH-02", severity=AlarmSeverity.HIGH))
    mgr.raise_alarm(_make_alarm("CH-03", severity=AlarmSeverity.HIGH))

    summary = mgr.get_hmi_summary()

    assert summary["total_active"] == 3
    assert summary["by_severity"].get(1) == 1  # one critical
    assert summary["by_severity"].get(2) == 2  # two high
    assert summary["by_state"].get("unacknowledged") == 3
    assert isinstance(summary["flooded"], bool)
    assert summary["oldest_unacknowledged_minutes"] is not None


# ---------------------------------------------------------------------------
# Rationalization report
# ---------------------------------------------------------------------------

def test_rationalization_report_includes_all_alarms():
    """The rationalization report should list every alarm with its justification."""
    mgr = AlarmManager()
    mgr.raise_alarm(_make_alarm("CH-01"))
    mgr.raise_alarm(_make_alarm("CH-02"))

    report = mgr.get_rationalization_report()

    assert len(report) == 2
    for entry in report:
        assert entry["is_rationalized"] is True
        assert "alarm_id" in entry
        assert "tag" in entry
        assert "severity" in entry
        assert "rationalization" in entry
        assert "consequence_of_inaction" in entry
        assert "is_chatter" in entry


def test_rationalize_updates_alarm():
    """The rationalize method should update an alarm's rationalization text."""
    mgr = AlarmManager()
    alarm = ISA18Alarm(
        tag="CH-01",
        description="Test alarm without rationalization",
        severity=AlarmSeverity.MEDIUM,
        rationalization="",  # empty — not rationalized
        consequence_of_inaction="Unknown",
        time_to_respond_seconds=1800,
    )
    mgr.raise_alarm(alarm)

    report = mgr.get_rationalization_report()
    assert report[0]["is_rationalized"] is False

    mgr.rationalize(alarm.id, "Added rationale per ISA-18.2 commissioning review")
    report = mgr.get_rationalization_report()
    assert report[0]["is_rationalized"] is True
    assert "ISA-18.2" in report[0]["rationalization"]


# ---------------------------------------------------------------------------
# Query methods
# ---------------------------------------------------------------------------

def test_get_alarms_by_state():
    """Filtering alarms by state should return correct subset."""
    mgr = AlarmManager()
    a1 = _make_alarm("CH-01")
    a2 = _make_alarm("CH-02")
    mgr.raise_alarm(a1)
    mgr.raise_alarm(a2)
    mgr.acknowledge(a1.id, "op")

    unacked = mgr.get_alarms_by_state(AlarmState.UNACKNOWLEDGED)
    acked = mgr.get_alarms_by_state(AlarmState.ACKNOWLEDGED)

    assert len(unacked) == 1
    assert unacked[0].id == a2.id
    assert len(acked) == 1
    assert acked[0].id == a1.id


def test_get_alarms_by_severity():
    """Filtering alarms by severity should return correct subset."""
    mgr = AlarmManager()
    mgr.raise_alarm(_make_alarm("CH-01", severity=AlarmSeverity.CRITICAL))
    mgr.raise_alarm(_make_alarm("CH-02", severity=AlarmSeverity.LOW))

    critical = mgr.get_alarms_by_severity(AlarmSeverity.CRITICAL)
    low = mgr.get_alarms_by_severity(AlarmSeverity.LOW)

    assert len(critical) == 1
    assert len(low) == 1


def test_get_alarms_by_tag():
    """Finding alarms by equipment tag should return all for that tag."""
    mgr = AlarmManager()
    mgr.raise_alarm(_make_alarm("CH-01"))
    mgr.clear(mgr.raise_alarm(_make_alarm("CH-01")).id)
    mgr.raise_alarm(_make_alarm("CH-01"))  # re-raise after clear

    by_tag = mgr.get_alarms_by_tag("CH-01")
    assert len(by_tag) >= 2  # cleared + re-raised


def test_get_alarm_missing():
    """Getting a non-existent alarm should return None."""
    mgr = AlarmManager()
    assert mgr.get_alarm("nonexistent") is None


# ---------------------------------------------------------------------------
# Model-level properties
# ---------------------------------------------------------------------------

def test_isa18_alarm_priority_auto_computed():
    """Priority should be auto-computed from severity and TTR."""
    alarm = ISA18Alarm(
        tag="CH-01",
        description="Test",
        severity=AlarmSeverity.CRITICAL,
        rationalization="Test rationalization",
        consequence_of_inaction="Test consequence",
        time_to_respond_seconds=60,
    )
    assert 1 <= alarm.priority <= 100
    # Critical + very short TTR → high priority
    assert alarm.priority >= 70


def test_is_stale_after_24h():
    """An unacknowledged alarm older than 24h should be stale."""
    alarm = ISA18Alarm(
        tag="CH-01",
        description="Old alarm",
        severity=AlarmSeverity.LOW,
        rationalization="Test",
        consequence_of_inaction="Test",
        time_to_respond_seconds=86400,
    )
    # Manually set time back 25 hours
    alarm.time_activated = _utcnow() - timedelta(hours=25)
    assert alarm.is_stale is True


def test_is_not_stale_when_acknowledged():
    """An acknowledged alarm should not be stale regardless of age."""
    alarm = ISA18Alarm(
        tag="CH-01",
        description="Old but acked",
        severity=AlarmSeverity.LOW,
        rationalization="Test",
        consequence_of_inaction="Test",
        time_to_respond_seconds=86400,
    )
    alarm.time_activated = _utcnow() - timedelta(hours=25)
    alarm.state = AlarmState.ACKNOWLEDGED
    alarm.time_acknowledged = _utcnow() - timedelta(hours=24)
    assert alarm.is_stale is False


def test_ttr_remaining_and_expired():
    """TTR countdown should work correctly."""
    alarm = ISA18Alarm(
        tag="CH-01",
        description="TTR test",
        severity=AlarmSeverity.HIGH,
        rationalization="Test",
        consequence_of_inaction="Test",
        time_to_respond_seconds=300,  # 5 min
    )
    # Fresh alarm — should have ~300s remaining
    remaining = alarm.ttr_remaining_seconds
    assert 290 <= remaining <= 300
    assert alarm.ttr_expired is False

    # Time in the past → expired
    alarm.time_activated = _utcnow() - timedelta(minutes=10)
    assert alarm.ttr_remaining_seconds == 0.0
    assert alarm.ttr_expired is True


def test_active_property():
    """is_active should be True for non-NORMAL states."""
    alarm = _make_alarm("CH-01")
    assert alarm.is_active is True
    alarm.state = AlarmState.NORMAL
    assert alarm.is_active is False


def test_severity_colour_mapping():
    """Each severity should have an EEMUA 191 colour."""
    assert SEVERITY_COLOUR[AlarmSeverity.CRITICAL] == "#FF0000"
    assert SEVERITY_COLOUR[AlarmSeverity.HIGH] == "#FF8C00"
    assert SEVERITY_COLOUR[AlarmSeverity.MEDIUM] == "#FFD700"
    assert SEVERITY_COLOUR[AlarmSeverity.LOW] == "#87CEEB"
    assert SEVERITY_COLOUR[AlarmSeverity.INFO] == "#D3D3D3"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Threshold constants from alarm_manager (for test assertions)
CHATTER_MAX_COUNT = 3
CHATTER_WINDOW_SECONDS = 300


def _make_alarm(
    tag: str = "CH-01",
    severity: AlarmSeverity = AlarmSeverity.HIGH,
) -> ISA18Alarm:
    """Create a fully-populated ISA18Alarm for testing."""
    return ISA18Alarm(
        tag=tag,
        description=f"Test alarm for {tag}",
        severity=severity,
        rationalization=f"Rationalization for {tag}: per FMEA-042 risk assessment",
        consequence_of_inaction=f"Consequence of ignoring {tag}: equipment damage",
        time_to_respond_seconds=DEFAULT_TTR_SECONDS.get(severity, 300),
    )
