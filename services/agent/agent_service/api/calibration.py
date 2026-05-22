"""Calibration API endpoints for digital twin closed-loop calibration.

Endpoints:
  POST /api/calibration/run       — Compare sim vs real data
  GET  /api/calibration/drift     — Check for parameter drift
  POST /api/calibration/compute   — Compute calibration factors
  POST /api/calibration/apply     — Apply calibration factors
  GET  /api/calibration/status    — Active factors + history
  POST /api/calibration/reset     — Reset all calibrations
  GET  /api/calibration/chiller/{id} — Chiller-specific calibration
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..calibration_engine import CalibrationEngine
from ..calibration_models import CalibrationFactor, CalibrationRun

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level engine instance (in-memory, MVP)
_engine = CalibrationEngine()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CompareRequest(BaseModel):
    sim_data: List[Dict[str, Any]] = Field(..., description="Simulation output data points")
    real_data: List[Dict[str, Any]] = Field(..., description="Real sensor data points")
    parameters: List[str] = Field(..., description="Parameters to compare (e.g. cop, power_kw)")


class DriftQuery(BaseModel):
    threshold: float = Field(default=10.0, description="Deviation threshold percentage")


class ComputeRequest(BaseModel):
    drifted_params: List[str] = Field(..., description="Parameters to compute factors for")
    history_limit: int = Field(default=50, description="Max history runs to use")


class ApplyRequest(BaseModel):
    factors: List[Dict[str, Any]] = Field(..., description="Calibration factors to apply")


class ChillerCalRequest(BaseModel):
    chiller_spec: Dict[str, Any] = Field(..., description="Design specs: rated_cop, rated_capacity_kw, etc.")
    measured_cop_series: List[float] = Field(..., description="Measured COP time series")
    measured_load_series: List[float] = Field(..., description="Measured load / PLR time series")


class TowerCalRequest(BaseModel):
    tower_spec: Dict[str, Any] = Field(..., description="Design specs: design_approach_k, design_wb_k, etc.")
    measured_approach_series: List[float] = Field(..., description="Measured approach temperature series")
    measured_wb_series: List[float] = Field(..., description="Measured wet-bulb temperature series")


class PumpCalRequest(BaseModel):
    pump_spec: Dict[str, Any] = Field(..., description="Design specs: design_head_m, design_flow_lps, etc.")
    measured_flow_series: List[float] = Field(..., description="Measured flow rate series")
    measured_head_series: List[float] = Field(..., description="Measured head series")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/calibration/run")
async def run_comparison(req: CompareRequest):
    """Run comparison between simulation and real sensor data.

    Returns a CalibrationRun with per-point deviations, aggregate MBE,
    CV(RMSE), and ASHRAE G14 compliance status.
    """
    try:
        run = _engine.compare_sim_vs_real(
            sim_data=req.sim_data,
            real_data=req.real_data,
            parameters=req.parameters,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "run": {
            "id": run.id,
            "plant_id": run.plant_id,
            "timestamp": run.timestamp.isoformat(),
            "point_count": len(run.points),
            "points": [
                {
                    "timestamp": pt.timestamp.isoformat(),
                    "parameter": pt.parameter,
                    "simulated_value": pt.simulated_value,
                    "measured_value": pt.measured_value,
                    "deviation_pct": pt.deviation_pct,
                    "sensor_id": pt.sensor_id,
                    "equipment_id": pt.equipment_id,
                }
                for pt in run.points
            ],
            "overall_mbe_pct": run.overall_mbe_pct,
            "overall_cv_rmse_pct": run.overall_cv_rmse_pct,
            "is_compliant": run.is_compliant,
            "ashrae_g14_threshold": CalibrationRun.ASHRAE_G14_HOURLY_THRESHOLD,
        }
    }


@router.get("/calibration/drift")
async def check_drift(threshold: float = Query(default=10.0, description="Drift threshold %")):
    """Check if any parameters in the latest run are drifting above threshold."""
    if not _engine._history:
        return {"drifted": [], "message": "No calibration runs available. Run a comparison first."}

    latest_run = _engine._history[-1]
    drifted = _engine.detect_drift(latest_run, threshold=threshold)

    # Compute per-parameter mean deviation for context
    param_deviations: dict[str, float] = {}
    for pt in latest_run.points:
        if pt.parameter not in param_deviations:
            param_deviations[pt.parameter] = 0.0
    for pt in latest_run.points:
        param_deviations.setdefault(pt.parameter, 0.0)
    # Recompute properly
    param_devs: dict[str, list[float]] = {}
    for pt in latest_run.points:
        param_devs.setdefault(pt.parameter, []).append(pt.deviation_pct)
    param_means = {
        p: round(sum(d) / len(d), 2) for p, d in param_devs.items()
    }

    return {
        "drifted": drifted,
        "threshold": threshold,
        "parameter_mean_deviations": param_means,
        "latest_run_id": latest_run.id,
    }


@router.post("/calibration/compute")
async def compute_factors(req: ComputeRequest):
    """Compute calibration factors for drifted parameters using historical runs."""
    if not _engine._history:
        raise HTTPException(status_code=400, detail="No calibration history. Run comparisons first.")

    history = _engine._history[-req.history_limit:] if req.history_limit > 0 else _engine._history

    factors = _engine.compute_calibration_factors(history, req.drifted_params)

    return {
        "factors": [
            {
                "parameter": f.parameter,
                "original_value": f.original_value,
                "calibrated_value": f.calibrated_value,
                "adjustment_pct": f.adjustment_pct,
                "confidence": f.confidence,
                "method": f.method,
            }
            for f in factors
        ],
        "count": len(factors),
        "history_runs_used": len(history),
    }


@router.post("/calibration/apply")
async def apply_factors(req: ApplyRequest):
    """Apply calibration factors to the active set."""
    factors = [
        CalibrationFactor(
            parameter=f["parameter"],
            original_value=float(f["original_value"]),
            calibrated_value=float(f["calibrated_value"]),
            adjustment_pct=float(f["adjustment_pct"]),
            confidence=float(f["confidence"]),
            method=f["method"],
        )
        for f in req.factors
    ]

    result = _engine.apply_calibration(factors)

    return {
        "applied": result.applied,
        "factor_count": len(result.factors),
        "expected_improvement_pct": result.expected_improvement_pct,
        "active_count": len(_engine.get_active_calibrations()),
    }


@router.get("/calibration/status")
async def calibration_status():
    """Get current active calibration factors and history summary."""
    active = _engine.get_active_calibrations()

    return {
        "active_factors": {
            param: {
                "original_value": f.original_value,
                "calibrated_value": f.calibrated_value,
                "adjustment_pct": f.adjustment_pct,
                "confidence": f.confidence,
                "method": f.method,
            }
            for param, f in active.items()
        },
        "active_count": len(active),
        "history_runs": len(_engine._history),
        "latest_run": {
            "id": _engine._history[-1].id,
            "timestamp": _engine._history[-1].timestamp.isoformat(),
            "overall_mbe_pct": _engine._history[-1].overall_mbe_pct,
            "overall_cv_rmse_pct": _engine._history[-1].overall_cv_rmse_pct,
            "is_compliant": _engine._history[-1].is_compliant,
        } if _engine._history else None,
    }


@router.post("/calibration/reset")
async def reset_calibration():
    """Reset all calibration factors and clear history."""
    _engine.reset_calibration()
    return {
        "status": "reset",
        "active_factors": 0,
        "history_runs": 0,
    }


@router.get("/calibration/chiller/{equipment_id}")
async def calibrate_chiller(
    equipment_id: str,
    rated_cop: float = Query(..., description="Design rated COP"),
    rated_capacity_kw: float = Query(default=1000.0, description="Design rated capacity in kW"),
):
    """Get chiller calibration guidance.

    Returns the current calibration factors for the specified chiller
    along with recommended actions based on measured vs design performance.

    For full calibration with measured data, use POST /calibration/chiller/calibrate.
    """
    active = _engine.get_active_calibrations()

    chiller_factors = {
        p: {
            "original_value": f.original_value,
            "calibrated_value": f.calibrated_value,
            "adjustment_pct": f.adjustment_pct,
            "confidence": f.confidence,
            "method": f.method,
        }
        for p, f in active.items()
        if p in ("rated_cop", "cop_at_full_load")
    }

    return {
        "equipment_id": equipment_id,
        "design_rated_cop": rated_cop,
        "active_calibrations": chiller_factors,
        "recommendation": (
            "Apply calibration factors to simulation model"
            if chiller_factors
            else "No active calibration. Run comparison and compute factors."
        ),
    }


@router.post("/calibration/chiller/calibrate")
async def run_chiller_calibration(req: ChillerCalRequest):
    """Run chiller-specific calibration using measured COP vs load data."""
    if len(req.measured_cop_series) != len(req.measured_load_series):
        raise HTTPException(
            status_code=400,
            detail="measured_cop_series and measured_load_series must have same length",
        )

    if len(req.measured_cop_series) < 3:
        raise HTTPException(
            status_code=400,
            detail="Need at least 3 data points for chiller calibration",
        )

    factors = _engine.calibrate_chiller_model(
        chiller_spec=req.chiller_spec,
        measured_cop_series=req.measured_cop_series,
        measured_load_series=req.measured_load_series,
    )

    return {
        "factors": [
            {
                "parameter": f.parameter,
                "original_value": f.original_value,
                "calibrated_value": f.calibrated_value,
                "adjustment_pct": f.adjustment_pct,
                "confidence": f.confidence,
                "method": f.method,
            }
            for f in factors
        ],
        "count": len(factors),
    }


@router.post("/calibration/tower/calibrate")
async def run_tower_calibration(req: TowerCalRequest):
    """Run cooling tower calibration using measured approach temperature data."""
    if len(req.measured_approach_series) != len(req.measured_wb_series):
        raise HTTPException(
            status_code=400,
            detail="measured_approach_series and measured_wb_series must have same length",
        )

    if len(req.measured_approach_series) < 3:
        raise HTTPException(
            status_code=400,
            detail="Need at least 3 data points for tower calibration",
        )

    factors = _engine.calibrate_cooling_tower(
        tower_spec=req.tower_spec,
        measured_approach_series=req.measured_approach_series,
        measured_wb_series=req.measured_wb_series,
    )

    return {
        "factors": [
            {
                "parameter": f.parameter,
                "original_value": f.original_value,
                "calibrated_value": f.calibrated_value,
                "adjustment_pct": f.adjustment_pct,
                "confidence": f.confidence,
                "method": f.method,
            }
            for f in factors
        ],
        "count": len(factors),
    }


@router.post("/calibration/pump/calibrate")
async def run_pump_calibration(req: PumpCalRequest):
    """Run pump curve calibration using measured flow/head data."""
    if len(req.measured_flow_series) != len(req.measured_head_series):
        raise HTTPException(
            status_code=400,
            detail="measured_flow_series and measured_head_series must have same length",
        )

    if len(req.measured_flow_series) < 3:
        raise HTTPException(
            status_code=400,
            detail="Need at least 3 data points for pump calibration",
        )

    factors = _engine.calibrate_pump_curve(
        pump_spec=req.pump_spec,
        measured_flow_series=req.measured_flow_series,
        measured_head_series=req.measured_head_series,
    )

    return {
        "factors": [
            {
                "parameter": f.parameter,
                "original_value": f.original_value,
                "calibrated_value": f.calibrated_value,
                "adjustment_pct": f.adjustment_pct,
                "confidence": f.confidence,
                "method": f.method,
            }
            for f in factors
        ],
        "count": len(factors),
    }
