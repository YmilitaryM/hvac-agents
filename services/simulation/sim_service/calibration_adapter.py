"""Simulation calibration adapter.

Bridges the agent service's calibration factors into the simulation engine.
Allows the simulation to consume active calibration factors and adjust its
internal parameters accordingly, closing the digital twin feedback loop.
"""

from typing import Any, Dict, List


def apply_calibration_factors(
    factors: Dict[str, Any],
    sim_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply calibration factors to simulation parameters.

    Each factor contains:
      - parameter: the parameter name to adjust
      - original_value: the pre-calibration value
      - calibrated_value: the target calibrated value
      - method: "bias_correction" or "linear_regression"

    For bias_correction: param = param + (calibrated - original)
    For linear_regression: param = calibrated (direct substitution)

    Args:
        factors: Dict of {parameter_name: factor_dict} from calibration agent.
        sim_params: Current simulation input parameters.

    Returns:
        Adjusted simulation parameters dict.
    """
    adjusted = dict(sim_params)

    for param_name, factor in factors.items():
        method = factor.get("method", "bias_correction")
        original = float(factor["original_value"])
        calibrated = float(factor["calibrated_value"])

        if param_name not in adjusted:
            # Parameter not directly in sim_params — try common aliases
            aliases = _PARAM_ALIASES.get(param_name, [])
            for alias in aliases:
                if alias in adjusted:
                    param_name = alias
                    break
            else:
                # Add it as a new parameter
                adjusted[param_name] = calibrated
                continue

        current = float(adjusted[param_name])

        if method == "linear_regression":
            # Direct substitution: use the calibrated value
            adjusted[param_name] = calibrated
        elif method == "bias_correction":
            # Apply offset correction
            correction = calibrated - original
            adjusted[param_name] = current + correction
        else:
            # Unknown method — apply with 50% dampening
            correction = (calibrated - original) * 0.5
            adjusted[param_name] = current + correction

    return adjusted


def get_calibrated_sim_params(
    base_params: Dict[str, Any],
    active_factors: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Return calibrated simulation parameters.

    Convenience wrapper that applies active factors to base parameters.
    If no factors provided, returns base_params unchanged.

    Args:
        base_params: Base/original simulation parameters.
        active_factors: Active calibration factors (from agent service).

    Returns:
        Calibrated simulation parameters.
    """
    if not active_factors:
        return dict(base_params)

    return apply_calibration_factors(active_factors, base_params)


# Parameter name aliases mapping
# Maps calibration parameter names to possible simulation parameter names
_PARAM_ALIASES: Dict[str, List[str]] = {
    "rated_cop": ["chiller_rated_cop", "design_cop", "cop_rated"],
    "cop_at_full_load": ["cop_full_load", "design_full_load_cop"],
    "design_approach_k": ["tower_approach_k", "cooling_tower_approach", "ct_approach"],
    "design_head_m": ["pump_head_m", "pump_design_head", "head_design"],
    "power_kw": ["rated_power_kw", "design_power_kw"],
    "chw_supply_temp": ["chw_supply_setpoint", "chw_supply_temp_setpoint"],
    "cw_return_temp": ["cw_return_temp", "condenser_water_return_temp"],
    "cop": ["system_cop", "plant_cop"],
}


def extract_factors_from_agent_response(agent_response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract calibration factors from agent API response.

    Handles the response format from GET /api/calibration/status.

    Args:
        agent_response: Response dict from calibration status endpoint.

    Returns:
        Dict of {parameter_name: factor_dict} suitable for apply_calibration_factors.
    """
    active = agent_response.get("active_factors", {})
    if not active:
        return {}

    return {
        param: {
            "parameter": param,
            "original_value": float(info["original_value"]),
            "calibrated_value": float(info["calibrated_value"]),
            "adjustment_pct": float(info["adjustment_pct"]),
            "confidence": float(info["confidence"]),
            "method": info.get("method", "bias_correction"),
        }
        for param, info in active.items()
    }


def compute_adjusted_chiller_params(
    chiller_params: Dict[str, Any],
    calibration_factors: Dict[str, Any],
) -> Dict[str, Any]:
    """Specialized function for chiller parameter adjustment.

    Applies calibration factors specifically to chiller model parameters
    including COP curves, capacity, and part-load characteristics.

    Args:
        chiller_params: Chiller-specific simulation parameters.
        calibration_factors: Active calibration factors.

    Returns:
        Adjusted chiller parameters.
    """
    adjusted = apply_calibration_factors(calibration_factors, chiller_params)

    # If rated_cop was adjusted, propagate to related parameters
    if "rated_cop" in calibration_factors:
        cop_ratio = (
            float(calibration_factors["rated_cop"]["calibrated_value"])
            / float(calibration_factors["rated_cop"]["original_value"])
        )
        # Scale COP curve coefficients proportionally
        for key in ["cop_a0", "cop_a1", "cop_a2", "cop_curve_coeff_0",
                     "cop_curve_coeff_1", "cop_curve_coeff_2"]:
            if key in adjusted:
                adjusted[key] = round(float(adjusted[key]) * cop_ratio, 6)

    return adjusted
