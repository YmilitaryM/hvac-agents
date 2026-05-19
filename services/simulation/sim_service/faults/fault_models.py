"""Fault and disturbance data models for the simulation engine."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import uuid


class FaultType(str, Enum):
    SURGE = "surge"
    CAVITATION = "cavitation"
    VALVE_STICKING = "valve_sticking"
    SENSOR_FAILURE = "sensor_failure"
    FOULING = "fouling"
    RUST = "rust"
    DRIFT = "drift"
    REFRIGERANT_LEAK = "refrigerant_leak"


class DisturbanceType(str, Enum):
    EXTREME_WEATHER = "extreme_weather"
    GRID_FLUCTUATION = "grid_fluctuation"
    LOAD_SPIKE = "load_spike"
    COMM_LOSS = "comm_loss"


@dataclass
class EquipmentFault:
    device_id: str
    fault_type: FaultType
    severity: float  # 0.0 to 1.0
    onset_time: float = 0  # delay in seconds before fault activates
    duration: Optional[float] = None  # None = indefinite
    fault_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    injected_at: float = field(default_factory=lambda: __import__("time").time())


@dataclass
class ExternalDisturbance:
    disturbance_type: DisturbanceType
    magnitude: float  # 0.0 to 1.0
    onset_time: float = 0
    duration: Optional[float] = None
    dist_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    injected_at: float = field(default_factory=lambda: __import__("time").time())
