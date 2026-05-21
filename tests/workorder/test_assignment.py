"""Tests for the workorder role-assignment logic.

Pure logic tests — no database or mocking needed.
"""

import pytest

from agent_service.workorder.assignment import (
    DEFAULT_ROLE_MAP,
    assign_work_order,
)


# ---------------------------------------------------------------------------
# DEFAULT_ROLE_MAP structure
# ---------------------------------------------------------------------------

def test_role_map_has_expected_entries():
    assert DEFAULT_ROLE_MAP == {
        "chiller": "hvac-technician",
        "cooling_tower": "hvac-technician",
        "pump": "mechanic",
        "valve": "mechanic",
        "sensor": "instrumentation-tech",
    }


# ---------------------------------------------------------------------------
# assign_work_order — non-critical severity
# ---------------------------------------------------------------------------

def test_assign_chiller_normal():
    assert assign_work_order("chiller", "warning") == "hvac-technician"
    assert assign_work_order("chiller", "info") == "hvac-technician"


def test_assign_cooling_tower_normal():
    assert assign_work_order("cooling_tower", "minor") == "hvac-technician"


def test_assign_pump_normal():
    assert assign_work_order("pump", "moderate") == "mechanic"


def test_assign_valve_normal():
    assert assign_work_order("valve", "low") == "mechanic"


def test_assign_sensor_normal():
    assert assign_work_order("sensor", "normal") == "instrumentation-tech"


# ---------------------------------------------------------------------------
# assign_work_order — critical severity
# ---------------------------------------------------------------------------

def test_assign_chiller_critical():
    assert assign_work_order("chiller", "critical") == "hvac-technician-lead"


def test_assign_cooling_tower_critical():
    assert assign_work_order("cooling_tower", "critical") == "hvac-technician-lead"


def test_assign_pump_critical():
    assert assign_work_order("pump", "critical") == "mechanic-lead"


def test_assign_valve_critical():
    assert assign_work_order("valve", "critical") == "mechanic-lead"


def test_assign_sensor_critical():
    assert assign_work_order("sensor", "critical") == "instrumentation-tech-lead"


# ---------------------------------------------------------------------------
# assign_work_order — unknown equipment type
# ---------------------------------------------------------------------------

def test_assign_unknown_equipment_normal():
    assert assign_work_order("compressor", "warning") == "general-maintenance"


def test_assign_unknown_equipment_critical():
    assert assign_work_order("compressor", "critical") == "general-maintenance-lead"


def test_assign_empty_equipment_type():
    assert assign_work_order("", "normal") == "general-maintenance"


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------

def test_assign_case_sensitive_severity():
    """Severity 'Critical' (capital C) is not the same as 'critical'."""
    assert assign_work_order("pump", "Critical") == "mechanic"
    assert assign_work_order("pump", "CRITICAL") == "mechanic"


def test_assign_all_mapped_types_with_both_severities():
    """Sanity-check every mapped type with both normal and critical severity."""
    for eq_type, base_role in DEFAULT_ROLE_MAP.items():
        assert assign_work_order(eq_type, "normal") == base_role
        assert assign_work_order(eq_type, "critical") == f"{base_role}-lead"
