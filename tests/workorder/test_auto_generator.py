"""Tests for the workorder auto-generator functions.

These tests use the real WorkOrder model class but never persist to a DB.
Pure logic — no database or mocking needed.
"""

from agent_service.workorder.models import WorkOrder
from agent_service.workorder.auto_generator import (
    generate_from_anomaly,
    generate_from_degradation,
)


# ---------------------------------------------------------------------------
# generate_from_anomaly
# ---------------------------------------------------------------------------

def test_generate_from_anomaly_creates_workorder():
    wo = generate_from_anomaly(
        edge_id="edge-1",
        equipment_id="chiller-A",
        severity="critical",
        check_id="temp_check",
        detail="Temperature exceeds threshold",
    )

    assert isinstance(wo, WorkOrder)
    assert wo.edge_id == "edge-1"
    assert wo.equipment_id == "chiller-A"
    assert wo.severity == "critical"
    assert wo.title == "Inspection failed: temp_check"
    assert wo.description == "Temperature exceeds threshold"
    assert wo.source == "auto"


def test_generate_from_anomaly_default_status():
    """status is NULL at construction time - SQLAlchemy applies 'open' on INSERT.
    The generator does not set status explicitly."""
    wo = generate_from_anomaly("e1", "eq1", "warning", "c1", "detail")
    assert wo.status is None


def test_generate_from_anomaly_default_assigned_to():
    """assigned_to is not set by the generator — it should be None."""
    wo = generate_from_anomaly("e1", "eq1", "warning", "c1", "detail")
    assert wo.assigned_to is None


def test_generate_from_anomaly_with_empty_detail():
    wo = generate_from_anomaly("e1", "eq1", "info", "check-x", "")
    assert wo.description == ""
    assert wo.title == "Inspection failed: check-x"


# ---------------------------------------------------------------------------
# generate_from_degradation
# ---------------------------------------------------------------------------

def test_generate_from_degradation_creates_workorder():
    wo = generate_from_degradation(
        edge_id="edge-2",
        equipment_id="pump-B",
        severity="warning",
        recommendation="Efficiency dropped by 15%, schedule inspection",
    )

    assert isinstance(wo, WorkOrder)
    assert wo.edge_id == "edge-2"
    assert wo.equipment_id == "pump-B"
    assert wo.severity == "warning"
    assert wo.title == "Degradation detected: pump-B"
    assert wo.description == "Efficiency dropped by 15%, schedule inspection"
    assert wo.source == "auto"


def test_generate_from_degradation_default_status():
    """status is NULL at construction time - SQLAlchemy applies 'open' on INSERT."""
    wo = generate_from_degradation("e2", "eq2", "minor", "recommendation")
    assert wo.status is None


def test_generate_from_degradation_default_assigned_to():
    wo = generate_from_degradation("e2", "eq2", "minor", "recommendation")
    assert wo.assigned_to is None


def test_generate_from_degradation_empty_recommendation():
    wo = generate_from_degradation("e2", "eq2", "minor", "")
    assert wo.description == ""


# ---------------------------------------------------------------------------
# Cross-checks
# ---------------------------------------------------------------------------

def test_both_generators_produce_distinct_titles():
    anomaly = generate_from_anomaly("e1", "chiller-01", "high", "pressure", "detail")
    degrad = generate_from_degradation("e2", "chiller-01", "high", "detail")

    assert anomaly.title.startswith("Inspection failed: ")
    assert degrad.title.startswith("Degradation detected: ")
    assert anomaly.title != degrad.title
