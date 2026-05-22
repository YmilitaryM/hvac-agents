"""Digital twin calibration data models.

Defines the core dataclasses for the calibration closed-loop system:
  - CalibrationPoint: single comparison between simulated and measured values
  - CalibrationRun: a full comparison run with aggregate MBE and CV(RMSE)
  - CalibrationFactor: a computed correction factor for a simulation parameter
  - CalibrationResult: the outcome of applying one or more calibration factors
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CalibrationPoint:
    """A single comparison between simulated and measured values.

    Attributes:
        timestamp: When the comparison was made.
        parameter: The parameter name (e.g. "cop", "chw_supply_temp", "power_kw").
        simulated_value: Value from the simulation/twin model.
        measured_value: Value from the real sensor/acquisition system.
        deviation_pct: (|sim - meas| / meas) * 100 as a percentage.
        sensor_id: Source sensor identifier for the measured value.
        equipment_id: The equipment this point belongs to.
    """
    timestamp: datetime
    parameter: str
    simulated_value: float
    measured_value: float
    deviation_pct: float
    sensor_id: str
    equipment_id: str


@dataclass
class CalibrationRun:
    """A complete calibration comparison run.

    Contains all comparison points for one time window, plus aggregate
    error metrics per ASHRAE Guideline 14.

    Attributes:
        id: Unique run identifier.
        plant_id: The chiller plant this run belongs to.
        timestamp: When the run was executed.
        points: All CalibrationPoint comparisons in this run.
        overall_mbe_pct: Mean Bias Error across all points/parameters.
        overall_cv_rmse_pct: Coefficient of Variation of RMSE across all points.
        is_compliant: Whether CV(RMSE) < 30% per ASHRAE G14 for hourly data.
    """
    id: str = field(default_factory=_new_id)
    plant_id: str = ""
    timestamp: datetime = field(default_factory=_utcnow)
    points: list[CalibrationPoint] = field(default_factory=list)
    overall_mbe_pct: float = 0.0
    overall_cv_rmse_pct: float = 0.0
    is_compliant: bool = True

    ASHRAE_G14_HOURLY_THRESHOLD = 30.0  # CV(RMSE) must be < 30% for hourly data

    def compute_compliance(self) -> bool:
        """Check ASHRAE Guideline 14 compliance."""
        return self.overall_cv_rmse_pct < self.ASHRAE_G14_HOURLY_THRESHOLD


@dataclass
class CalibrationFactor:
    """A computed correction factor to adjust a simulation parameter.

    Attributes:
        parameter: The parameter name being calibrated.
        original_value: The original (uncalibrated) value or coefficient.
        calibrated_value: The corrected value after calibration.
        adjustment_pct: Percentage change from original to calibrated.
        confidence: 0-1 score based on data quality and quantity.
        method: The calibration method used (bias_correction, linear_regression,
                or bayesian_update).
    """
    parameter: str
    original_value: float
    calibrated_value: float
    adjustment_pct: float
    confidence: float  # 0-1
    method: str  # "bias_correction", "linear_regression", "bayesian_update"


@dataclass
class CalibrationResult:
    """The result of applying calibration factors.

    Attributes:
        run: The CalibrationRun that triggered this calibration.
        factors: The list of CalibrationFactor objects that were computed.
        applied: Whether the factors were successfully applied.
        expected_improvement_pct: Predicted reduction in CV(RMSE) after application.
    """
    run: CalibrationRun
    factors: list[CalibrationFactor] = field(default_factory=list)
    applied: bool = False
    expected_improvement_pct: float = 0.0
