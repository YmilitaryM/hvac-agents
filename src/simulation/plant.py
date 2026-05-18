from typing import Dict, List

from src.schemas.equipment import (
    ChillerState,
    CoolingTowerState,
    EquipmentStatus,
    PlantSnapshot,
    PumpState,
)
from src.simulation.chiller import CentrifugalChiller
from src.simulation.cooling_tower import CoolingTower
from src.simulation.pump import Pump

KW_PER_RT = 3.517


class ChillerPlant:
    """Chiller plant simulation — composes all equipment models"""

    def __init__(
        self,
        chillers: List[CentrifugalChiller],
        cooling_towers: List[CoolingTower],
        chw_pumps: List[Pump],
        cw_pumps: List[Pump],
    ):
        self.chillers = {c.name: c for c in chillers}
        self.cooling_towers = {t.name: t for t in cooling_towers}
        self.chw_pumps = {p.name: p for p in chw_pumps}
        self.cw_pumps = {p.name: p for p in cw_pumps}

    def snapshot(
        self, config: dict, outdoor_wb: float, outdoor_db: float
    ) -> PlantSnapshot:
        loads = config.get("chiller_loads", {})
        t_chws = config.get("chiller_t_chw", {})
        t_cws = config.get("chiller_t_cw", {})
        tower_speeds = config.get("tower_fan_speeds", {})
        chw_speeds = config.get("chw_pump_speeds", {})
        cw_speeds = config.get("cw_pump_speeds", {})

        # Compute chiller states
        chiller_states: Dict[str, ChillerState] = {}
        total_heat_rejection_kw = 0.0
        for name, ch in self.chillers.items():
            load_rt = loads.get(name, 0.0)
            if load_rt <= 0:
                chiller_states[name] = ChillerState(
                    device_id=name,
                    capacity_rt=ch.capacity_rt,
                    status=EquipmentStatus.OFF,
                    current_load_rt=0.0,
                )
                continue
            t_chw = t_chws.get(name, 7.0)
            t_cw = t_cws.get(name, 30.0)
            plr = load_rt / ch.capacity_rt
            cop = ch.compute_cop(plr=plr, t_chw=t_chw, t_cw=t_cw)
            if cop <= 0:
                raise ValueError(
                    f"{name} at PLR={plr:.2f}, T_cw={t_cw} C "
                    f"is in surge region"
                )
            power_kw = ch.compute_power_kw(load_rt, t_chw, t_cw)
            heat_rejection = (load_rt * KW_PER_RT) + power_kw
            total_heat_rejection_kw += heat_rejection
            chiller_states[name] = ChillerState(
                device_id=name,
                capacity_rt=ch.capacity_rt,
                status=EquipmentStatus.RUNNING,
                current_load_rt=load_rt,
                power_kw=power_kw,
                chw_supply_temp=t_chw,
            )

        # Compute tower states
        running_towers = [
            t
            for n, t in self.cooling_towers.items()
            if tower_speeds.get(n, 0) > 0
        ]
        n_towers = max(1, len(running_towers))
        tower_states: Dict[str, CoolingTowerState] = {}
        for name, tw in self.cooling_towers.items():
            speed = tower_speeds.get(name, 0.0)
            if speed <= 0:
                tower_states[name] = CoolingTowerState(
                    device_id=name,
                    status=EquipmentStatus.OFF,
                )
                continue
            heat_per_tower = total_heat_rejection_kw / n_towers
            outlet_temp = tw.compute_outlet_temp(
                heat_per_tower,
                tw.design_flow_lps,
                speed,
                outdoor_wb,
            )
            tower_states[name] = CoolingTowerState(
                device_id=name,
                status=EquipmentStatus.RUNNING,
                fan_speed_hz=speed,
                water_out_temp=outlet_temp,
                water_flow_lps=tw.design_flow_lps,
            )

        # Compute pump states
        def _make_pumps(speeds, pump_map):
            result: Dict[str, PumpState] = {}
            for name, p in pump_map.items():
                spd = speeds.get(name, 0.0)
                result[name] = PumpState(
                    device_id=name,
                    status=(
                        EquipmentStatus.RUNNING
                        if spd > 0
                        else EquipmentStatus.OFF
                    ),
                    speed_hz=spd,
                    rated_power_kw=p.rated_power_kw,
                    rated_flow_lps=p.rated_flow_lps,
                )
            return result

        return PlantSnapshot(
            chillers=chiller_states,
            cooling_towers=tower_states,
            chw_pumps=_make_pumps(chw_speeds, self.chw_pumps),
            cw_pumps=_make_pumps(cw_speeds, self.cw_pumps),
            outdoor_wb_temp=outdoor_wb,
            outdoor_db_temp=outdoor_db,
        )
