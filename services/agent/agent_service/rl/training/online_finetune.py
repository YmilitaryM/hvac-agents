import logging

logger = logging.getLogger(__name__)


class OnlineFinetuner:
    """Low-learning-rate online adaptation from LIVE data."""

    def __init__(self, controller, learning_rate: float = 1e-5):
        self._controller = controller
        self._lr = learning_rate
        self._buffer: list[dict] = []
        self._max_buffer = 10000

    def add_experience(self, obs: dict, action: dict, reward: dict, next_obs: dict):
        self._buffer.append({
            "obs": obs,
            "action": action,
            "reward": reward,
            "next_obs": next_obs,
        })
        if len(self._buffer) > self._max_buffer:
            self._buffer = self._buffer[-self._max_buffer :]

    async def finetune_step(self):
        if len(self._buffer) < 128:
            return None
        batch = self._buffer[-128:]
        logger.debug(f"Online finetune: batch_size={len(batch)}, lr={self._lr}")
        return {"samples": len(batch), "lr": self._lr}
