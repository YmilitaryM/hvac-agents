"""Tests for ISA-18.2 compliance validator.

Covers:
  - Benchmark checks: alarm rate, peak rate, stale %, rationalization, chatter
  - Edge cases: empty alarm set, all-compliant set, deliberately non-compliant set
  - Utility functions: get_unrationalized_alarms, get_chattering_alarms
"""

from datetime import datetime, timedelta, timezone

import pytest

from agent_service.alarm_models import ISA18Alarm, AlarmState, AlarmSeverity
from agent_service.alarm_manager import AlarmManager
from agent_service.alarm_compliance import (
    validate_compliance,
    get_unrationalized_alarms,
    get_chattering_alarms,
    ComplianceReport,
    ComplianceCheck,
)


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Empty alarm set
# ---------------------------------------------------------------------------

def test_empty_alarm_set_is_compliant():
    """An empty alarm manager should pass all compliance checks."""
    mgr = AlarmManager()
    report = validate_compliance(mgr)

    assert report.overall_compliant is True
    assert report.failed_count == 0
    for check in report.checks:
        assert check.passed is True, f"Check '{check.name}' failed: {check.actual_value}"


def test_empty_set_rationalization_coverage_100():
    """Empty set should show 100% rationalization coverage."""
    mgr = AlarmManager()
    report = validate_compliance(mgr)

    rationalization_check = _find_check(report, "rationalization_coverage")
    assert rationalization_check.actual_value == 100.0


# ---------------------------------------------------------------------------
# Compliant alarm set
# ---------------------------------------------------------------------------

def test_fully_compliant_alarms_pass_all_checks():
    """A well-configured alarm set should pass all ISA-18.2 checks."""
    mgr = AlarmManager()

    # Only 5 alarms — well under 150/day
    for i in range(5):
        alarm = ISA18Alarm(
            tag=f"CH-{i:02d}",
            description=f"Chiller {i} high pressure",
            severity=AlarmSeverity.MEDIUM,
            rationalization=f"Per FMEA-{42+i}, risk assessment completed",
            consequence_of_inaction=f"Compressor degradation, $10k repair",
            time_to_respond_seconds=1800,
        )
        mgr.raise_alarm(alarm)

    report = validate_compliance(mgr)
    assert report.overall_compliant is True
    assert report.failed_count == 0


# ---------------------------------------------------------------------------
# Non-compliant: unrationalized alarms
# ---------------------------------------------------------------------------

def test_unrationalized_alarms_fail():
    """Alarms missing rationalization should fail the rationalization check."""
    mgr = AlarmManager()

    alarm = ISA18Alarm(
        tag="CH-01",
        description="No rationale provided",
        severity=AlarmSeverity.HIGH,
        rationalization="",  # EMPTY — not rationalized
        consequence_of_inaction="Unknown",
        time_to_respond_seconds=300,
    )
    mgr.raise_alarm(alarm)

    report = validate_compliance(mgr)
    assert report.overall_compliant is False

    check = _find_check(report, "rationalization_coverage")
    assert check.passed is False
    assert check.actual_value == 0.0  # 0 out of 1 rationalized


def test_mixed_rationalization_state():
    """Some rationalized and some not should show partial coverage."""
    mgr = AlarmManager()

    # Rationalized
    mgr.raise_alarm(ISA18Alarm(
        tag="CH-01",
        description="Test 1",
        severity=AlarmSeverity.MEDIUM,
        rationalization="Documented rationale",
        consequence_of_inaction="Test",
        time_to_respond_seconds=1800,
    ))
    # Not rationalized
    mgr.raise_alarm(ISA18Alarm(
        tag="CH-02",
        description="Test 2",
        severity=AlarmSeverity.MEDIUM,
        rationalization="",
        consequence_of_inaction="Test",
        time_to_respond_seconds=1800,
    ))

    report = validate_compliance(mgr)

    check = _find_check(report, "rationalization_coverage")
    assert check.actual_value == 50.0


# ---------------------------------------------------------------------------
# Non-compliant: stale alarms
# ---------------------------------------------------------------------------

def test_stale_alarms_exceeding_threshold():
    """Alarms older than 24h unacknowledged should trigger stale check failure."""
    mgr = AlarmManager()

    alarm = ISA18Alarm(
        tag="CH-01",
        description="Very old alarm",
        severity=AlarmSeverity.LOW,
        rationalization="Documented",
        consequence_of_inaction="Minor",
        time_to_respond_seconds=86400,
    )
    # Set activation to 25 hours ago
    alarm.time_activated = _utcnow() - timedelta(hours=25)
    mgr._alarms[alarm.id] = alarm

    report = validate_compliance(mgr)

    check = _find_check(report, "stale_alarm_pct")
    # 1 out of 1 = 100% stale → fails threshold of 5%
    assert check.passed is False
    assert check.actual_value > 5.0


# ---------------------------------------------------------------------------
# Non-compliant: chattering alarms
# ---------------------------------------------------------------------------

def test_chattering_alarms_fail_chatter_check():
    """Alarms flagged as chattering should fail the chatter-free check."""
    mgr = AlarmManager()

    # Simulate chattering alarm by raising same tag 4x
    for i in range(4):
        alarm = ISA18Alarm(
            tag="CH-01",
            description="Chattering alarm",
            severity=AlarmSeverity.HIGH,
            rationalization="Documented",
            consequence_of_inaction="Test",
            time_to_respond_seconds=300,
        )
        mgr.raise_alarm(alarm)

    report = validate_compliance(mgr)

    check = _find_check(report, "chatter_free")
    assert check.passed is False
    assert check.actual_value >= 1


def test_no_chatter_when_below_threshold():
    """Alarms under the chatter threshold should pass."""
    mgr = AlarmManager()

    # Only 1 occurrence — no chatter
    alarm = ISA18Alarm(
        tag="CH-01",
        description="Normal alarm",
        severity=AlarmSeverity.MEDIUM,
        rationalization="Documented",
        consequence_of_inaction="Test",
        time_to_respond_seconds=1800,
    )
    mgr.raise_alarm(alarm)

    report = validate_compliance(mgr)

    check = _find_check(report, "chatter_free")
    assert check.passed is True


# ---------------------------------------------------------------------------
# Non-compliant: high alarm rate
# ---------------------------------------------------------------------------

def test_high_alarm_rate_fails_avg_check():
    """More than 150 alarms in one day should fail the average rate check."""
    mgr = AlarmManager()

    # 200 alarms (exceeds 150/day limit)
    for i in range(200):
        alarm = ISA18Alarm(
            tag=f"CH-{i:03d}",
            description=f"Rate test alarm {i}",
            severity=AlarmSeverity.INFO,
            rationalization=f"Rate test #{i}",
            consequence_of_inaction="Test",
            time_to_respond_seconds=86400,
        )
        mgr.raise_alarm(alarm)

    report = validate_compliance(mgr)

    check = _find_check(report, "avg_alarm_rate")
    # 200 alarms raised roughly now — over a day this is > 150
    assert check.passed is False


# ---------------------------------------------------------------------------
# Non-compliant: peak alarm rate
# ---------------------------------------------------------------------------

def test_high_peak_rate_fails_peak_check():
    """More than 10 alarms in 10 minutes should fail the peak rate check."""
    mgr = AlarmManager()

    # 15 alarms with different tags
    for i in range(15):
        alarm = ISA18Alarm(
            tag=f"PK-{i:02d}",
            description=f"Peak test alarm {i}",
            severity=AlarmSeverity.MEDIUM,
            rationalization="Documented",
            consequence_of_inaction="Test",
            time_to_respond_seconds=1800,
        )
        mgr.raise_alarm(alarm)

    report = validate_compliance(mgr)

    check = _find_check(report, "peak_alarm_rate")
    assert check.passed is False
    assert check.actual_value >= 10


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def test_get_unrationalized_alarms():
    """get_unrationalized_alarms should return only alarms without justification."""
    mgr = AlarmManager()

    mgr.raise_alarm(ISA18Alarm(
        tag="CH-01",
        description="Has rationale",
        severity=AlarmSeverity.MEDIUM,
        rationalization="Documented",
        consequence_of_inaction="Test",
        time_to_respond_seconds=1800,
    ))
    mgr.raise_alarm(ISA18Alarm(
        tag="CH-02",
        description="No rationale",
        severity=AlarmSeverity.MEDIUM,
        rationalization="",
        consequence_of_inaction="Test",
        time_to_respond_seconds=1800,
    ))

    unrationalized = get_unrationalized_alarms(mgr)
    assert len(unrationalized) == 1
    assert unrationalized[0]["tag"] == "CH-02"


def test_get_unrationalized_empty():
    """Empty manager should return empty list."""
    mgr = AlarmManager()
    assert get_unrationalized_alarms(mgr) == []


def test_get_chattering_alarms():
    """get_chattering_alarms should return only chattering alarms."""
    mgr = AlarmManager()

    # Create a chattering alarm (same tag 4x)
    for i in range(4):
        alarm = ISA18Alarm(
            tag="CH-01",
            description="Chattering",
            severity=AlarmSeverity.HIGH,
            rationalization="Documented",
            consequence_of_inaction="Test",
            time_to_respond_seconds=300,
        )
        mgr.raise_alarm(alarm)

    # Create a normal alarm
    mgr.raise_alarm(ISA18Alarm(
        tag="CH-02",
        description="Normal",
        severity=AlarmSeverity.LOW,
        rationalization="Documented",
        consequence_of_inaction="Test",
        time_to_respond_seconds=14400,
    ))

    chattering = get_chattering_alarms(mgr)
    assert len(chattering) >= 1
    # The chattering alarm should be in the results
    tags = [c["tag"] for c in chattering]
    assert "CH-01" in tags


def test_get_chattering_empty():
    """No chattering alarms should return empty list."""
    mgr = AlarmManager()
    assert get_chattering_alarms(mgr) == []


# ---------------------------------------------------------------------------
# ComplianceReport structure
# ---------------------------------------------------------------------------

def test_compliance_report_has_all_checks():
    """The compliance report should include all 5 ISA-18.2 benchmark checks."""
    mgr = AlarmManager()
    report = validate_compliance(mgr)

    check_names = {c.name for c in report.checks}
    expected = {
        "avg_alarm_rate",
        "peak_alarm_rate",
        "stale_alarm_pct",
        "rationalization_coverage",
        "chatter_free",
    }
    assert check_names == expected


def test_compliance_report_totals_add_up():
    """passed_count + failed_count should equal total checks."""
    mgr = AlarmManager()
    report = validate_compliance(mgr)

    assert report.passed_count + report.failed_count == len(report.checks)


def test_compliance_report_generated_at():
    """The report should include a generation timestamp."""
    mgr = AlarmManager()
    report = validate_compliance(mgr)

    assert report.generated_at is not None
    # Should be a valid ISO datetime string
    datetime.fromisoformat(report.generated_at)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_single_compliant_alarm():
    """A single well-formed alarm should pass all checks."""
    mgr = AlarmManager()
    alarm = ISA18Alarm(
        tag="CH-01",
        description="Single compliant alarm",
        severity=AlarmSeverity.MEDIUM,
        rationalization="Full rationalization per FMEA-042",
        consequence_of_inaction="Gradual efficiency loss",
        time_to_respond_seconds=1800,
    )
    mgr.raise_alarm(alarm)

    report = validate_compliance(mgr)
    assert report.overall_compliant is True


def test_only_unrationalized_fails_specific_check():
    """When only rationalization is missing, only that check should fail."""
    mgr = AlarmManager()
    alarm = ISA18Alarm(
        tag="CH-01",
        description="No rationale",
        severity=AlarmSeverity.MEDIUM,
        rationalization="",
        consequence_of_inaction="Test",
        time_to_respond_seconds=1800,
    )
    # Set old time so it's not a rate spike but not stale either
    alarm.time_activated = _utcnow() - timedelta(hours=1)
    mgr._alarms[alarm.id] = alarm

    report = validate_compliance(mgr)

    # Only rationalization_coverage should fail
    for check in report.checks:
        if check.name == "rationalization_coverage":
            assert check.passed is False
        else:
            assert check.passed is True, (
                f"Check '{check.name}' unexpectedly failed: "
                f"actual={check.actual_value}, threshold={check.threshold}"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_check(report: ComplianceReport, name: str) -> ComplianceCheck:
    """Find a specific compliance check by name."""
    for check in report.checks:
        if check.name == name:
            return check
    raise KeyError(f"Check '{name}' not found in report")
