import pytest
from src.control.interlock import (
    InterlockStep,
    InterlockStepType,
    InterlockSequence,
    build_chiller_start_sequence,
    build_chiller_stop_sequence,
    validate_sequence,
)


class TestBuildStartSequence:
    def test_start_sequence_has_7_steps(self):
        """Build start sequence with tower => 7 steps."""
        seq = build_chiller_start_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
            tower_name="CT-1",
        )
        assert len(seq.steps) == 7

    def test_start_sequence_without_tower(self):
        """tower_name=None => fewer steps (6 instead of 7)."""
        seq = build_chiller_start_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
            tower_name=None,
        )
        assert len(seq.steps) == 6

    def test_start_sequence_pumps_before_chiller(self):
        """Pumps come before chiller start in the sequence."""
        seq = build_chiller_start_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
            tower_name="CT-1",
        )
        pump_indices = [
            i for i, s in enumerate(seq.steps)
            if s.step_type == InterlockStepType.START_PUMP
        ]
        chiller_index = next(
            i for i, s in enumerate(seq.steps)
            if s.step_type == InterlockStepType.START_CHILLER
        )
        assert all(p < chiller_index for p in pump_indices)

    def test_start_sequence_metadata(self):
        """Start sequence has correct metadata."""
        seq = build_chiller_start_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
        )
        assert seq.sequence_id == "start_CH-1"
        assert seq.device == "CH-1"
        assert seq.operation == "start"

    def test_start_sequence_valves_before_pumps(self):
        """Isolation valves open before pumps start."""
        seq = build_chiller_start_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
        )
        valve_indices = [
            i for i, s in enumerate(seq.steps)
            if s.step_type == InterlockStepType.OPEN_VALVE
        ]
        pump_indices = [
            i for i, s in enumerate(seq.steps)
            if s.step_type == InterlockStepType.START_PUMP
        ]
        # CHW valve (index 0) before CHW pump (index 1)
        # CW valve (index 2) before CW pump (index 3)
        assert valve_indices[0] < pump_indices[0]  # CHW valve before CHW pump
        assert valve_indices[1] < pump_indices[1]  # CW valve before CW pump


class TestBuildStopSequence:
    def test_stop_sequence_has_cooldown_wait(self):
        """Stop sequence includes 300s cooldown."""
        seq = build_chiller_stop_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
        )
        cooldown_step = next(
            s for s in seq.steps
            if s.wait_sec == 300.0
        )
        assert cooldown_step is not None
        assert cooldown_step.step_type == InterlockStepType.WAIT

    def test_stop_sequence_chiller_stops_first(self):
        """Chiller stops before pumps in stop sequence."""
        seq = build_chiller_stop_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
        )
        chiller_stop_idx = next(
            i for i, s in enumerate(seq.steps)
            if s.step_type == InterlockStepType.STOP_CHILLER
        )
        pump_stop_indices = [
            i for i, s in enumerate(seq.steps)
            if s.step_type == InterlockStepType.STOP_PUMP
        ]
        assert all(chiller_stop_idx < p for p in pump_stop_indices)

    def test_stop_sequence_with_tower(self):
        """Stop sequence with tower includes tower stop."""
        seq = build_chiller_stop_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
            tower_name="CT-1",
        )
        tower_steps = [
            s for s in seq.steps if s.device == "CT-1"
        ]
        assert len(tower_steps) == 1

    def test_stop_sequence_without_tower(self):
        """Stop sequence without tower has fewer steps."""
        seq = build_chiller_stop_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
            tower_name=None,
        )
        assert len(seq.steps) == 5

    def test_stop_sequence_metadata(self):
        """Stop sequence has correct metadata."""
        seq = build_chiller_stop_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
        )
        assert seq.sequence_id == "stop_CH-1"
        assert seq.device == "CH-1"
        assert seq.operation == "stop"


class TestValidateSequence:
    def test_validate_valid_start_sequence(self):
        """Valid start sequence => passes validation."""
        seq = build_chiller_start_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
        )
        is_valid, issues = validate_sequence(seq)
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_valid_stop_sequence(self):
        """Valid stop sequence => passes validation."""
        seq = build_chiller_stop_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
        )
        is_valid, issues = validate_sequence(seq)
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_empty_sequence(self):
        """Empty sequence => invalid."""
        seq = InterlockSequence(
            sequence_id="empty",
            device="test",
            operation="start",
            steps=[],
        )
        is_valid, issues = validate_sequence(seq)
        assert is_valid is False
        assert len(issues) > 0

    def test_validate_wrong_sequence_numbers(self):
        """Steps with wrong seq numbers => invalid."""
        steps = [
            InterlockStep(seq=1, step_type=InterlockStepType.START_PUMP,
                          device="P1", description="pump"),
            InterlockStep(seq=5, step_type=InterlockStepType.START_CHILLER,
                          device="CH-1", description="chiller"),
        ]
        seq = InterlockSequence(
            sequence_id="bad",
            device="CH-1",
            operation="start",
            steps=steps,
        )
        is_valid, issues = validate_sequence(seq)
        assert is_valid is False
        assert any("wrong sequence number" in issue for issue in issues)

    def test_validate_pump_after_chiller(self):
        """Pump started after chiller => invalid for start sequence."""
        steps = [
            InterlockStep(seq=1, step_type=InterlockStepType.START_CHILLER,
                          device="CH-1", description="chiller", check_condition="no_faults"),
            InterlockStep(seq=2, step_type=InterlockStepType.START_PUMP,
                          device="P1", description="pump"),
        ]
        seq = InterlockSequence(
            sequence_id="bad_order",
            device="CH-1",
            operation="start",
            steps=steps,
        )
        is_valid, issues = validate_sequence(seq)
        assert is_valid is False
        assert any("Pump started after chiller" in issue for issue in issues)

    def test_validate_chiller_without_flow_check(self):
        """Chiller start without flow check => invalid."""
        steps = [
            InterlockStep(seq=1, step_type=InterlockStepType.START_PUMP,
                          device="P1", description="pump"),
            InterlockStep(seq=2, step_type=InterlockStepType.START_CHILLER,
                          device="CH-1", description="chiller"),
        ]
        seq = InterlockSequence(
            sequence_id="no_flow",
            device="CH-1",
            operation="start",
            steps=steps,
        )
        is_valid, issues = validate_sequence(seq)
        assert is_valid is False
        assert any("without flow check" in issue for issue in issues)


class TestInterlockSequence:
    def test_sequence_total_duration(self):
        """Total wait time is correct."""
        seq = build_chiller_start_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
        )
        expected_duration = 5.0 + 10.0 + 5.0 + 10.0 + 30.0 + 0.0  # = 60.0
        assert seq.total_duration_sec == expected_duration

    def test_sequence_total_duration_with_tower(self):
        """Total wait time with tower is correct."""
        seq = build_chiller_start_sequence(
            chiller_name="CH-1",
            chw_pump_name="CHWP-1",
            cw_pump_name="CWP-1",
            tower_name="CT-1",
        )
        expected_duration = 5.0 + 10.0 + 5.0 + 10.0 + 5.0 + 30.0 + 0.0  # = 65.0
        assert seq.total_duration_sec == expected_duration
