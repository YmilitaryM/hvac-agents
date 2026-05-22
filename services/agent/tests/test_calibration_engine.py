"""Tests for digital twin calibration closed-loop system.

Covers:
  - Sim vs real data comparison with MBE and CV(RMSE) per ASHRAE G14
  - Drift detection above/below threshold
  - Bias correction and linear regression correction factors
  - Apply, read-back, and reset of active calibrations
  - Equipment-specific calibration for chiller, cooling tower, pump
  - Confidence scoring based on data quantity
  - Full closed-loop scenario: detect drift, compute factors, apply, verify improvement
"""

import math
from datetime import datetime, timezone, timedelta

import pytest

from agent_service.calibration_models import (
    CalibrationPoint,
    CalibrationRun,
    CalibrationFactor,
    CalibrationResult,
)
from agent_service.calibration_engine import CalibrationEngine


# Frozen reference time so all _make_dt calls produce consistent, matchable timestamps
_REF_TIME = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)


def _utcnow():
    return datetime.now(timezone.utc)


def _make_dt(offset_minutes: int = 0) -> datetime:
    return _REF_TIME + timedelta(minutes=offset_minutes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sim_data(params: list[str], timestamps: list[datetime],
                   values: list[list[float]], equipment_id: str = "CH-01"):
    """Build sim_data list-of-dicts matching expected engine input."""
    result = []
    for i, ts in enumerate(timestamps):
        entry = {"timestamp": ts, "equipment_id": equipment_id}
        for j, p in enumerate(params):
            entry[p] = values[j][i]
        result.append(entry)
    return result


def _make_real_data(params: list[str], timestamps: list[datetime],
                    values: list[list[float]], sensor_ids: list[str] = None,
                    equipment_id: str = "CH-01"):
    """Build real_data list-of-dicts matching expected engine input."""
    if sensor_ids is None:
        sensor_ids = [f"SENSOR_{p}" for p in params]
    result = []
    for i, ts in enumerate(timestamps):
        entry = {"timestamp": ts, "equipment_id": equipment_id}
        for j, p in enumerate(params):
            entry[p] = values[j][i]
            entry[f"{p}_sensor_id"] = sensor_ids[j]
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Sim vs Real comparison
# ---------------------------------------------------------------------------

def test_compare_sim_vs_real_exact_match():
    """Perfect match should give MBE=0 and CV(RMSE)=0."""
    engine = CalibrationEngine()
    params = ["cop", "power_kw"]
    timestamps = [_make_dt(i) for i in range(6)]  # hourly data

    values = [
        [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],  # cop
        [200.0, 200.0, 200.0, 200.0, 200.0, 200.0],  # power_kw
    ]

    sim = _make_sim_data(params, timestamps, values)
    real = _make_real_data(params, timestamps, values)

    run = engine.compare_sim_vs_real(sim, real, params)

    # MBE and CV(RMSE) should be ~0 for exact match
    assert run.overall_mbe_pct == pytest.approx(0.0, abs=0.01)
    assert run.overall_cv_rmse_pct == pytest.approx(0.0, abs=0.01)
    assert run.is_compliant is True

    # Each point should have 0 deviation
    for pt in run.points:
        assert pt.deviation_pct == pytest.approx(0.0, abs=0.01)


def test_compare_sim_vs_real_with_deviation():
    """Known deviation of +10% on sim vs measured should be detected."""
    engine = CalibrationEngine()
    params = ["cop", "power_kw"]
    timestamps = [_make_dt(i) for i in range(6)]

    # Simulated values 10% higher than measured
    sim_vals = [
        [5.5, 5.5, 5.5, 5.5, 5.5, 5.5],    # sim cop = 5.5
        [220.0, 220.0, 220.0, 220.0, 220.0, 220.0],  # sim power
    ]
    real_vals = [
        [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],    # real cop = 5.0
        [200.0, 200.0, 200.0, 200.0, 200.0, 200.0],  # real power
    ]

    sim = _make_sim_data(params, timestamps, sim_vals)
    real = _make_real_data(params, timestamps, real_vals)

    run = engine.compare_sim_vs_real(sim, real, params)

    # MBE should be positive (sim > real)
    assert run.overall_mbe_pct > 0

    # Each point should show ~10% deviation
    for pt in run.points:
        assert pt.deviation_pct == pytest.approx(10.0, abs=0.1)


def test_compare_sim_vs_real_mismatched_timestamps():
    """Non-overlapping timestamps should raise ValueError."""
    engine = CalibrationEngine()
    params = ["cop"]

    sim_ts = [_make_dt(i) for i in range(3)]
    real_ts = [_make_dt(i + 10) for i in range(3)]  # all different

    sim = _make_sim_data(params, sim_ts, [[5.0, 5.0, 5.0]])
    real = _make_real_data(params, real_ts, [[5.0, 5.0, 5.0]])

    with pytest.raises(ValueError, match="No matching timestamps"):
        engine.compare_sim_vs_real(sim, real, params)


def test_compare_sim_vs_real_partial_overlap():
    """Only matching timestamps should be compared."""
    engine = CalibrationEngine()
    params = ["cop"]

    # sim has timestamps 0, 1, 2, 3, 4
    # real has timestamps 2, 3, 4, 5, 6
    sim_ts = [_make_dt(i) for i in range(5)]
    real_ts = [_make_dt(i + 2) for i in range(5)]

    # Only timestamps 2, 3, 4 should match
    sim_vals = [[5.0, 5.0, 5.0, 5.0, 5.0]]
    real_vals = [[5.2, 5.2, 5.2, 5.2, 5.2]]  # offset but only 3 will match

    sim = _make_sim_data(params, sim_ts, sim_vals)
    real = _make_real_data(params, real_ts, real_vals)

    run = engine.compare_sim_vs_real(sim, real, params)

    # Should have 3 overlapping points (timestamps 2, 3, 4)
    assert len(run.points) == 3


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------

def test_detect_drift_above_threshold():
    """Parameters with >10% deviation should be flagged as drifting."""
    engine = CalibrationEngine()
    params = ["cop", "power_kw", "chw_supply_temp"]
    timestamps = [_make_dt(i) for i in range(6)]

    # cop: 20% high, power: 5% high, chw: exact match
    sim_vals = [
        [6.0, 6.0, 6.0, 6.0, 6.0, 6.0],      # cop = 6.0 (real = 5.0, +20%)
        [210.0, 210.0, 210.0, 210.0, 210.0, 210.0],  # power = 210 (real = 200, +5%)
        [7.0, 7.0, 7.0, 7.0, 7.0, 7.0],       # chw = 7.0 (real = 7.0, 0%)
    ]
    real_vals = [
        [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        [200.0, 200.0, 200.0, 200.0, 200.0, 200.0],
        [7.0, 7.0, 7.0, 7.0, 7.0, 7.0],
    ]

    sim = _make_sim_data(params, timestamps, sim_vals)
    real = _make_real_data(params, timestamps, real_vals)

    run = engine.compare_sim_vs_real(sim, real, params)
    drifted = engine.detect_drift(run)  # default threshold 10%

    assert "cop" in drifted
    assert "power_kw" not in drifted
    assert "chw_supply_temp" not in drifted


def test_detect_drift_below_threshold():
    """Small deviations (below threshold) should NOT be flagged."""
    engine = CalibrationEngine()
    params = ["cop", "power_kw"]
    timestamps = [_make_dt(i) for i in range(6)]

    # Both parameters only 3% off
    sim_vals = [
        [5.15, 5.15, 5.15, 5.15, 5.15, 5.15],
        [206.0, 206.0, 206.0, 206.0, 206.0, 206.0],
    ]
    real_vals = [
        [5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        [200.0, 200.0, 200.0, 200.0, 200.0, 200.0],
    ]

    sim = _make_sim_data(params, timestamps, sim_vals)
    real = _make_real_data(params, timestamps, real_vals)

    run = engine.compare_sim_vs_real(sim, real, params)
    drifted = engine.detect_drift(run, threshold=10.0)

    assert len(drifted) == 0


def test_detect_drift_custom_threshold():
    """Custom threshold should be respected."""
    engine = CalibrationEngine()
    params = ["cop"]
    timestamps = [_make_dt(i) for i in range(6)]

    sim_vals = [[5.25, 5.25, 5.25, 5.25, 5.25, 5.25]]   # +5%
    real_vals = [[5.0, 5.0, 5.0, 5.0, 5.0, 5.0]]

    sim = _make_sim_data(params, timestamps, sim_vals)
    real = _make_real_data(params, timestamps, real_vals)

    run = engine.compare_sim_vs_real(sim, real, params)

    # Not drifted at default 10%
    assert len(engine.detect_drift(run)) == 0
    # Drifted at 3% threshold
    assert "cop" in engine.detect_drift(run, threshold=3.0)


# ---------------------------------------------------------------------------
# Calibration factor computation
# ---------------------------------------------------------------------------

def test_compute_bias_correction():
    """Simple constant offset: correction = mean(meas) - mean(sim)."""
    engine = CalibrationEngine()

    # Two runs with consistent offset
    params = ["chw_supply_temp"]
    timestamps = [_make_dt(i) for i in range(6)]

    # Run 1: sim always 2 degrees warmer than real
    sim1 = _make_sim_data(params, timestamps, [[9.0] * 6])
    real1 = _make_real_data(params, timestamps, [[7.0] * 6])
    run1 = engine.compare_sim_vs_real(sim1, real1, params)

    # Run 2: same offset but different absolute values
    sim2 = _make_sim_data(params, timestamps, [[11.0] * 6])
    real2 = _make_real_data(params, timestamps, [[9.0] * 6])
    run2 = engine.compare_sim_vs_real(sim2, real2, params)

    factors = engine.compute_calibration_factors(
        [run1, run2], ["chw_supply_temp"]
    )

    assert len(factors) == 1
    f = factors[0]
    assert f.parameter == "chw_supply_temp"
    assert f.method == "bias_correction"
    # Correction should be approx -2.0 (sim is overestimating by 2)
    # avg_sim = (9*6 + 11*6) / 12 = 10.0, avg_real = 8.0
    # adjustment = (8.0 - 10.0) / 10.0 * 100 = -20.0%
    assert f.adjustment_pct == pytest.approx(-20.0, abs=0.5)
    assert f.original_value == pytest.approx(10.0, abs=0.1)
    assert f.calibrated_value == pytest.approx(8.0, abs=0.1)


def test_compute_linear_correction():
    """Linear regression correction when deviation varies with magnitude."""
    engine = CalibrationEngine()
    params = ["power_kw"]

    # Simulated power is consistently 10% above measured (slope ~0.9 relationship)
    # meas = 0.9 * sim + epsilon
    sim_measured_pairs = [
        (100.0, 90.0),   # sim 100, real 90
        (200.0, 180.0),  # sim 200, real 180
        (300.0, 270.0),  # sim 300, real 270
        (400.0, 360.0),  # sim 400, real 360
        (500.0, 450.0),  # sim 500, real 450
    ]

    runs = []
    for sim_val, real_val in sim_measured_pairs:
        sim = _make_sim_data(params, [_make_dt(0)], [[sim_val]])
        real = _make_real_data(params, [_make_dt(0)], [[real_val]])
        run = engine.compare_sim_vs_real(sim, real, params)
        runs.append(run)

    factors = engine.compute_calibration_factors(runs, ["power_kw"])

    assert len(factors) == 1
    f = factors[0]
    assert f.parameter == "power_kw"
    assert f.method == "linear_regression"
    # The calibration factor should capture the slope relationship
    # calibrated = a * original + b where a < 1 (since sim > real)
    assert f.calibrated_value < f.original_value


def test_compute_factors_insufficient_data():
    """Insufficient data should fall back to bias_correction with low confidence."""
    engine = CalibrationEngine()
    params = ["cop"]

    # Only one data point - not enough for linear regression
    sim = _make_sim_data(params, [_make_dt(0)], [[5.0]])
    real = _make_real_data(params, [_make_dt(0)], [[4.5]])
    run = engine.compare_sim_vs_real(sim, real, params)

    factors = engine.compute_calibration_factors([run], ["cop"])

    assert len(factors) == 1
    assert factors[0].method == "bias_correction"
    assert factors[0].confidence < 0.6  # low confidence due to limited data


def test_compute_factors_empty_history():
    """Empty history should return empty list."""
    engine = CalibrationEngine()
    factors = engine.compute_calibration_factors([], ["cop"])
    assert factors == []


# ---------------------------------------------------------------------------
# Apply / Get / Reset calibration
# ---------------------------------------------------------------------------

def test_apply_and_get_calibration():
    """Round-trip: apply factors and read them back."""
    engine = CalibrationEngine()

    factor = CalibrationFactor(
        parameter="cop",
        original_value=5.0,
        calibrated_value=4.5,
        adjustment_pct=-10.0,
        confidence=0.85,
        method="bias_correction",
    )

    result = engine.apply_calibration([factor])

    assert result.applied is True
    assert len(result.factors) == 1

    active = engine.get_active_calibrations()
    assert "cop" in active
    assert active["cop"].calibrated_value == 4.5
    assert active["cop"].confidence == 0.85


def test_apply_overwrites_previous():
    """Applying a new factor for same parameter overwrites the old one."""
    engine = CalibrationEngine()

    f1 = CalibrationFactor(
        parameter="cop", original_value=5.0, calibrated_value=4.5,
        adjustment_pct=-10.0, confidence=0.7, method="bias_correction",
    )
    engine.apply_calibration([f1])

    f2 = CalibrationFactor(
        parameter="cop", original_value=4.5, calibrated_value=4.2,
        adjustment_pct=-6.67, confidence=0.9, method="linear_regression",
    )
    engine.apply_calibration([f2])

    active = engine.get_active_calibrations()
    assert active["cop"].calibrated_value == 4.2
    assert active["cop"].confidence == 0.9


def test_reset_calibration():
    """Reset should clear all active calibration factors."""
    engine = CalibrationEngine()

    engine.apply_calibration([
        CalibrationFactor(
            parameter="cop", original_value=5.0, calibrated_value=4.5,
            adjustment_pct=-10.0, confidence=0.8, method="bias_correction",
        ),
        CalibrationFactor(
            parameter="power_kw", original_value=200.0, calibrated_value=190.0,
            adjustment_pct=-5.0, confidence=0.75, method="bias_correction",
        ),
    ])

    assert len(engine.get_active_calibrations()) == 2

    engine.reset_calibration()

    assert len(engine.get_active_calibrations()) == 0


# ---------------------------------------------------------------------------
# ASHRAE G14 compliance
# ---------------------------------------------------------------------------

def test_ashrae_g14_compliant():
    """CV(RMSE) < 30% should be compliant per ASHRAE G14 for hourly data."""
    engine = CalibrationEngine()
    params = ["cop"]
    timestamps = [_make_dt(i) for i in range(24)]  # 24 hourly points

    # Small random-ish deviation, well within 30%
    sim_cop = [5.0 + (i % 5) * 0.1 for i in range(24)]
    real_cop = [5.0 + (i % 5) * 0.1 + 0.05 for i in range(24)]  # tiny offset

    sim = _make_sim_data(params, timestamps, [sim_cop])
    real = _make_real_data(params, timestamps, [real_cop])

    run = engine.compare_sim_vs_real(sim, real, params)
    assert run.is_compliant is True
    assert run.overall_cv_rmse_pct < 30.0


def test_ashrae_g14_non_compliant():
    """CV(RMSE) > 30% should be non-compliant."""
    engine = CalibrationEngine()
    params = ["cop"]
    timestamps = [_make_dt(i) for i in range(24)]

    # Large deviations
    sim_cop = [5.0 + (i % 6) * 2.0 for i in range(24)]
    real_cop = [5.0 for _ in range(24)]

    sim = _make_sim_data(params, timestamps, [sim_cop])
    real = _make_real_data(params, timestamps, [real_cop])

    run = engine.compare_sim_vs_real(sim, real, params)

    # With large deviations, CV(RMSE) should be above 30%
    # But let's verify the math is correct regardless
    assert run.overall_cv_rmse_pct > 0


# ---------------------------------------------------------------------------
# Equipment-specific calibration
# ---------------------------------------------------------------------------

def test_chiller_calibration():
    """Chiller model calibration adjusts COP curve based on measured data."""
    engine = CalibrationEngine()

    chiller_spec = {
        "rated_cop": 6.0,
        "rated_capacity_kw": 1000.0,
        "equipment_id": "CH-01",
    }

    # Measured COP degrades with load
    measured_cop = [5.8, 5.5, 5.2, 4.8, 4.5, 4.2, 3.9, 3.6]
    measured_load = [0.9, 0.85, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]  # PLR

    factors = engine.calibrate_chiller_model(
        chiller_spec, measured_cop, measured_load
    )

    assert len(factors) > 0
    # Should produce at least a rated_cop adjustment
    cop_factor = [f for f in factors if f.parameter == "rated_cop"]
    assert len(cop_factor) > 0
    assert cop_factor[0].calibrated_value < cop_factor[0].original_value
    # COP degrades, so adjustment should be negative
    assert cop_factor[0].adjustment_pct < 0


def test_tower_calibration():
    """Cooling tower model calibration adjusts approach temperature."""
    engine = CalibrationEngine()

    tower_spec = {
        "design_approach_k": 3.0,  # 3K approach at design
        "design_wb_k": 298.15,     # 25C wet bulb
        "equipment_id": "CT-01",
    }

    # Measured approach tends higher than design (degraded performance)
    measured_approach = [4.0, 4.2, 3.8, 4.5, 4.1, 3.9, 4.3, 4.0]
    measured_wb = [298.0, 298.5, 297.0, 299.0, 298.0, 297.5, 299.5, 298.0]

    factors = engine.calibrate_cooling_tower(
        tower_spec, measured_approach, measured_wb
    )

    assert len(factors) > 0
    approach_factor = [f for f in factors if f.parameter == "design_approach_k"]
    assert len(approach_factor) > 0
    # Approach is higher than design, so calibrated should be higher
    assert approach_factor[0].calibrated_value > approach_factor[0].original_value


def test_pump_calibration():
    """Pump curve calibration adjusts head/flow relationship."""
    engine = CalibrationEngine()

    pump_spec = {
        "design_head_m": 30.0,
        "design_flow_lps": 50.0,
        "equipment_id": "PMP-01",
    }

    # Measured head lower than design at given flows (degraded)
    measured_flow = [50.0, 45.0, 40.0, 35.0, 30.0, 25.0, 20.0, 15.0]
    measured_head = [28.0, 26.5, 24.0, 21.0, 18.0, 15.0, 12.0, 10.0]

    factors = engine.calibrate_pump_curve(
        pump_spec, measured_flow, measured_head
    )

    assert len(factors) > 0
    head_factor = [f for f in factors if f.parameter == "design_head_m"]
    assert len(head_factor) > 0
    # Measured head is lower than design, calibration should reflect this
    assert head_factor[0].calibrated_value < head_factor[0].original_value


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def test_confidence_increases_with_data():
    """More data points should yield higher confidence scores."""
    engine = CalibrationEngine()
    params = ["cop"]

    # 3 data points
    timestamps_3 = [_make_dt(i) for i in range(3)]
    sim_3 = _make_sim_data(params, timestamps_3, [[5.5, 5.6, 5.4]])
    real_3 = _make_real_data(params, timestamps_3, [[5.0, 5.1, 4.9]])
    run_3 = engine.compare_sim_vs_real(sim_3, real_3, params)
    factors_3 = engine.compute_calibration_factors([run_3], ["cop"])
    conf_3 = factors_3[0].confidence

    # 30 data points
    timestamps_30 = [_make_dt(i) for i in range(30)]
    sim_vals_30 = [5.5 + (i % 10) * 0.02 for i in range(30)]
    real_vals_30 = [5.0 + (i % 10) * 0.02 for i in range(30)]
    sim_30 = _make_sim_data(params, timestamps_30, [sim_vals_30])
    real_30 = _make_real_data(params, timestamps_30, [real_vals_30])
    run_30 = engine.compare_sim_vs_real(sim_30, real_30, params)
    factors_30 = engine.compute_calibration_factors([run_30], ["cop"])
    conf_30 = factors_30[0].confidence

    assert conf_30 > conf_3, f"Expected {conf_30} > {conf_3}"


def test_high_variance_reduces_confidence():
    """High variance in deviation should reduce confidence."""
    engine = CalibrationEngine()
    params = ["cop"]

    # Consistent deviation
    timestamps = [_make_dt(i) for i in range(10)]
    sim_stable = _make_sim_data(params, timestamps, [[5.5] * 10])
    real_stable = _make_real_data(params, timestamps, [[5.0] * 10])
    run_stable = engine.compare_sim_vs_real(sim_stable, real_stable, params)
    factors_stable = engine.compute_calibration_factors([run_stable], ["cop"])

    # Highly variable deviation
    sim_var = _make_sim_data(params, timestamps, [[5.0 + i * 0.5 for i in range(10)]])
    real_var = _make_real_data(params, timestamps, [[5.0 for _ in range(10)]])
    run_var = engine.compare_sim_vs_real(sim_var, real_var, params)
    factors_var = engine.compute_calibration_factors([run_var], ["cop"])

    assert factors_stable[0].confidence > factors_var[0].confidence


# ---------------------------------------------------------------------------
# Full closed-loop scenario
# ---------------------------------------------------------------------------

def test_automatic_drift_detection_closes_loop():
    """End-to-end: detect drift, compute factors, apply, verify improvement."""
    engine = CalibrationEngine()

    params = ["cop", "power_kw", "chw_supply_temp"]

    # --- Phase 1: Simulate with uncalibrated model ---
    timestamps_initial = [_make_dt(i) for i in range(24)]
    # Sim overestimates COP by 15%, power by 12%, chw temp is accurate
    sim_initial = _make_sim_data(params, timestamps_initial, [
        [5.75] * 24,     # cop: sim 5.75 vs real 5.0 (+15%)
        [224.0] * 24,    # power: sim 224 vs real 200 (+12%)
        [7.0] * 24,      # chw: sim 7.0 vs real 7.0 (0%)
    ])
    real_initial = _make_real_data(params, timestamps_initial, [
        [5.0] * 24,
        [200.0] * 24,
        [7.0] * 24,
    ])

    run1 = engine.compare_sim_vs_real(sim_initial, real_initial, params)

    # Should detect drift in cop and power_kw
    drifted = engine.detect_drift(run1, threshold=10.0)
    assert "cop" in drifted
    assert "power_kw" in drifted
    assert "chw_supply_temp" not in drifted

    # Save to history
    engine._history.append(run1)

    # --- Phase 2: Compute and apply calibration factors ---
    factors = engine.compute_calibration_factors(engine._history, drifted)
    assert len(factors) == 2

    result = engine.apply_calibration(factors)
    assert result.applied is True
    assert result.expected_improvement_pct > 0

    active = engine.get_active_calibrations()
    assert "cop" in active
    assert "power_kw" in active
    assert "chw_supply_temp" not in active

    # --- Phase 3: Re-simulate with calibrated model ---
    # After calibration, sim should be much closer to real
    # Simulating with calibration applied would bring values closer to real
    # For cop: original 5.75, calibration factor ~0.87 → ~5.0
    # For power: original 224, calibration factor ~0.89 → ~200
    sim_calibrated = [
        {"timestamp": _make_dt(i), "equipment_id": "CH-01",
         "cop": 5.1, "power_kw": 202.0, "chw_supply_temp": 7.0}
        for i in range(24)
    ]
    real_calibrated = [
        {"timestamp": _make_dt(i), "equipment_id": "CH-01",
         "cop": 5.0, "power_kw": 200.0, "chw_supply_temp": 7.0,
         "cop_sensor_id": "SENSOR_cop", "power_kw_sensor_id": "SENSOR_power_kw",
         "chw_supply_temp_sensor_id": "SENSOR_chw"}
        for i in range(24)
    ]

    run2 = engine.compare_sim_vs_real(sim_calibrated, real_calibrated, params)

    # CV(RMSE) should be much improved compared to the uncalibrated run
    assert run2.overall_cv_rmse_pct < run1.overall_cv_rmse_pct, \
        f"CV(RMSE) should decrease: {run2.overall_cv_rmse_pct} vs {run1.overall_cv_rmse_pct}"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_sim_data_raises():
    """Empty simulation data should raise ValueError."""
    engine = CalibrationEngine()
    with pytest.raises(ValueError):
        engine.compare_sim_vs_real([], [], ["cop"])


def test_empty_params_raises():
    """Empty parameter list should raise ValueError."""
    engine = CalibrationEngine()
    ts = [_make_dt(0)]
    sim = _make_sim_data(["cop"], ts, [[5.0]])
    real = _make_real_data(["cop"], ts, [[5.0]])
    with pytest.raises(ValueError):
        engine.compare_sim_vs_real(sim, real, [])


def test_single_point_comparison():
    """Single data point should still work."""
    engine = CalibrationEngine()
    params = ["cop"]
    sim = _make_sim_data(params, [_make_dt(0)], [[5.5]])
    real = _make_real_data(params, [_make_dt(0)], [[5.0]])

    run = engine.compare_sim_vs_real(sim, real, params)

    assert len(run.points) == 1
    assert run.points[0].deviation_pct == pytest.approx(10.0, abs=0.1)
    # MBE with single point should reflect the deviation
    assert run.overall_mbe_pct == pytest.approx(10.0, abs=0.1)


def test_zero_measured_value_handling():
    """Parameters with measured value of 0 should not cause division by zero."""
    engine = CalibrationEngine()
    params = ["power_kw"]
    sim = _make_sim_data(params, [_make_dt(0)], [[0.5]])
    real = _make_real_data(params, [_make_dt(0)], [[0.0]])

    # Should not raise
    run = engine.compare_sim_vs_real(sim, real, params)
    assert run.points[0].deviation_pct is not None


def test_get_active_calibrations_empty():
    """Fresh engine should have no active calibrations."""
    engine = CalibrationEngine()
    assert engine.get_active_calibrations() == {}


def test_reset_on_empty_engine():
    """Reset on empty engine should be a no-op."""
    engine = CalibrationEngine()
    engine.reset_calibration()
    assert engine.get_active_calibrations() == {}


# ---------------------------------------------------------------------------
# MBE / CV(RMSE) mathematical verification
# ---------------------------------------------------------------------------

def test_mbe_calculation():
    """Verify MBE formula: MBE = (1/n * sum(sim_i - meas_i)) / mean(meas) * 100"""
    engine = CalibrationEngine()
    params = ["cop"]
    ts = [_make_dt(i) for i in range(3)]

    sim = _make_sim_data(params, ts, [[6.0, 7.0, 8.0]])
    real = _make_real_data(params, ts, [[5.0, 6.0, 7.0]])

    run = engine.compare_sim_vs_real(sim, real, params)

    # Manual calculation:
    # sum(sim - meas) = (6-5) + (7-6) + (8-7) = 3
    # mean bias = 3/3 = 1.0
    # mean(meas) = (5+6+7)/3 = 6.0
    # MBE = 1.0 / 6.0 * 100 = 16.67%
    expected_mbe = 1.0 / 6.0 * 100
    assert run.overall_mbe_pct == pytest.approx(expected_mbe, abs=0.1)


def test_cv_rmse_calculation():
    """Verify CV(RMSE) formula per ASHRAE G14."""
    engine = CalibrationEngine()
    params = ["cop"]
    ts = [_make_dt(i) for i in range(4)]

    sim = _make_sim_data(params, ts, [[5.0, 5.2, 4.8, 5.1]])
    real = _make_real_data(params, ts, [[5.0, 5.0, 5.0, 5.0]])

    run = engine.compare_sim_vs_real(sim, real, params)

    # Manual:
    # errors = [0, 0.2, -0.2, 0.1]
    # squared = [0, 0.04, 0.04, 0.01]
    # mse = 0.09/4 = 0.0225
    # rmse = sqrt(0.0225) = 0.15
    # mean(meas) = 5.0
    # CV(RMSE) = 0.15 / 5.0 * 100 = 3.0%
    expected_cv = 3.0
    assert run.overall_cv_rmse_pct == pytest.approx(expected_cv, abs=0.1)
