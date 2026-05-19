KW_PER_RT = 3.517


def run_plant_snapshot(assembly, config: dict, outdoor_wb: float, outdoor_db: float) -> dict:
    """Simple iteration: compute each equipment, propagate through pipes."""
    loads = config.get("chiller_loads_rt", {})
    t_chws = config.get("t_chw_setpoints", {})
    t_cws = config.get("t_cw_setpoints", {})

    chiller_results = {}
    total_power_kw = 0
    total_load_rt = 0

    for ch_id, ch in assembly.chillers.items():
        load_rt = loads.get(ch_id, ch.capacity_rt * 0.6)
        t_chw = t_chws.get(ch_id, 7.0)
        t_cw = t_cws.get(ch_id, 30.0)
        plr = load_rt / ch.capacity_rt if ch.capacity_rt > 0 else 0
        cop = ch.compute_cop(plr=plr, t_chw=t_chw, t_cw=t_cw)
        power_kw = (load_rt * KW_PER_RT) / cop if cop > 0 else 0
        chiller_results[ch_id] = {
            "device_id": ch_id,
            "name": ch.name,
            "status": "running",
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
