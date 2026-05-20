import numpy as np


class RewardShaper:
    """Multi-objective reward shaping for MAPPO."""

    def __init__(self, weights: dict | None = None):
        self.weights = weights or {
            "cop": 0.35,
            "carbon": -0.20,
            "electric": -0.15,
            "load_match": 0.20,
            "anticipatory": 0.05,
            "comfort": -0.05,
        }

    def compute(
        self,
        obs: np.ndarray,
        action: np.ndarray,
        next_obs: np.ndarray,
        design_cop: float = 5.5,
    ) -> float:
        current_plr = obs[0]
        current_cop = (design_cop * current_plr) if current_plr > 0.1 else 0.0
        pred_load_15m = obs[5]
        pred_load_1h = obs[6]
        carbon_price = obs[9]
        electric_price = obs[10]
        chwst = action[0] if len(action) > 0 else 7.0

        comfort_penalty = max(0, chwst - 10.0) + max(0, 5.0 - chwst)
        cop_reward = (current_cop / design_cop) if design_cop > 0 else 0.0
        power_est = current_plr * 500.0
        carbon_penalty = (power_est * 0.0006 * carbon_price) / 100.0
        electric_penalty = (power_est * electric_price) / 500.0

        load_gap = abs(current_plr * 500.0 - pred_load_15m * 500.0) / (
            pred_load_15m * 500.0 + 1e-6
        )
        load_match_reward = max(0, 1.0 - load_gap)

        anticipatory_bonus = 0.0
        if abs(pred_load_1h - current_plr) / (current_plr + 1e-6) > 0.2:
            anticipatory_bonus = 0.1 if abs(action[0]) > 0.3 else -0.1

        reward = (
            self.weights["cop"] * cop_reward
            + self.weights["carbon"] * carbon_penalty
            + self.weights["electric"] * electric_penalty
            + self.weights["load_match"] * load_match_reward
            + self.weights["anticipatory"] * anticipatory_bonus
            + self.weights["comfort"] * comfort_penalty
        )
        return float(reward)
