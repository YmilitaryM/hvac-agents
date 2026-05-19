from typing import Dict, List, Tuple, Optional
from .simulation.chiller import CentrifugalChiller


def surge_constraint(
    chiller: CentrifugalChiller, plr: float, t_cw: float
) -> Tuple[bool, str]:
    """Check if PLR is above surge boundary. PLR=0 (off) always passes."""
    if plr <= 0:
        return True, ""
    boundary = chiller.surge_boundary(t_cw)
    if plr < boundary:
        return False, (
            f"{chiller.name}: PLR={plr:.2f} below surge boundary "
            f"{boundary:.2f} at T_cw={t_cw}°C"
        )
    return True, ""


def min_runtime_constraint(
    device_name: str,
    action: str,
    last_start_time: Optional[float],
    last_stop_time: Optional[float],
    current_time: float,
    min_runtime: float = 1800.0,
    min_offtime: float = 900.0,
) -> Tuple[bool, str]:
    """Check minimum runtime / off-time constraints."""
    if action == "start":
        if last_stop_time is not None:
            elapsed = current_time - last_stop_time
            if elapsed < min_offtime:
                return False, (
                    f"{device_name}: cannot start, only {elapsed:.0f}s since last stop "
                    f"(min {min_offtime}s)"
                )
    elif action == "stop":
        if last_start_time is not None:
            elapsed = current_time - last_start_time
            if elapsed < min_runtime:
                return False, (
                    f"{device_name}: cannot stop, only {elapsed:.0f}s since last start "
                    f"(min {min_runtime}s)"
                )
    return True, ""


def motor_start_interval(
    device_name: str,
    current_time: float,
    recent_motor_starts: List[Tuple[str, float]],
    min_interval: float = 30.0,
) -> Tuple[bool, str]:
    """Ensure no two large motors start within min_interval seconds."""
    for other_name, start_time in recent_motor_starts:
        if other_name != device_name and (current_time - start_time) < min_interval:
            return False, (
                f"{device_name}: motor start too close to {other_name} "
                f"({current_time - start_time:.0f}s ago, min {min_interval}s)"
            )
    return True, ""


def capacity_balance(
    chiller_capacities: Dict[str, float],
    total_load_rt: float,
    margin: float = 0.1,
) -> Tuple[bool, str]:
    """Check total running capacity >= load * (1 + margin)."""
    total_capacity = sum(chiller_capacities.values())
    required = total_load_rt * (1 + margin)
    if total_capacity < required:
        return False, (
            f"Capacity shortfall: {total_capacity:.0f}RT available, "
            f"{required:.0f}RT required (load={total_load_rt:.0f}RT + {margin:.0%} margin)"
        )
    return True, ""


def check_all_constraints(
    chiller_loads: Dict[str, float],
    chillers: Dict[str, CentrifugalChiller],
    t_cw: float,
    current_time: float,
    recent_motor_starts: List[Tuple[str, float]],
    device_states: Optional[Dict[str, dict]] = None,
) -> List[str]:
    """Run all constraints, return list of failure messages (empty = all pass)."""
    failures = []
    device_states = device_states or {}

    for name, ch in chillers.items():
        load_rt = chiller_loads.get(name, 0.0)
        plr = load_rt / ch.capacity_rt if ch.capacity_rt > 0 else 0.0
        ok, msg = surge_constraint(ch, plr, t_cw)
        if not ok:
            failures.append(msg)

    total_capacity = {
        name: ch.capacity_rt
        for name, ch in chillers.items()
        if chiller_loads.get(name, 0) > 0
    }
    total_load = sum(chiller_loads.values())
    ok, msg = capacity_balance(total_capacity, total_load)
    if not ok:
        failures.append(msg)

    return failures
