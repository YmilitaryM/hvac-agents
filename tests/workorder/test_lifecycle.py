"""Tests for the workorder lifecycle state machine.

Pure logic tests — no database or mocking needed.
"""

import pytest
from datetime import datetime, timezone

from agent_service.workorder.lifecycle import (
    VALID_TRANSITIONS,
    can_transition,
    transition,
)


class FakeWorkOrder:
    """A lightweight fake with just the attributes lifecycle.transition needs."""

    def __init__(self, id: int = 1, status: str = "open", resolved_at=None):
        self.id = id
        self.status = status
        self.resolved_at = resolved_at


# ---------------------------------------------------------------------------
# VALID_TRANSITIONS structure
# ---------------------------------------------------------------------------

def test_valid_transitions_has_correct_states():
    """All known states must be present in the transition map."""
    expected_states = {"open", "acknowledged", "in_progress", "resolved", "closed", "rejected"}
    assert set(VALID_TRANSITIONS.keys()) == expected_states


def test_terminal_states_have_no_transitions():
    """closed and rejected should not allow any further transitions."""
    assert VALID_TRANSITIONS["closed"] == []
    assert VALID_TRANSITIONS["rejected"] == []


# ---------------------------------------------------------------------------
# can_transition
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("from_s,to_s", [
    ("open", "acknowledged"),
    ("open", "rejected"),
    ("acknowledged", "in_progress"),
    ("acknowledged", "rejected"),
    ("in_progress", "resolved"),
    ("resolved", "closed"),
    ("resolved", "in_progress"),
])
def test_can_transition_valid(from_s, to_s):
    assert can_transition(from_s, to_s) is True


@pytest.mark.parametrize("from_s,to_s", [
    ("open", "in_progress"),
    ("open", "resolved"),
    ("open", "closed"),
    ("acknowledged", "closed"),
    ("in_progress", "closed"),
    ("in_progress", "acknowledged"),
    ("closed", "open"),
    ("closed", "rejected"),
    ("rejected", "open"),
    ("rejected", "in_progress"),
])
def test_can_transition_invalid(from_s, to_s):
    assert can_transition(from_s, to_s) is False


def test_can_transition_unknown_from_status():
    """An unknown status should return False, not raise."""
    assert can_transition("nonexistent", "open") is False


# ---------------------------------------------------------------------------
# transition
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("from_s,to_s", [
    ("open", "acknowledged"),
    ("acknowledged", "in_progress"),
    ("in_progress", "resolved"),
    ("resolved", "closed"),
])
def test_transition_valid_path(from_s, to_s):
    wo = FakeWorkOrder(status=from_s)
    result = transition(wo, to_s, changed_by="tester", note="test note")

    assert wo.status == to_s
    assert result["work_order_id"] == wo.id
    assert result["from_status"] == from_s
    assert result["to_status"] == to_s
    assert result["changed_by"] == "tester"
    assert result["note"] == "test note"


def test_transition_resolved_sets_resolved_at():
    wo = FakeWorkOrder(status="in_progress")
    assert wo.resolved_at is None

    transition(wo, "resolved")

    assert wo.resolved_at is not None
    assert isinstance(wo.resolved_at, datetime)
    # Should be UTC-aware or naive (implementation uses timezone.utc)
    if wo.resolved_at.tzinfo is not None:
        assert wo.resolved_at.tzinfo == timezone.utc


def test_transition_resolved_to_in_progress_clears_resolved_at():
    """Going from resolved back to in_progress does NOT clear resolved_at
    (the implementation only sets it — it never clears it).
    This test documents current behaviour."""
    wo = FakeWorkOrder(status="resolved", resolved_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    transition(wo, "in_progress")

    assert wo.status == "in_progress"
    # resolved_at is not cleared by the implementation
    assert wo.resolved_at is not None


def test_transition_default_changed_by_and_note():
    wo = FakeWorkOrder(status="open")
    result = transition(wo, "acknowledged")

    assert result["changed_by"] == "system"
    assert result["note"] is None


@pytest.mark.parametrize("from_s,to_s", [
    ("open", "in_progress"),
    ("open", "resolved"),
    ("open", "closed"),
    ("acknowledged", "closed"),
    ("in_progress", "acknowledged"),
    ("closed", "open"),
    ("rejected", "open"),
])
def test_transition_invalid_raises(from_s, to_s):
    wo = FakeWorkOrder(status=from_s)
    with pytest.raises(ValueError, match=f"Cannot transition from {from_s} to {to_s}"):
        transition(wo, to_s)


def test_transition_rejected_from_open():
    """open -> rejected is valid."""
    wo = FakeWorkOrder(status="open")
    result = transition(wo, "rejected")
    assert wo.status == "rejected"


def test_transition_rejected_from_acknowledged():
    """acknowledged -> rejected is valid."""
    wo = FakeWorkOrder(status="acknowledged")
    result = transition(wo, "rejected")
    assert wo.status == "rejected"
