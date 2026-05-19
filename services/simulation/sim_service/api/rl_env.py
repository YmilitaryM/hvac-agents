"""RL Environment API - exposes simulation as an OpenAI Gym-style env via HTTP."""
import time
import math
from fastapi import APIRouter, HTTPException, Request

from ..plant_builder import build_plant_from_services
from ..solver import run_plant_snapshot

router = APIRouter()

# In-memory environment state per session
_env_sessions: dict[str, dict] = {}
SESSION_TTL = 7200  # auto-expire sessions after 2 hours of inactivity


def _cleanup_expired_sessions(now: float):
    """Remove sessions that have been inactive beyond SESSION_TTL."""
    expired = [
        sid for sid, s in _env_sessions.items()
        if now - s.get("last_access", 0) > SESSION_TTL
    ]
    for sid in expired:
        del _env_sessions[sid]


# Reward weights (configurable)
DEFAULT_WEIGHTS = {
    "w_cop": 1.0,
    "w_power_deviation": 0.5,
    "w_start_stop": 0.1,
    "w_surge_risk": 0.3,
    "w_temp_violation": 0.5,
    "w_carbon": 0.2,
}


def _default_weather(hour: int) -> dict:
    """Generate weather for a given hour (0-8759)."""
    hour_of_day = hour % 24
    month = (hour // 730) % 12 + 1
    t_base = 28 + 8 * math.sin(2 * math.pi * (month - 1) / 12)
    t_daily = 6 * math.sin(2 * math.pi * (hour_of_day - 14) / 24)
    return {"db_temp": round(t_base + t_daily, 1), "wb_temp": round(t_base + t_daily - 7, 1)}


# Action space definition
ACTION_BOUNDS = {
    "t_chw_supply": (5.0, 12.0),          # °C
    "t_cw_inlet": (24.0, 35.0),            # °C
    "pump_frequency": (20.0, 50.0),         # Hz
    "tower_fan_frequency": (10.0, 50.0),    # Hz
    "valve_opening": (0.0, 1.0),            # 0-1
}


@router.post("/rl/reset")
async def rl_reset(data: dict, request: Request):
    """Reset the environment and return initial state.

    Body: {plant_id, weather_hour (0-8759), seed (optional)}
    Returns: {state: [12-dim vector], session_id, weather, action_bounds}
    """
    plant_id = data["plant_id"]
    weather_hour = data.get("weather_hour", 0)
    session_id = f"{plant_id}_{int(time.time())}"

    _env_sessions[session_id] = {
        "plant_id": plant_id,
        "weather_hour": weather_hour,
        "total_reward": 0.0,
        "steps": 0,
        "done": False,
        "last_action": None,
        "last_access": time.time(),
    }

    weather = _default_weather(weather_hour)

    return {
        "session_id": session_id,
        "state": _build_state(weather, None, weather_hour),
        "weather": weather,
        "action_bounds": ACTION_BOUNDS,
    }


@router.post("/rl/step")
async def rl_step(data: dict, request: Request):
    """Execute one environment step.

    Body: {session_id, action: {t_chw_supply, t_cw_inlet, pump_frequency,
           tower_fan_frequency, valve_opening, plr_allocation: {chiller_id: plr}}}
    Returns: {state: [...], reward: float, done: bool, info: {...}}
    """
    session_id = data["session_id"]
    action = data["action"]

    session = _env_sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found. Call /rl/reset first.")

    if session["done"]:
        raise HTTPException(400, "Episode is done. Call /rl/reset to start new episode.")

    session["last_access"] = time.time()
    _cleanup_expired_sessions(time.time())

    # Enforce action bounds
    for key, (lo, hi) in ACTION_BOUNDS.items():
        if key in action:
            action[key] = max(lo, min(hi, float(action[key])))

    plant_id = session["plant_id"]
    weather_hour = session["weather_hour"]
    weather = _default_weather(weather_hour)
    asset_url = request.app.state.asset_service_url
    env_url = request.app.state.env_service_url

    # Try to run simulation with the action as overrides
    try:
        assembly = await build_plant_from_services(plant_id, asset_url, env_url)
        if assembly:
            # Build per-chiller config from action
            plr_allocation = action.get("plr_allocation", {})
            config = {
                "chiller_loads_rt": {
                    ch_id: plr_allocation.get(ch_id, 0.75) * ch.capacity_rt
                    for ch_id, ch in assembly.chillers.items()
                },
                "t_chw_setpoints": {
                    ch_id: action.get("t_chw_supply", 7.0)
                    for ch_id in assembly.chillers
                },
                "t_cw_setpoints": {
                    ch_id: action.get("t_cw_inlet", 30.0)
                    for ch_id in assembly.chillers
                },
            }
            result = await run_plant_snapshot(
                assembly, config, weather["wb_temp"], weather["db_temp"]
            )
            snapshot = result
        else:
            snapshot = _simulate_snapshot(weather, action, weather_hour)
    except Exception:
        snapshot = _simulate_snapshot(weather, action, weather_hour)

    # Compute reward
    reward = _compute_reward(snapshot, action, session)

    # Advance weather
    weather_hour = (weather_hour + 1) % 8760
    session["weather_hour"] = weather_hour
    session["steps"] += 1
    session["total_reward"] += reward
    session["done"] = session["steps"] >= 8760  # max 1 year

    next_weather = _default_weather(weather_hour)
    next_state = _build_state(next_weather, snapshot, weather_hour, action)

    return {
        "state": next_state,
        "reward": round(reward, 4),
        "done": session["done"],
        "info": {
            "step": session["steps"],
            "total_reward": round(session["total_reward"], 4),
            "system_cop": snapshot.get("system_cop", 0),
            "total_power_kw": snapshot.get("total_power_kw", 0),
            "cooling_load_rt": snapshot.get("total_cooling_load_rt", 0),
        },
    }


def _build_state(weather: dict, snapshot: dict | None, weather_hour: int = 0,
                 action: dict | None = None) -> list:
    """Build 12-dim state vector.

    [db_temp, wb_temp, hour_sin, hour_cos, month_sin, month_cos,
     cop, power_kw, load_rt, plr_avg, pump_hz, tower_hz]
    """
    hour_of_day = weather_hour % 24
    month = (weather_hour // 730) % 12 + 1

    cop = snapshot.get("system_cop", 0) if snapshot else 0
    power = snapshot.get("total_power_kw", 0) if snapshot else 0
    load = snapshot.get("total_cooling_load_rt", 0) if snapshot else 0

    # Extract actual PLR, pump, and tower values from snapshot or action
    plr_avg = 0.75
    pump_hz = 50.0
    tower_hz = 50.0
    if snapshot:
        chillers = snapshot.get("chillers", {})
        if chillers:
            plr_values = [c.get("plr", 0.75) for c in chillers.values()]
            plr_avg = sum(plr_values) / len(plr_values) if plr_values else 0.75
    if action:
        pump_hz = action.get("pump_frequency", 50.0)
        tower_hz = action.get("tower_fan_frequency", 50.0)

    return [
        weather.get("db_temp", 33),
        weather.get("wb_temp", 26),
        math.sin(2 * math.pi * hour_of_day / 24),
        math.cos(2 * math.pi * hour_of_day / 24),
        math.sin(2 * math.pi * month / 12),
        math.cos(2 * math.pi * month / 12),
        round(cop, 2),
        round(power, 1),
        round(load, 1),
        round(plr_avg, 2),
        pump_hz,
        tower_hz,
    ]


def _compute_reward(snapshot: dict, action: dict, session: dict) -> float:
    """Compute reward: R = w1*COP - w2*power_deviation - w3*start_stop
       - w4*surge_risk - w5*temp_violation - w6*carbon"""
    w = DEFAULT_WEIGHTS

    cop = snapshot.get("system_cop", 0)
    power = snapshot.get("total_power_kw", 0)
    load_rt = snapshot.get("total_cooling_load_rt", 1)
    expected_power = load_rt * 3.517 / cop if cop > 0 else power
    power_deviation = abs(power - expected_power) / max(expected_power, 1.0)

    # Surge risk penalty
    surge_risk = snapshot.get("surge_risk", 0)

    # Temperature violation
    chw_supply = action.get("t_chw_supply", 7.0)
    temp_violation = max(0, chw_supply - 10.0)  # penalty if > 10°C

    # Start/stop penalty (if action changed significantly)
    last_action = session.get("last_action", action)
    start_stop = 0.0
    if last_action:
        prev_plr = last_action.get("plr_allocation", {}).get("ch-1", 0.75)
        curr_plr = action.get("plr_allocation", {}).get("ch-1", 0.75)
        plr_change = abs(curr_plr - prev_plr)
        if plr_change > 0.5:  # major change = likely start/stop
            start_stop = 1.0

    session["last_action"] = action

    # Carbon estimate: power * grid intensity (assume 0.5 kgCO2/kWh)
    carbon = power * 0.5

    return (
        w["w_cop"] * cop
        - w["w_power_deviation"] * power_deviation
        - w["w_start_stop"] * start_stop
        - w["w_surge_risk"] * surge_risk
        - w["w_temp_violation"] * temp_violation
        - w["w_carbon"] * carbon * 0.001  # scaled down
    )


def _simulate_snapshot(weather: dict, action: dict, weather_hour: int = 0) -> dict:
    """Fallback simulated snapshot for testing when solver is unavailable."""
    t_chw = action.get("t_chw_supply", 7.0)
    t_cw = action.get("t_cw_inlet", 30.0)
    hour_of_day = weather_hour % 24
    load_rt = 300 + 100 * math.sin(2 * math.pi * hour_of_day / 24)

    # Simple COP model: higher CHW temp = better COP
    cop_theoretical = t_chw / (t_cw - t_chw + 0.001) * 0.6
    cop = min(8, max(2, cop_theoretical))

    power_kw = load_rt * 3.517 / cop

    return {
        "system_cop": round(cop, 2),
        "total_power_kw": round(power_kw, 1),
        "total_cooling_load_rt": round(load_rt, 1),
        "surge_risk": 0.1 if cop > 4 else 0.6,
        "chillers": {},
    }
