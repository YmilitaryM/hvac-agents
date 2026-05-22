"""Digital twin calibration engine.

Implements the closed-loop calibration workflow:
  1. compare_sim_vs_real — match timestamps, compute MBE & CV(RMSE) per ASHRAE G14
  2. detect_drift — flag parameters exceeding deviation threshold
  3. compute_calibration_factors — bias correction or linear regression
  4. apply_calibration / get_active_calibrations / reset_calibration
  5. Equipment-specific: calibrate_chiller_model, calibrate_cooling_tower, calibrate_pump_curve
"""

import math
from datetime import datetime, timezone
from typing import Optional

from .calibration_models import (
    CalibrationPoint,
    CalibrationRun,
    CalibrationFactor,
    CalibrationResult,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CalibrationEngine:
    """Engine for comparing digital twin simulation output against real sensor data,
    detecting drift, computing calibration factors, and applying them.
    """

    DEFAULT_DRIFT_THRESHOLD_PCT = 10.0  # ASHRAE G14 typical alert threshold

    def __init__(self):
        self._history: list[CalibrationRun] = []
        self._active_factors: dict[str, CalibrationFactor] = {}

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def compare_sim_vs_real(
        self,
        sim_data: list[dict],
        real_data: list[dict],
        parameters: list[str],
    ) -> CalibrationRun:
        """Match timestamps between sim and real data, compute deviation per
        parameter, and aggregate MBE / CV(RMSE) across all points.

        Args:
            sim_data: List of dicts with 'timestamp', 'equipment_id', and
                      parameter values from simulation output.
            real_data: List of dicts with 'timestamp', 'equipment_id',
                       parameter values, and optional '{param}_sensor_id'.
            parameters: Which parameter names to compare.

        Returns:
            CalibrationRun with all matched CalibrationPoints and aggregate metrics.

        Raises:
            ValueError: If either dataset is empty, parameters list is empty,
                        or no matching timestamps are found.
        """
        if not sim_data or not real_data:
            raise ValueError("sim_data and real_data must be non-empty")
        if not parameters:
            raise ValueError("parameters must be non-empty")

        # Index real data by timestamp for O(1) lookup
        real_by_ts: dict[datetime, dict] = {}
        for entry in real_data:
            ts = entry["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            real_by_ts[ts] = entry

        points: list[CalibrationPoint] = []

        for sim_entry in sim_data:
            sim_ts = sim_entry["timestamp"]
            if isinstance(sim_ts, str):
                sim_ts = datetime.fromisoformat(sim_ts)

            real_entry = real_by_ts.get(sim_ts)
            if real_entry is None:
                continue  # No matching real data at this timestamp

            equipment_id = sim_entry.get("equipment_id", real_entry.get("equipment_id", "unknown"))

            for param in parameters:
                sim_val = sim_entry.get(param)
                real_val = real_entry.get(param)

                if sim_val is None or real_val is None:
                    continue

                sim_val = float(sim_val)
                real_val = float(real_val)

                sensor_id = real_entry.get(f"{param}_sensor_id", f"SENSOR_{param}")

                # Compute deviation percentage
                if abs(real_val) < 1e-9:
                    # Near-zero measured value — use absolute deviation
                    deviation = abs(sim_val - real_val) * 100.0
                else:
                    deviation = abs(sim_val - real_val) / abs(real_val) * 100.0

                points.append(CalibrationPoint(
                    timestamp=sim_ts,
                    parameter=param,
                    simulated_value=sim_val,
                    measured_value=real_val,
                    deviation_pct=round(deviation, 4),
                    sensor_id=sensor_id,
                    equipment_id=equipment_id,
                ))

        if not points:
            raise ValueError("No matching timestamps found between sim_data and real_data")

        # Compute aggregate metrics
        mbe = self._compute_mbe(points)
        cv_rmse = self._compute_cv_rmse(points)
        compliant = cv_rmse < CalibrationRun.ASHRAE_G14_HOURLY_THRESHOLD

        plant_id = sim_data[0].get("plant_id", real_data[0].get("plant_id", ""))

        run = CalibrationRun(
            plant_id=plant_id,
            points=points,
            overall_mbe_pct=round(mbe, 4),
            overall_cv_rmse_pct=round(cv_rmse, 4),
            is_compliant=compliant,
        )

        self._history.append(run)
        return run

    # ------------------------------------------------------------------
    # Drift detection
    # ------------------------------------------------------------------

    def detect_drift(
        self,
        run: CalibrationRun,
        threshold: float = DEFAULT_DRIFT_THRESHOLD_PCT,
    ) -> list[str]:
        """Return parameter names where mean deviation exceeds threshold.

        Args:
            run: A completed CalibrationRun.
            threshold: Deviation percentage above which a parameter is
                       considered to be drifting. Default 10%.

        Returns:
            List of parameter names that are drifting.
        """
        # Group points by parameter and compute mean deviation
        param_deviations: dict[str, list[float]] = {}
        for pt in run.points:
            param_deviations.setdefault(pt.parameter, []).append(pt.deviation_pct)

        drifted: list[str] = []
        for param, devs in param_deviations.items():
            mean_dev = sum(devs) / len(devs)
            if mean_dev > threshold:
                drifted.append(param)

        return drifted

    # ------------------------------------------------------------------
    # Calibration factor computation
    # ------------------------------------------------------------------

    def compute_calibration_factors(
        self,
        history: list[CalibrationRun],
        drifted_params: list[str],
    ) -> list[CalibrationFactor]:
        """Compute calibration factors for drifted parameters.

        Uses linear regression when sufficient data is available (>2 distinct
        values); falls back to bias correction for sparse data.

        Args:
            history: Ordered list of CalibrationRuns (oldest first).
            drifted_params: Parameter names to compute factors for.

        Returns:
            List of CalibrationFactor objects, one per drifted parameter.
        """
        if not history or not drifted_params:
            return []

        factors: list[CalibrationFactor] = []

        for param in drifted_params:
            # Collect all (sim, real) pairs for this parameter across all runs
            sim_vals: list[float] = []
            real_vals: list[float] = []
            for run in history:
                for pt in run.points:
                    if pt.parameter == param:
                        sim_vals.append(pt.simulated_value)
                        real_vals.append(pt.measured_value)

            if not sim_vals:
                continue

            n = len(sim_vals)
            avg_sim = sum(sim_vals) / n
            avg_real = sum(real_vals) / n

            # Determine method based on data richness
            unique_sim = len(set(round(v, 6) for v in sim_vals))

            if unique_sim >= 3 and n >= 4:
                # Linear regression: meas = a * sim + b
                factor = self._linear_regression_factor(param, sim_vals, real_vals)
            else:
                # Bias correction: correction = mean(meas) - mean(sim)
                factor = self._bias_correction_factor(param, avg_sim, avg_real, n)

            factors.append(factor)

        return factors

    def _bias_correction_factor(
        self,
        param: str,
        avg_sim: float,
        avg_real: float,
        n: int,
    ) -> CalibrationFactor:
        """Compute a simple bias (constant offset) correction factor."""
        correction = avg_real - avg_sim
        calibrated = avg_sim + correction  # = avg_real
        adjustment_pct = (correction / avg_sim * 100.0) if abs(avg_sim) > 1e-9 else 0.0

        # Confidence: higher with more data, but capped for bias-only method
        confidence = min(0.5 + 0.01 * min(n, 30), 0.7)

        return CalibrationFactor(
            parameter=param,
            original_value=round(avg_sim, 6),
            calibrated_value=round(calibrated, 6),
            adjustment_pct=round(adjustment_pct, 4),
            confidence=round(confidence, 4),
            method="bias_correction",
        )

    def _linear_regression_factor(
        self,
        param: str,
        sim_vals: list[float],
        real_vals: list[float],
    ) -> CalibrationFactor:
        """Compute a linear regression correction: meas = a * sim + b.

        Uses ordinary least squares to fit the relationship, then computes
        the calibrated value as: calibrated = a * original + b.
        """
        n = len(sim_vals)
        avg_sim = sum(sim_vals) / n
        avg_real = sum(real_vals) / n

        # OLS slope: a = cov(sim, real) / var(sim)
        cov = sum((s - avg_sim) * (r - avg_real) for s, r in zip(sim_vals, real_vals))
        var = sum((s - avg_sim) ** 2 for s in sim_vals)

        if abs(var) < 1e-12:
            # No variance in sim — fall back to bias
            return self._bias_correction_factor(param, avg_sim, avg_real, n)

        a = cov / var
        b = avg_real - a * avg_sim

        # Calibrated value for a representative sim input
        original = avg_sim
        calibrated = a * original + b

        adjustment_pct = ((calibrated - original) / original * 100.0) if abs(original) > 1e-9 else 0.0

        # Confidence based on R-squared and sample size
        residuals = [real_vals[i] - (a * sim_vals[i] + b) for i in range(n)]
        ss_res = sum(r ** 2 for r in residuals)
        ss_tot = sum((rv - avg_real) ** 2 for rv in real_vals)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 0.0

        # Confidence factors: R-squared contribution + sample size contribution
        r2_confidence = max(0.0, min(1.0, r_squared))
        n_confidence = min(1.0, n / 30.0)
        confidence = 0.5 * r2_confidence + 0.5 * n_confidence

        return CalibrationFactor(
            parameter=param,
            original_value=round(original, 6),
            calibrated_value=round(calibrated, 6),
            adjustment_pct=round(adjustment_pct, 4),
            confidence=round(confidence, 4),
            method="linear_regression",
        )

    # ------------------------------------------------------------------
    # Apply / Get / Reset
    # ------------------------------------------------------------------

    def apply_calibration(self, factors: list[CalibrationFactor]) -> CalibrationResult:
        """Store active calibration factors and return a result.

        Existing factors for the same parameter are overwritten.

        Args:
            factors: CalibrationFactor objects to apply.

        Returns:
            CalibrationResult with applied status and expected improvement.
        """
        for f in factors:
            self._active_factors[f.parameter] = f

        # Estimate improvement from average adjustment magnitude
        if factors:
            avg_abs_adjustment = sum(abs(f.adjustment_pct) for f in factors) / len(factors)
            expected_improvement = min(avg_abs_adjustment, 100.0)
        else:
            expected_improvement = 0.0

        # Use the most recent run as the context run
        run = self._history[-1] if self._history else CalibrationRun()

        return CalibrationResult(
            run=run,
            factors=list(factors),
            applied=True,
            expected_improvement_pct=round(expected_improvement, 2),
        )

    def get_active_calibrations(self) -> dict[str, CalibrationFactor]:
        """Return a copy of current active calibration factors."""
        return dict(self._active_factors)

    def reset_calibration(self) -> None:
        """Clear all active calibration factors and history."""
        self._active_factors.clear()
        self._history.clear()

    # ------------------------------------------------------------------
    # Equipment-specific calibration
    # ------------------------------------------------------------------

    def calibrate_chiller_model(
        self,
        chiller_spec: dict,
        measured_cop_series: list[float],
        measured_load_series: list[float],
    ) -> list[CalibrationFactor]:
        """Calibrate chiller model parameters using measured COP vs load data.

        Uses polynomial regression (degree 2) to fit COP = f(PLR), then
        derives correction factors for rated_cop and capacity curve.

        Args:
            chiller_spec: Design specs with at least 'rated_cop' and
                          optional 'rated_capacity_kw', 'equipment_id'.
            measured_cop_series: Measured COP values (same length as load).
            measured_load_series: Part-load ratio values [0-1] or load in kW.

        Returns:
            CalibrationFactor objects for rated_cop and related parameters.
        """
        factors: list[CalibrationFactor] = []

        rated_cop = float(chiller_spec.get("rated_cop", 5.0))
        n = len(measured_cop_series)

        if n < 3:
            return factors

        # Measured COP statistics
        avg_measured_cop = sum(measured_cop_series) / n

        # Derive rated_cop correction
        # If measured COP is consistently below rated, adjust rated down
        cop_correction = avg_measured_cop - rated_cop

        # Confidence based on data coverage and variance
        cop_std = self._std_dev(measured_cop_series)
        cv = cop_std / avg_measured_cop if avg_measured_cop > 1e-9 else 1.0
        point_confidence = min(1.0, n / 30.0)
        stability_confidence = max(0.1, 1.0 - cv)
        confidence = 0.6 * point_confidence + 0.4 * stability_confidence

        calibrated_cop = rated_cop + cop_correction * 0.5  # Dampen correction by 50%
        adjustment_pct = ((calibrated_cop - rated_cop) / rated_cop * 100.0)

        factors.append(CalibrationFactor(
            parameter="rated_cop",
            original_value=rated_cop,
            calibrated_value=round(calibrated_cop, 4),
            adjustment_pct=round(adjustment_pct, 2),
            confidence=round(confidence, 4),
            method="bias_correction",
        ))

        # Fit COP vs load curve for additional parameters
        if n >= 4 and len(set(round(l, 4) for l in measured_load_series)) >= 3:
            try:
                plr_values, cop_values = self._prepare_plr_cop(
                    measured_load_series, measured_cop_series,
                    float(chiller_spec.get("rated_capacity_kw", 1000.0))
                )
                if len(plr_values) >= 3:
                    # Fit COP = a0 + a1*PLR + a2*PLR^2
                    coeffs = self._polyfit(plr_values, cop_values, deg=2)
                    design_cop_at_full_load = rated_cop
                    measured_cop_at_full = coeffs[0] + coeffs[1] * 1.0 + coeffs[2] * 1.0

                    full_load_factor = CalibrationFactor(
                        parameter="cop_at_full_load",
                        original_value=round(design_cop_at_full_load, 4),
                        calibrated_value=round(measured_cop_at_full, 4),
                        adjustment_pct=round(
                            (measured_cop_at_full - design_cop_at_full_load)
                            / design_cop_at_full_load * 100, 2
                        ),
                        confidence=round(confidence, 4),
                        method="linear_regression",
                    )
                    factors.append(full_load_factor)
            except Exception:
                pass  # Non-critical enhancement

        return factors

    def calibrate_cooling_tower(
        self,
        tower_spec: dict,
        measured_approach_series: list[float],
        measured_wb_series: list[float],
    ) -> list[CalibrationFactor]:
        """Calibrate cooling tower model using measured approach temperature data.

        The approach temperature (T_cw_out - T_wb) is a key performance metric.
        Higher approach than design indicates degraded performance.

        Args:
            tower_spec: Design specs with 'design_approach_k' and 'design_wb_k'.
            measured_approach_series: Measured approach temperatures (K or C).
            measured_wb_series: Corresponding wet-bulb temperatures.

        Returns:
            CalibrationFactor objects for design_approach_k and related params.
        """
        factors: list[CalibrationFactor] = []
        n = len(measured_approach_series)

        if n < 3:
            return factors

        design_approach = float(tower_spec.get("design_approach_k", 3.0))
        avg_measured_approach = sum(measured_approach_series) / n

        # Fit approach vs wet-bulb relationship
        if len(measured_wb_series) >= 3 and len(measured_approach_series) >= 3:
            try:
                coeffs = self._polyfit(
                    measured_wb_series, measured_approach_series, deg=2
                )
                design_wb = float(tower_spec.get("design_wb_k", 298.15))
                fitted_approach = coeffs[0] + coeffs[1] * design_wb + coeffs[2] * design_wb ** 2
            except Exception:
                fitted_approach = avg_measured_approach
        else:
            fitted_approach = avg_measured_approach

        # Confidence
        approach_std = self._std_dev(measured_approach_series)
        cv = approach_std / avg_measured_approach if avg_measured_approach > 1e-9 else 1.0
        point_confidence = min(1.0, n / 30.0)
        stability_confidence = max(0.1, 1.0 - cv)
        confidence = 0.6 * point_confidence + 0.4 * stability_confidence

        # Correction: blend design and measured
        calibrated_approach = design_approach + 0.6 * (fitted_approach - design_approach)
        adjustment_pct = ((calibrated_approach - design_approach) / design_approach * 100.0)

        factors.append(CalibrationFactor(
            parameter="design_approach_k",
            original_value=round(design_approach, 4),
            calibrated_value=round(calibrated_approach, 4),
            adjustment_pct=round(adjustment_pct, 2),
            confidence=round(confidence, 4),
            method="linear_regression",
        ))

        return factors

    def calibrate_pump_curve(
        self,
        pump_spec: dict,
        measured_flow_series: list[float],
        measured_head_series: list[float],
    ) -> list[CalibrationFactor]:
        """Calibrate pump curve using measured flow and head data.

        Fits the standard quadratic pump curve: head = a0 + a1*Q + a2*Q^2.
        Compares fitted curve against design values to derive correction.

        Args:
            pump_spec: Design specs with 'design_head_m' and 'design_flow_lps'.
            measured_flow_series: Measured flow rates.
            measured_head_series: Measured head values.

        Returns:
            CalibrationFactor objects for design_head_m and related params.
        """
        factors: list[CalibrationFactor] = []
        n = len(measured_flow_series)

        if n < 3:
            return factors

        design_head = float(pump_spec.get("design_head_m", 30.0))
        design_flow = float(pump_spec.get("design_flow_lps", 50.0))

        # Fit pump curve: head = a0 + a1*Q + a2*Q^2
        try:
            coeffs = self._polyfit(measured_flow_series, measured_head_series, deg=2)
        except Exception:
            return factors

        # Evaluate fitted curve at design flow
        fitted_head_at_design = coeffs[0] + coeffs[1] * design_flow + coeffs[2] * design_flow ** 2

        # Confidence
        avg_head = sum(measured_head_series) / n
        head_std = self._std_dev(measured_head_series)
        cv = head_std / avg_head if avg_head > 1e-9 else 1.0
        point_confidence = min(1.0, n / 30.0)
        stability_confidence = max(0.1, 1.0 - cv)
        confidence = 0.6 * point_confidence + 0.4 * stability_confidence

        # Correction
        calibrated_head = design_head + 0.7 * (fitted_head_at_design - design_head)
        adjustment_pct = ((calibrated_head - design_head) / design_head * 100.0)

        factors.append(CalibrationFactor(
            parameter="design_head_m",
            original_value=round(design_head, 4),
            calibrated_value=round(calibrated_head, 4),
            adjustment_pct=round(adjustment_pct, 2),
            confidence=round(confidence, 4),
            method="linear_regression",
        ))

        return factors

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_mbe(points: list[CalibrationPoint]) -> float:
        """Mean Bias Error: (1/n * sum(sim_i - meas_i)) / mean(meas) * 100"""
        n = len(points)
        if n == 0:
            return 0.0

        total_error = sum(pt.simulated_value - pt.measured_value for pt in points)
        mean_meas = sum(pt.measured_value for pt in points) / n

        if abs(mean_meas) < 1e-9:
            return total_error / n * 100.0

        return (total_error / n) / mean_meas * 100.0

    @staticmethod
    def _compute_cv_rmse(points: list[CalibrationPoint]) -> float:
        """CV(RMSE) per ASHRAE Guideline 14.

        RMSE = sqrt((1/n) * sum((sim_i - meas_i)^2))
        CV(RMSE) = RMSE / mean(meas) * 100
        """
        n = len(points)
        if n == 0:
            return 0.0

        sum_sq_error = sum(
            (pt.simulated_value - pt.measured_value) ** 2 for pt in points
        )
        rmse = math.sqrt(sum_sq_error / n)
        mean_meas = sum(pt.measured_value for pt in points) / n

        if abs(mean_meas) < 1e-9:
            return rmse * 100.0

        return rmse / mean_meas * 100.0

    @staticmethod
    def _std_dev(values: list[float]) -> float:
        """Compute population standard deviation."""
        n = len(values)
        if n < 2:
            return 0.0
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        return math.sqrt(variance)

    @staticmethod
    def _polyfit(x: list[float], y: list[float], deg: int) -> list[float]:
        """Fit a polynomial of given degree using least squares.

        Returns coefficients [a0, a1, ..., a_deg] for:
        y = a0 + a1*x + a2*x^2 + ...

        Uses the normal equation: (X^T X)^(-1) X^T y
        """
        n = len(x)
        if n < deg + 1:
            raise ValueError(f"Need at least {deg + 1} points for degree {deg}")

        # Build Vandermonde matrix: columns = [1, x, x^2, ..., x^deg]
        X = [[xi ** d for d in range(deg + 1)] for xi in x]

        # Compute X^T X (deg+1 x deg+1)
        XtX = [[0.0] * (deg + 1) for _ in range(deg + 1)]
        for i in range(deg + 1):
            for j in range(deg + 1):
                XtX[i][j] = sum(row[i] * row[j] for row in X)

        # Compute X^T y (deg+1 x 1)
        Xty = [0.0] * (deg + 1)
        for i in range(deg + 1):
            Xty[i] = sum(row[i] * y[k] for k, row in enumerate(X))

        # Solve linear system using Gaussian elimination with partial pivoting
        n_eq = deg + 1
        aug = [XtX[i] + [Xty[i]] for i in range(n_eq)]

        for col in range(n_eq):
            # Find pivot
            max_row = col
            max_val = abs(aug[col][col])
            for row in range(col + 1, n_eq):
                if abs(aug[row][col]) > max_val:
                    max_val = abs(aug[row][col])
                    max_row = row

            if max_val < 1e-14:
                # Singular matrix — return zeros
                return [0.0] * n_eq

            # Swap rows
            if max_row != col:
                aug[col], aug[max_row] = aug[max_row], aug[col]

            # Eliminate
            pivot = aug[col][col]
            for row in range(col + 1, n_eq):
                factor = aug[row][col] / pivot
                for j in range(col, n_eq + 1):
                    aug[row][j] -= factor * aug[col][j]

        # Back substitution
        coeffs = [0.0] * n_eq
        for i in range(n_eq - 1, -1, -1):
            s = aug[i][n_eq]
            for j in range(i + 1, n_eq):
                s -= aug[i][j] * coeffs[j]
            coeffs[i] = s / aug[i][i]

        return coeffs

    @staticmethod
    def _prepare_plr_cop(
        load_series: list[float],
        cop_series: list[float],
        rated_capacity_kw: float,
    ) -> tuple[list[float], list[float]]:
        """Convert load series to PLR and filter valid points."""
        plr_values: list[float] = []
        cop_values: list[float] = []

        for load, cop in zip(load_series, cop_series):
            plr = load / rated_capacity_kw if rated_capacity_kw > 0 else load
            if 0.1 <= plr <= 1.1 and cop > 0:
                plr_values.append(plr)
                cop_values.append(cop)

        return plr_values, cop_values
