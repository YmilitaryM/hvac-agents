import time
from typing import Optional

from .faults.injector import FaultInjector

KW_PER_RT = 3.517


def apply_active_faults(assembly, injector: FaultInjector, current_time: float):
    """Apply active faults to all equipment models in the assembly before simulation step.

    Iterates over every equipment category in the PlantAssembly and modifies
    model parameters in-place according to any active faults registered in
    the injector whose device_id matches.
    """
    # ---- Chillers ----
    for eq_id, ch in assembly.chillers.items():
        params = {
            "design_cop": ch.design_cop,
            "capacity_rt": ch.capacity_rt,
            "min_plr": ch.min_plr_base,
        }
        modified = injector.modify_model_params("CentrifugalChiller", eq_id, params, current_time)
        if modified != params:
            ch.design_cop = modified["design_cop"]
            ch.capacity_rt = modified["capacity_rt"]
            ch.min_plr_base = modified["min_plr"]

    # ---- Pumps ----
    for eq_id, pump in assembly.pumps.items():
        params = {"rated_power_kw": pump.rated_power_kw}
        modified = injector.modify_model_params("Pump", eq_id, params, current_time)
        if modified != params:
            pump.rated_power_kw = modified["rated_power_kw"]

    # ---- Cooling Towers ----
    for eq_id, ct in assembly.cooling_towers.items():
        params = {
            "design_heat_rejection_kw": ct.design_heat_rejection_kw,
            "design_approach": ct.design_approach,
        }
        modified = injector.modify_model_params("CoolingTower", eq_id, params, current_time)
        if modified != params:
            ct.design_heat_rejection_kw = modified.get("design_heat_rejection_kw", ct.design_heat_rejection_kw)
            ct.design_approach = modified.get("design_approach", ct.design_approach)

    # ---- Valves ----
    for eq_id, valve in assembly.valves.items():
        # Only ControlValve has a Cv parameter
        if hasattr(valve, "cv"):
            params = {"cv": valve.cv}
            modified = injector.modify_model_params("ControlValve", eq_id, params, current_time)
            if modified != params:
                valve.cv = modified["cv"]

    # ---- Pipes ----
    for eq_id, pipe in assembly.pipes.items():
        # PipeSegment stores roughness in meters; convert for the fault model
        roughness_mm = pipe.roughness_m * 1000.0
        params = {"roughness_mm": roughness_mm}
        modified = injector.modify_model_params("PipeSegment", eq_id, params, current_time)
        if modified != params:
            pipe.roughness_m = modified["roughness_mm"] / 1000.0


async def run_plant_snapshot(
    assembly,
    config: dict,
    outdoor_wb: float,
    outdoor_db: float,
    injector: Optional[FaultInjector] = None,
) -> dict:
    """Simple iteration: compute each equipment, propagate through pipes.

    If an *injector* is provided, active faults and disturbances are applied
    to equipment models and ambient conditions before the simulation step.
    """
    current_time = time.time()

    # Apply faults and disturbances before simulation
    if injector:
        apply_active_faults(assembly, injector, current_time)
        outdoor_wb, outdoor_db = injector.get_weather_modifier(outdoor_wb, outdoor_db, current_time)

    loads = config.get("chiller_loads_rt", {})
    t_chws = config.get("t_chw_setpoints", {})
    t_cws = config.get("t_cw_setpoints", {})

    chiller_results = {}
    total_power_kw = 0
    total_load_rt = 0

    for ch_id, ch in assembly.chillers.items():
        load_rt = loads.get(ch_id, ch.capacity_rt * 0.6)
        # Apply load-spike disturbances if injector is available
        if injector:
            load_rt = injector.get_load_modifier(load_rt, current_time)
        t_chw = t_chws.get(ch_id, 7.0)
        t_cw = t_cws.get(ch_id, 30.0)
        plr = load_rt / ch.capacity_rt if ch.capacity_rt > 0 else 0
        cop = ch.compute_cop(plr=plr, t_chw=t_chw, t_cw=t_cw)
        if cop > 0:
            power_kw = (load_rt * KW_PER_RT) / cop
        else:
            power_kw = 0
            load_rt = 0  # Surging chiller delivers no cooling
        chiller_results[ch_id] = {
            "device_id": ch_id,
            "name": ch.name,
            "status": "surging" if cop <= 0 else "running",
            "current_load_rt": load_rt,
            "plr": plr,
            "cop": cop,
            "power_kw": power_kw,
            "chw_supply_temp": t_chw,
            "cw_leaving_temp": t_cw + 5,
        }
        total_power_kw += power_kw
        total_load_rt += load_rt

    system_cop = (total_load_rt * KW_PER_RT) / total_power_kw if total_power_kw > 0 else 0

    return {
        "timestamp": 0,
        "total_cooling_load_rt": total_load_rt,
        "total_power_kw": total_power_kw,
        "system_cop": round(system_cop, 2),
        "outdoor_wb_temp": outdoor_wb,
        "outdoor_db_temp": outdoor_db,
        "chillers": chiller_results,
        "cooling_towers": {},
        "chw_pumps": {},
        "cw_pumps": {},
    }
