"""Feature extraction for RL contextual bandit."""

from typing import Any, Dict, Optional
import numpy as np

# Feature vector dimension
FEATURE_DIM = 12

# Feature names for interpretability
FEATURE_NAMES = [
    "load_ratio",            # current_load / 1500 (normalized, assume 3x500RT plant)
    "load_change_ratio",     # |predicted - current| / current
    "outdoor_wb_norm",       # outdoor_wb / 40
    "electricity_price_norm",  # price / 2.0
    "carbon_intensity_norm",   # intensity / 1.0
    "num_actions",            # number of strategy actions / 10
    "num_start_actions",      # number of start actions / 5
    "num_stop_actions",       # number of stop actions / 5
    "has_transition_plan",    # 1.0 if transition_plan exists, else 0.0
    "expected_cop_improvement",  # clip to [-0.2, 0.2]
    "energy_saving_norm",     # energy_saving / 500
    "carbon_saving_norm",     # carbon_saving / 200
]


def extract_features(
    strategy: Optional[Dict[str, Any]] = None,
    current_load_rt: float = 0.0,
    predicted_load_rt: float = 0.0,
    outdoor_wb_temp: float = 26.0,
    electricity_price: float = 0.8,
    carbon_intensity: float = 0.5,
) -> np.ndarray:
    """Extract normalized feature vector from strategy and context.

    Args:
        strategy: Strategy dict (optional — if None, uses partial context)
        current_load_rt: Current plant load in RT
        predicted_load_rt: Predicted load in RT
        outdoor_wb_temp: Outdoor wet bulb temp °C
        electricity_price: Electricity price per kWh
        carbon_intensity: Grid carbon intensity kgCO2/kWh

    Returns:
        numpy array of shape (FEATURE_DIM,) with values in roughly [0, 1] range
    """
    strategy = strategy or {}
    actions = strategy.get("actions", [])

    load_ratio = min(1.0, max(0.0, current_load_rt / 1500.0))

    load_change = abs(predicted_load_rt - current_load_rt) / max(current_load_rt, 1.0)
    load_change_ratio = min(1.0, load_change)

    outdoor_wb_norm = min(1.0, max(0.0, outdoor_wb_temp / 40.0))
    price_norm = min(1.0, electricity_price / 2.0)
    carbon_norm = min(1.0, carbon_intensity / 1.0)

    num_actions = min(1.0, len(actions) / 10.0) if actions else 0.0
    num_starts = min(1.0, sum(1 for a in actions if a.get("action") == "start") / 5.0) if actions else 0.0
    num_stops = min(1.0, sum(1 for a in actions if a.get("action") == "stop") / 5.0) if actions else 0.0

    has_transition = 1.0 if strategy.get("transition_plan") else 0.0

    cop_imp = strategy.get("expected_cop_improvement") or 0.0
    cop_imp = max(-0.2, min(0.2, cop_imp))

    energy_saving = (strategy.get("expected_energy_saving_kwh_per_h") or 0.0) / 500.0
    energy_saving = max(-1.0, min(1.0, energy_saving))

    carbon_saving = (strategy.get("expected_carbon_saving_kg_per_h") or 0.0) / 200.0
    carbon_saving = max(-1.0, min(1.0, carbon_saving))

    features = np.array([
        load_ratio, load_change_ratio, outdoor_wb_norm, price_norm, carbon_norm,
        num_actions, num_starts, num_stops, has_transition,
        cop_imp, energy_saving, carbon_saving,
    ], dtype=np.float64)

    return features
