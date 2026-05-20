import numpy as np

from agent_service.rl.multi_agent.action_mask import ActionMask
from agent_service.rl.multi_agent.mappo import HAS_TORCH, MultiAgentController
from agent_service.rl.multi_agent.reward_shaper import RewardShaper


def test_action_mask_from_milp_on():
    schedule = {"chiller_1": {"on": True, "target_load": 300}}
    masks = ActionMask.from_milp_schedule(schedule)
    assert np.array_equal(masks["chiller_1"], np.ones(1))


def test_action_mask_from_milp_off():
    schedule = {"chiller_2": {"on": False, "target_load": 0}}
    masks = ActionMask.from_milp_schedule(schedule)
    assert np.array_equal(masks["chiller_2"], np.zeros(1))


def test_action_mask_apply_constraints():
    actions = {"chiller_1": np.array([15.0])}
    limits = {"chiller_1": {"min": 5.0, "max": 12.0}}
    result = ActionMask.apply_constraints(actions, limits)
    assert result["chiller_1"][0] == 12.0


def test_action_mask_apply_constraints_min():
    actions = {"chiller_1": np.array([2.0])}
    limits = {"chiller_1": {"min": 5.0, "max": 12.0}}
    result = ActionMask.apply_constraints(actions, limits)
    assert result["chiller_1"][0] == 5.0


def test_reward_shaper_default_weights():
    shaper = RewardShaper()
    assert "cop" in shaper.weights
    assert abs(shaper.weights["cop"] - 0.35) < 1e-10


def test_reward_shaper_custom_weights():
    shaper = RewardShaper(weights={"cop": 0.5})
    assert shaper.weights["cop"] == 0.5
    assert "carbon" not in shaper.weights


def test_reward_shaper_compute():
    shaper = RewardShaper()
    obs = np.array([0.8, 7.0, 12.0, 30.0, 24.0, 0.75, 0.6, 0.5, 0.4, 58.5, 0.85, 0.0, 0.7, 5.0], dtype=np.float32)
    action = np.array([7.0])
    next_obs = np.array([0.78, 7.0, 12.0, 30.0, 24.0, 0.7, 0.6, 0.5, 0.4, 58.5, 0.85, 0.0, 0.7, 5.0], dtype=np.float32)
    reward = shaper.compute(obs, action, next_obs)
    assert isinstance(reward, float)
    assert -10.0 < reward < 10.0


def test_build_observation():
    controller = MultiAgentController({})
    current = {"plr": 0.8, "chwst": 7.0, "chwrt": 12.0, "cwst": 30.0, "ambient_wb": 24.0}
    predictions = {"load_15m": 0.75, "load_1h": 0.6, "load_4h": 0.5, "load_24h": 0.4}
    prices = {"carbon": 60.0, "electric": 0.9, "price_trend_4h": 0.1}
    peer_states = {"peer_plr_avg": 0.7, "peer_cop_avg": 5.2}
    obs = controller.build_observation(current, predictions, prices, peer_states)
    assert len(obs) == 14
    assert obs[0] == 0.8
    assert obs[9] == 60.0
    assert obs[13] == 5.2


def test_multi_agent_controller_no_torch():
    controller = MultiAgentController({"d1": {"obs_dim": 14, "act_dim": 1}})
    if not HAS_TORCH:
        actions = controller.get_actions({"d1": np.zeros(14, dtype=np.float32)})
        assert np.array_equal(actions["d1"], np.zeros(1))
        values = controller.get_values({"d1": np.zeros(14, dtype=np.float32)})
        assert values["d1"] == 0.0


def test_multi_agent_controller_with_torch():
    if not HAS_TORCH:
        return
    controller = MultiAgentController({"d1": {"obs_dim": 14, "act_dim": 1}})
    obs = np.zeros(14, dtype=np.float32)
    actions = controller.get_actions({"d1": obs})
    assert "d1" in actions
    assert actions["d1"].shape == (1,)
    values = controller.get_values({"d1": obs})
    assert isinstance(values["d1"], float)


def test_action_masking():
    if not HAS_TORCH:
        return
    controller = MultiAgentController({"d1": {"obs_dim": 14, "act_dim": 1}})
    obs = np.ones(14, dtype=np.float32)
    mask = {"d1": np.zeros(1)}  # mask out all actions
    actions = controller.get_actions({"d1": obs}, action_masks=mask)
    assert np.allclose(actions["d1"], np.zeros(1))
