from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence


@dataclass
class CalibrationDataPoint:
    timestamp: datetime
    input_features: dict
    measured_output: float


@dataclass
class CalibrationResult:
    equipment_id: str
    curve_name: str
    original_params: dict
    calibrated_params: dict
    mape: float
    rmse: float
    sample_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseCalibrator(ABC):
    @abstractmethod
    def calibrate(self, data: Sequence[CalibrationDataPoint]) -> CalibrationResult: ...

    @abstractmethod
    def validate(self, data: Sequence[CalibrationDataPoint], params: dict) -> tuple[float, float]: ...
