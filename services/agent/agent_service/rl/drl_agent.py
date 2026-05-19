"""PPO Agent for HVAC control optimization.

A simplified PPO-style agent using linear Gaussian policies (REINFORCE + baseline)
for 12-dim state, 5-dim continuous action space. Avoids heavy torch dependency.
"""
import os
import pickle
import numpy as np


class PPOAgent:
    """Simplified PPO agent with linear Gaussian policy.

    State dim: 12  (weather + system state)
    Action dim: 5  (t_chw_supply, t_cw_inlet, pump_frequency,
                     tower_fan_frequency, valve_opening)

    Uses a linear mean + learned log_std per action dimension.
    Internal action representation is in [-2, 2] space, then mapped
    to physical ranges via _raw_to_action.
    """

    def __init__(self, state_dim: int = 12, action_dim: int = 5, lr: float = 0.001):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr

        # Linear policy: W_mean (action_dim, state_dim), b_mean (action_dim,)
        self.W_mean = np.random.randn(action_dim, state_dim) * 0.01
        self.b_mean = np.zeros(action_dim)
        # Log std per action (exploration). log(1.0) = 0
        self.log_std = np.zeros(action_dim)

        # Value function: V(s) = w_v dot s + b_v
        self.w_v = np.random.randn(state_dim) * 0.01
        self.b_v = 0.0

        self.total_steps = 0

    def select_action(self, state: list[float], deterministic: bool = False) -> tuple[dict, list[float]]:
        """Select action given state.

        Returns:
            action_dict: physical action values
            raw_action: internal [-2, 2] action vector (for training storage)
        """
        s = np.array(state, dtype=np.float32)

        # Compute mean action via linear policy (in [-2, 2] space)
        means = np.clip(self.W_mean @ s + self.b_mean, -2.0, 2.0)

        if deterministic:
            actions_raw = means
        else:
            stds = np.exp(self.log_std)
            actions_raw = means + np.random.randn(self.action_dim) * stds

        # Convert internal representation to physical action dict
        action_dict = self._raw_to_action(actions_raw)

        return action_dict, actions_raw.tolist()

    def _raw_to_action(self, raw: np.ndarray) -> dict:
        """Convert raw [-2, 2] actions to actual physical ranges."""
        raw = np.clip(raw, -2.0, 2.0)
        # Map [-2, 2] -> [0, 1]
        normalized = (raw + 2.0) / 4.0

        return {
            "t_chw_supply": round(5.0 + normalized[0] * 7.0, 1),      # 5-12 °C
            "t_cw_inlet": round(24.0 + normalized[1] * 11.0, 1),       # 24-35 °C
            "pump_frequency": round(20.0 + normalized[2] * 30.0, 1),    # 20-50 Hz
            "tower_fan_frequency": round(10.0 + normalized[3] * 40.0, 1),  # 10-50 Hz
            "valve_opening": round(float(normalized[4]), 2),             # 0-1
        }

    def update(
        self,
        states: list,
        actions: list,
        rewards: list,
        next_states: list,
        dones: list,
    ) -> dict:
        """Simple policy gradient update (REINFORCE with baseline).

        Args:
            states: list of state vectors
            actions: list of raw action vectors (in [-2, 2] space)
            rewards: list of scalar rewards
            next_states: list of next state vectors
            dones: list of done flags (1=terminal, 0=not)

        Returns:
            dict with training metrics
        """
        s = np.array(states, dtype=np.float32)
        a = np.array(actions, dtype=np.float32)
        r = np.array(rewards, dtype=np.float32)
        ns = np.array(next_states, dtype=np.float32)

        # Compute discounted returns
        gamma = 0.99
        returns = np.zeros_like(r)
        running = 0.0
        for t in range(len(r) - 1, -1, -1):
            running = r[t] + gamma * running * (1.0 - dones[t])
            returns[t] = running

        # Normalize returns for stable training
        ret_std = returns.std()
        if ret_std > 0:
            returns = (returns - returns.mean()) / ret_std
        else:
            returns = returns - returns.mean()

        # Compute values (baseline) and advantages
        values = s @ self.w_v + self.b_v
        advantages = returns - values

        # Update value function (MSE gradient)
        self.w_v += self.lr * (s.T @ advantages) / len(states)
        self.b_v += self.lr * advantages.mean()

        # Update policy (REINFORCE gradient on mean parameters)
        for i in range(len(states)):
            mean_i = self.W_mean @ s[i] + self.b_mean
            error = a[i] - mean_i
            # Outer product: grad = advantage * (action - mean) outer state
            grad_w = np.outer(error, s[i])
            self.W_mean += self.lr * advantages[i] * grad_w * 0.1
            self.b_mean += self.lr * advantages[i] * error * 0.1

        self.total_steps += len(states)

        return {
            "mean_reward": float(r.mean()),
            "mean_return": float(returns.mean()),
            "value_loss": float((advantages ** 2).mean()),
            "total_steps": self.total_steps,
        }

    def save(self, path: str):
        """Save model weights to disk."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        data = {
            "W_mean": self.W_mean,
            "b_mean": self.b_mean,
            "log_std": self.log_std,
            "w_v": self.w_v,
            "b_v": self.b_v,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "total_steps": self.total_steps,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load(self, path: str):
        """Load model weights from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.W_mean = data["W_mean"]
        self.b_mean = data["b_mean"]
        self.log_std = data["log_std"]
        self.w_v = data["w_v"]
        self.b_v = data["b_v"]
        self.total_steps = data.get("total_steps", 0)
