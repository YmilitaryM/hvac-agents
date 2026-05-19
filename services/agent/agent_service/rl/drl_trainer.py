"""Offline DRL trainer - uses Simulation Engine RL API for environment interaction."""
import asyncio
import os
import httpx
from .drl_agent import PPOAgent


class DRLTrainer:
    """Trains the PPO agent by interacting with the Simulation Engine's RL API.

    Each training episode runs for `steps_per_episode` environment steps.
    The policy is updated after every episode using REINFORCE + baseline.
    """

    def __init__(self, sim_service_url: str = "http://localhost:8003",
                 model_dir: str = None):
        self.sim_url = sim_service_url.rstrip("/")
        self.model_dir = model_dir or os.environ.get("MODEL_STORAGE_PATH", "/tmp/models")
        os.makedirs(self.model_dir, exist_ok=True)
        self.agent = PPOAgent()
        self._training = False
        self._progress = {
            "episode": 0,
            "total_episodes": 0,
            "avg_reward": 0,
            "status": "idle",
        }

    def is_training(self) -> bool:
        return self._training

    def get_progress(self) -> dict:
        return self._progress

    async def train(self, plant_id: str, num_episodes: int = 100,
                    steps_per_episode: int = 168) -> dict:
        """Run offline training using Simulation Engine RL API.

        Args:
            plant_id: the plant to train against
            num_episodes: total training episodes
            steps_per_episode: env steps per episode (168h = 1 week)

        Returns:
            dict with training summary
        """
        self._training = True
        self._progress = {
            "episode": 0,
            "total_episodes": num_episodes,
            "avg_reward": 0,
            "status": "running",
        }

        all_episode_rewards = []
        consecutive_failures = 0

        async with httpx.AsyncClient() as client:
            for ep in range(num_episodes):
                # Reset environment
                try:
                    reset_resp = await client.post(
                        f"{self.sim_url}/api/simulation/rl/reset",
                        json={
                            "plant_id": plant_id,
                            "weather_hour": ep * steps_per_episode,
                        },
                    )
                except httpx.ConnectError:
                    consecutive_failures += 1
                    if consecutive_failures > 3:
                        self._progress["status"] = "failed"
                        self._training = False
                        return {"status": "failed", "error": "Simulation service unavailable"}
                    await asyncio.sleep(2)
                    continue

                if reset_resp.status_code != 200:
                    consecutive_failures += 1
                    if consecutive_failures > 3:
                        self._progress["status"] = "failed"
                        self._training = False
                        return {"status": "failed", "error": "Simulation RL API returned errors"}
                    continue
                consecutive_failures = 0
                reset_data = reset_resp.json()
                session_id = reset_data["session_id"]
                state = reset_data["state"]

                states = []
                raw_actions = []
                rewards = []
                next_states = []
                dones = []
                ep_reward = 0.0

                for step in range(steps_per_episode):
                    # Select action (returns action_dict + raw vector for training)
                    action_dict, raw_action = self.agent.select_action(state)

                    # Step environment
                    try:
                        step_resp = await client.post(
                            f"{self.sim_url}/api/simulation/rl/step",
                            json={
                                "session_id": session_id,
                                "action": action_dict,
                            },
                        )
                    except (httpx.ConnectError, httpx.TimeoutException):
                        consecutive_failures += 1
                        break

                    if step_resp.status_code != 200:
                        consecutive_failures += 1
                        break
                    step_data = step_resp.json()

                    next_state = step_data["state"]
                    reward = step_data["reward"]
                    done = step_data["done"]

                    # Store transition (raw_action in [-2, 2] space matches policy)
                    states.append(state)
                    raw_actions.append(raw_action)
                    rewards.append(reward)
                    next_states.append(next_state)
                    dones.append(float(done))

                    ep_reward += reward
                    state = next_state

                    if done:
                        break

                # Update policy after each episode
                if len(states) > 0:
                    self.agent.update(states, raw_actions, rewards, next_states, dones)
                    all_episode_rewards.append(ep_reward)

                # Update progress (trailing 10-episode average)
                window = all_episode_rewards[-10:]
                avg_r = sum(window) / len(window) if window else 0
                self._progress = {
                    "episode": ep + 1,
                    "total_episodes": num_episodes,
                    "avg_reward": round(float(avg_r), 2),
                    "latest_reward": round(float(ep_reward), 2),
                    "status": "running",
                }

                # Yield control to allow other tasks to run
                await asyncio.sleep(0)

        # Save the trained model
        self.agent.save(os.path.join(self.model_dir, "ppo_agent.pkl"))

        final_avg = (
            sum(all_episode_rewards) / len(all_episode_rewards)
            if all_episode_rewards else 0
        )
        self._progress = {
            "episode": num_episodes,
            "total_episodes": num_episodes,
            "avg_reward": round(float(final_avg), 2),
            "status": "completed",
        }
        self._training = False

        return {
            "status": "completed",
            "episodes": num_episodes,
            "avg_reward": round(float(final_avg), 2),
        }
