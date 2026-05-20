# services/agent/tests/test_workorder.py
import pytest
from agent_service.workorder.lifecycle import can_transition, transition


class FakeWorkOrder:
    id = 1
    status = "open"
    resolved_at = None


def test_valid_transitions():
    assert can_transition("open", "acknowledged") is True
    assert can_transition("open", "rejected") is True
    assert can_transition("acknowledged", "in_progress") is True
    assert can_transition("in_progress", "resolved") is True
    assert can_transition("resolved", "closed") is True
    assert can_transition("resolved", "in_progress") is True  # reopen


def test_invalid_transitions():
    assert can_transition("open", "resolved") is False
    assert can_transition("closed", "in_progress") is False
    assert can_transition("rejected", "acknowledged") is False


def test_transition_mutates_status():
    wo = FakeWorkOrder()
    result = transition(wo, "acknowledged")
    assert wo.status == "acknowledged"
    assert result["from_status"] == "open"
    assert result["to_status"] == "acknowledged"


def test_transition_invalid_raises():
    wo = FakeWorkOrder()
    with pytest.raises(ValueError, match="Cannot transition"):
        transition(wo, "resolved")
