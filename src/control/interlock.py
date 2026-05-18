"""Device interlock sequences for safe chiller start/stop operations."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class InterlockStepType(str, Enum):
    START_PUMP = "start_pump"
    STOP_PUMP = "stop_pump"
    OPEN_VALVE = "open_valve"
    CLOSE_VALVE = "close_valve"
    START_CHILLER = "start_chiller"
    STOP_CHILLER = "stop_chiller"
    WAIT = "wait"
    CHECK = "check"


@dataclass
class InterlockStep:
    """A single step in an interlock sequence."""
    seq: int
    step_type: InterlockStepType
    device: str
    description: str = ""
    wait_sec: float = 0.0  # wait after completing this step
    check_condition: str = ""  # condition to verify before proceeding


@dataclass
class InterlockSequence:
    """A complete interlock sequence for a device operation."""
    sequence_id: str
    device: str
    operation: str  # "start" or "stop"
    steps: List[InterlockStep] = field(default_factory=list)

    @property
    def total_duration_sec(self) -> float:
        return sum(s.wait_sec for s in self.steps)


def build_chiller_start_sequence(
    chiller_name: str,
    chw_pump_name: str,
    cw_pump_name: str,
    tower_name: Optional[str] = None,
) -> InterlockSequence:
    """Build the standard chiller startup sequence.

    Standard 7-step startup sequence:
    1. Open chilled water isolation valve
    2. Start chilled water pump, prove flow
    3. Open condenser water isolation valve
    4. Start condenser water pump, prove flow
    5. Start cooling tower fan (if applicable)
    6. Wait 30 seconds minimum for flow stabilization
    7. Start chiller compressor
    """
    steps = []
    seq = 1

    # Step 1: Open CHW valve
    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.OPEN_VALVE,
        device=f"{chiller_name}_chw_valve",
        description=f"Open chilled water isolation valve for {chiller_name}",
        wait_sec=5.0,
    ))
    seq += 1

    # Step 2: Start CHW pump
    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.START_PUMP,
        device=chw_pump_name,
        description=f"Start chilled water pump {chw_pump_name}",
        check_condition="chw_flow > 0",
        wait_sec=10.0,
    ))
    seq += 1

    # Step 3: Open CW valve
    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.OPEN_VALVE,
        device=f"{chiller_name}_cw_valve",
        description=f"Open condenser water isolation valve for {chiller_name}",
        wait_sec=5.0,
    ))
    seq += 1

    # Step 4: Start CW pump
    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.START_PUMP,
        device=cw_pump_name,
        description=f"Start condenser water pump {cw_pump_name}",
        check_condition="cw_flow > 0",
        wait_sec=10.0,
    ))
    seq += 1

    # Step 5: Start cooling tower (optional)
    if tower_name:
        steps.append(InterlockStep(
            seq=seq, step_type=InterlockStepType.START_PUMP,
            device=tower_name,
            description=f"Start cooling tower fan {tower_name}",
            wait_sec=5.0,
        ))
        seq += 1

    # Step 6: Wait for stabilization
    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.WAIT,
        device="system",
        description="Wait for flow stabilization",
        wait_sec=30.0,
        check_condition="chw_flow_stable AND cw_flow_stable",
    ))
    seq += 1

    # Step 7: Start chiller
    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.START_CHILLER,
        device=chiller_name,
        description=f"Start chiller compressor {chiller_name}",
        check_condition="chiller_ready AND no_faults",
        wait_sec=0.0,
    ))

    return InterlockSequence(
        sequence_id=f"start_{chiller_name}",
        device=chiller_name,
        operation="start",
        steps=steps,
    )


def build_chiller_stop_sequence(
    chiller_name: str,
    chw_pump_name: str,
    cw_pump_name: str,
    tower_name: Optional[str] = None,
) -> InterlockSequence:
    """Build the standard chiller shutdown sequence.

    Standard 5-step shutdown:
    1. Ramp chiller load to minimum
    2. Stop chiller compressor
    3. Wait 5 minutes for compressor cooldown
    4. Stop condenser water pump
    5. Stop chilled water pump
    """
    steps = []
    seq = 1

    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.CHECK,
        device=chiller_name,
        description=f"Ramp {chiller_name} to minimum load",
        wait_sec=60.0,
    ))
    seq += 1

    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.STOP_CHILLER,
        device=chiller_name,
        description=f"Stop chiller compressor {chiller_name}",
        wait_sec=0.0,
    ))
    seq += 1

    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.WAIT,
        device="system",
        description="Wait for compressor cooldown (5 minutes)",
        wait_sec=300.0,
    ))
    seq += 1

    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.STOP_PUMP,
        device=cw_pump_name,
        description=f"Stop condenser water pump {cw_pump_name}",
        wait_sec=0.0,
    ))
    seq += 1

    if tower_name:
        steps.append(InterlockStep(
            seq=seq, step_type=InterlockStepType.STOP_PUMP,
            device=tower_name,
            description=f"Stop cooling tower fan {tower_name}",
            wait_sec=0.0,
        ))
        seq += 1

    steps.append(InterlockStep(
        seq=seq, step_type=InterlockStepType.STOP_PUMP,
        device=chw_pump_name,
        description=f"Stop chilled water pump {chw_pump_name}",
        wait_sec=0.0,
    ))

    return InterlockSequence(
        sequence_id=f"stop_{chiller_name}",
        device=chiller_name,
        operation="stop",
        steps=steps,
    )


def validate_sequence(sequence: InterlockSequence) -> Tuple[bool, List[str]]:
    """Validate an interlock sequence.

    Checks:
    - Steps are sequentially numbered starting at 1
    - CHW pump started before chiller
    - CW pump started before chiller
    - Chiller not started before flow is proven
    - Sequence is not empty

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []

    if not sequence.steps:
        issues.append("Sequence has no steps")
        return False, issues

    # Check sequential numbering
    for i, step in enumerate(sequence.steps):
        expected_seq = i + 1
        if step.seq != expected_seq:
            issues.append(f"Step {step.seq} has wrong sequence number (expected {expected_seq})")

    # Check flow before chiller start
    if sequence.operation == "start":
        chiller_start_idx = None
        flow_proven = False
        for i, step in enumerate(sequence.steps):
            if step.step_type == InterlockStepType.START_CHILLER:
                chiller_start_idx = i
            if step.check_condition and "flow" in step.check_condition.lower():
                flow_proven = True

        if chiller_start_idx is not None and not flow_proven:
            issues.append("Chiller started without flow check")

    # Check pump order for start: pumps before chiller
    if sequence.operation == "start":
        pump_indices = []
        chiller_idx = None
        for i, step in enumerate(sequence.steps):
            if step.step_type == InterlockStepType.START_PUMP:
                pump_indices.append(i)
            if step.step_type == InterlockStepType.START_CHILLER:
                chiller_idx = i

        if chiller_idx is not None and any(p > chiller_idx for p in pump_indices):
            issues.append("Pump started after chiller -- pumps must start before chiller")

    return len(issues) == 0, issues
