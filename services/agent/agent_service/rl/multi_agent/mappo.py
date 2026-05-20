import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.distributions import Normal

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class ActorCritic(nn.Module if HAS_TORCH else object):
    """Policy (Actor) + Value (Critic) network for MAPPO."""

    def __init__(self, obs_dim: int, act_dim: int, hidden: int = 128):
        if not HAS_TORCH:
            raise RuntimeError("torch is required for ActorCritic")
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
        )
        self.actor_mean = nn.Linear(hidden, act_dim)
        self.actor_logstd = nn.Parameter(torch.zeros(1, act_dim))
        self.critic = nn.Linear(hidden, 1)

    def forward(self, obs):
        features = self.shared(obs)
        mean = self.actor_mean(features)
        std = self.actor_logstd.exp().expand_as(mean)
        dist = Normal(mean, std)
        value = self.critic(features)
        return dist, value


class MultiAgentController:
    """Manages multiple PPO agents sharing a global critic."""

    def __init__(self, device_configs: dict[str, dict]):
        self.agents: dict[str, ActorCritic | None] = {}
        for device_id, cfg in device_configs.items():
            self.agents[device_id] = (
                ActorCritic(obs_dim=cfg["obs_dim"], act_dim=cfg["act_dim"])
                if HAS_TORCH
                else None
            )

    def get_actions(
        self,
        observations: dict[str, np.ndarray],
        action_masks: dict[str, np.ndarray] | None = None,
    ) -> dict[str, np.ndarray]:
        actions: dict[str, np.ndarray] = {}
        for device_id, obs in observations.items():
            agent = self.agents.get(device_id)
            if agent is None or not HAS_TORCH:
                actions[device_id] = np.zeros(1)
                continue
            with torch.no_grad():
                obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                dist, _ = agent(obs_tensor)
                action = dist.mean.numpy()[0]
                if action_masks and device_id in action_masks:
                    mask = action_masks[device_id]
                    action = action * mask
            actions[device_id] = action
        return actions

    def get_values(self, observations: dict[str, np.ndarray]) -> dict[str, float]:
        values: dict[str, float] = {}
        for device_id, obs in observations.items():
            agent = self.agents.get(device_id)
            if agent is None or not HAS_TORCH:
                values[device_id] = 0.0
                continue
            with torch.no_grad():
                obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                _, value = agent(obs_tensor)
                values[device_id] = float(value.item())
        return values

    @staticmethod
    def build_observation(
        current: dict,
        predictions: dict,
        prices: dict,
        peer_states: dict,
    ) -> np.ndarray:
        obs = np.array([
            current.get("plr", 0.0),
            current.get("chwst", 7.0),
            current.get("chwrt", 12.0),
            current.get("cwst", 30.0),
            current.get("ambient_wb", 24.0),
            predictions.get("load_15m", current.get("plr", 0.0)),
            predictions.get("load_1h", current.get("plr", 0.0)),
            predictions.get("load_4h", current.get("plr", 0.0)),
            predictions.get("load_24h", current.get("plr", 0.0)),
            prices.get("carbon", 58.5),
            prices.get("electric", 0.85),
            prices.get("price_trend_4h", 0.0),
            peer_states.get("peer_plr_avg", current.get("plr", 0.0)),
            peer_states.get("peer_cop_avg", 5.0),
        ], dtype=np.float32)
        return obs
