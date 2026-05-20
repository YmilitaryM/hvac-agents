"""DRL control optimization API."""
import os
import asyncio
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Request
from common.auth import require_role, Role
from ..rl.drl_agent import PPOAgent
from ..rl.drl_trainer import DRLTrainer
from ..rl.drl_safety import DRLSafetyWrapper

router = APIRouter()

_agent = PPOAgent()
_safety = DRLSafetyWrapper()
_trainer: DRLTrainer = None
_trainer_lock = asyncio.Lock()


class TrainRequest(BaseModel):
    plant_id: str
    num_episodes: int = Field(default=100, ge=1, le=10000)
    steps_per_episode: int = Field(default=168, ge=1, le=8760)


class InferenceRequest(BaseModel):
    state: list[float] | None = None


async def _get_trainer(request: Request) -> DRLTrainer:
    global _trainer
    if _trainer is None:
        async with _trainer_lock:
            if _trainer is None:
                sim_url = getattr(request.app.state, "sim_service_url", "http://localhost:8003")
                _trainer = DRLTrainer(sim_service_url=sim_url)
    return _trainer


@router.post("/train")
async def start_training(
    request: Request,
    data: TrainRequest,
    user: dict = Depends(require_role(Role.ENGINEER, Role.ADMIN)),
):
    """Start offline DRL training."""
    trainer = await _get_trainer(request)
    if trainer.is_training():
        return {"status": "already_running", "progress": trainer.get_progress()}

    task = asyncio.create_task(trainer.train(
        plant_id=data.plant_id,
        num_episodes=data.num_episodes,
        steps_per_episode=data.steps_per_episode,
    ))
    task.add_done_callback(_log_training_done)
    return {"status": "started", "message": "Training launched in background"}


def _log_training_done(task: asyncio.Task):
    try:
        task.result()
    except Exception as e:
        import logging
        logging.getLogger("rl").error(f"Training failed: {e}")


@router.get("/status")
async def get_rl_status(request: Request):
    """Get DRL training and model status."""
    trainer = await _get_trainer(request)
    return {
        "training": trainer.get_progress(),
        "safety": _safety.get_stats(),
        "model": {
            "total_steps": _agent.total_steps,
            "state_dim": _agent.state_dim,
            "action_dim": _agent.action_dim,
        },
    }


@router.post("/inference")
async def rl_inference(data: InferenceRequest):
    """Run DRL inference to get optimal control action."""
    state = data.state or [33, 26, 0, 1, 0, 1, 5.0, 500, 300, 0.75, 50, 50]
    action, _raw = _agent.select_action(state, deterministic=True)
    safe_action, passed, reason = _safety.check_action(action, {
        "load_rt": state[8] if len(state) > 8 else 300,
        "cop": state[6] if len(state) > 6 else 5.0,
        "outdoor_wb_temp": state[1] if len(state) > 1 else 26.0,
    })
    return {
        "action": safe_action,
        "original_action": action if not passed else None,
        "safety_passed": passed,
        "safety_reason": reason,
    }


@router.get("/checkpoints")
async def list_checkpoints():
    """List saved model checkpoints."""
    model_dir = os.environ.get("MODEL_STORAGE_PATH", "/tmp/models")
    try:
        files = [f for f in os.listdir(model_dir) if f.endswith(".pkl")] if os.path.isdir(model_dir) else []
        return {"checkpoints": files, "model_dir": model_dir}
    except Exception:
        return {"checkpoints": [], "model_dir": model_dir}


# --- MAPPO multi-agent endpoints ---

_mappo_controller: object = None


def get_mappo_controller():
    global _mappo_controller
    if _mappo_controller is not None:
        return _mappo_controller
    try:
        from ..rl.multi_agent.mappo import HAS_TORCH, MultiAgentController
        if HAS_TORCH:
            _mappo_controller = MultiAgentController({})
        else:
            _mappo_controller = MultiAgentController({})
    except Exception:
        _mappo_controller = None
    return _mappo_controller


class MAPPOInferenceRequest(BaseModel):
    observations: dict[str, list[float]]
    device_configs: dict[str, dict] = {}
    action_masks: dict[str, list[float]] | None = None


class MAPPOValuesRequest(BaseModel):
    observations: dict[str, list[float]]


@router.post("/mappo/actions")
async def mappo_get_actions(data: MAPPOInferenceRequest):
    """Get MAPPO actions for multiple devices."""
    import numpy as np

    controller = get_mappo_controller()
    if controller is None or not hasattr(controller, "get_actions"):
        return {"actions": {}, "status": "mappo_unavailable"}

    observations = {
        did: np.array(obs, dtype=np.float32)
        for did, obs in data.observations.items()
    }
    action_masks = None
    if data.action_masks:
        action_masks = {
            did: np.array(mask, dtype=np.float32)
            for did, mask in data.action_masks.items()
        }

    actions = controller.get_actions(observations, action_masks)
    return {
        "actions": {did: act.tolist() for did, act in actions.items()},
        "status": "ok",
    }


@router.post("/mappo/values")
async def mappo_get_values(data: MAPPOValuesRequest):
    """Get value function estimates for multi-agent observations."""
    import numpy as np

    controller = get_mappo_controller()
    if controller is None or not hasattr(controller, "get_values"):
        return {"values": {}, "status": "mappo_unavailable"}

    observations = {
        did: np.array(obs, dtype=np.float32)
        for did, obs in data.observations.items()
    }
    values = controller.get_values(observations)
    return {"values": values, "status": "ok"}
