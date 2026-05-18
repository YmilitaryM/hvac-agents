from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, computed_field

_RATED_FREQUENCY_HZ = 50.0


class EquipmentStatus(str, Enum):
    OFF = "off"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAULT = "fault"
    MAINTENANCE = "maintenance"


class ChillerState(BaseModel):
    device_id: str
    capacity_rt: float
    status: EquipmentStatus = EquipmentStatus.OFF
    current_load_rt: float = 0.0
    power_kw: float = 0.0
    chw_supply_temp: float = 7.0
    chw_return_temp: float = 12.0
    cw_entering_temp: float = 30.0
    cw_leaving_temp: float = 35.0
    evap_flow_rate_lps: float = 0.0
    cond_flow_rate_lps: float = 0.0
    cumulative_starts: int = 0
    cumulative_run_hours: float = 0.0
    last_start_time: Optional[float] = None
    last_stop_time: Optional[float] = None

    @computed_field
    @property
    def is_running(self) -> bool:
        return self.status == EquipmentStatus.RUNNING

    @computed_field
    @property
    def plr(self) -> float:
        if self.capacity_rt <= 0:
            return 0.0
        return self.current_load_rt / self.capacity_rt

    @computed_field
    @property
    def instant_cop(self) -> float:
        if self.power_kw <= 0:
            return 0.0
        return (self.current_load_rt * 3.517) / self.power_kw

    @computed_field
    @property
    def surge_risk(self) -> float:
        if self.status != EquipmentStatus.RUNNING or self.plr <= 0:
            return 0.0
        cond_factor = max(0, (self.cw_entering_temp - 24) / 16)
        load_penalty = max(0, (0.4 - self.plr) / 0.4)
        risk = 0.3 * cond_factor + 0.7 * load_penalty
        return min(1.0, max(0.0, risk))


class PumpState(BaseModel):
    device_id: str
    status: EquipmentStatus = EquipmentStatus.OFF
    speed_hz: float = 0.0
    rated_power_kw: float = 37.0
    rated_flow_lps: float = 100.0
    rated_head_m: float = 32.0
    cumulative_starts: int = 0

    @computed_field
    @property
    def is_running(self) -> bool:
        return self.status == EquipmentStatus.RUNNING and self.speed_hz > 0

    @computed_field
    @property
    def power_kw(self) -> float:
        if self.speed_hz <= 0 or self.rated_power_kw <= 0:
            return 0.0
        return self.rated_power_kw * (self.speed_hz / _RATED_FREQUENCY_HZ) ** 3

    @computed_field
    @property
    def flow_lps(self) -> float:
        if self.speed_hz <= 0:
            return 0.0
        return self.rated_flow_lps * (self.speed_hz / _RATED_FREQUENCY_HZ)


class CoolingTowerState(BaseModel):
    device_id: str
    status: EquipmentStatus = EquipmentStatus.OFF
    fan_speed_hz: float = 0.0
    rated_fan_power_kw: float = 15.0
    water_in_temp: float = 35.0
    water_out_temp: float = 30.0
    water_flow_lps: float = 0.0

    @computed_field
    @property
    def is_running(self) -> bool:
        return self.status == EquipmentStatus.RUNNING

    @computed_field
    @property
    def fan_power_kw(self) -> float:
        if self.fan_speed_hz <= 0:
            return 0.0
        return self.rated_fan_power_kw * (self.fan_speed_hz / _RATED_FREQUENCY_HZ) ** 3


class PlantSnapshot(BaseModel):
    chillers: Dict[str, ChillerState] = Field(default_factory=dict)
    cooling_towers: Dict[str, CoolingTowerState] = Field(default_factory=dict)
    chw_pumps: Dict[str, PumpState] = Field(default_factory=dict)
    cw_pumps: Dict[str, PumpState] = Field(default_factory=dict)
    outdoor_wb_temp: float = 26.0
    outdoor_db_temp: float = 33.0
    timestamp: float = 0.0

    @computed_field
    @property
    def total_cooling_load_rt(self) -> float:
        return sum(c.current_load_rt for c in self.chillers.values())

    @computed_field
    @property
    def total_power_kw(self) -> float:
        chiller_power = sum(c.power_kw for c in self.chillers.values())
        tower_power = sum(t.fan_power_kw for t in self.cooling_towers.values())
        pump_power = sum(p.power_kw for p in self.chw_pumps.values())
        pump_power += sum(p.power_kw for p in self.cw_pumps.values())
        return chiller_power + tower_power + pump_power

    @computed_field
    @property
    def system_cop(self) -> float:
        if self.total_power_kw <= 0:
            return 0.0
        return (self.total_cooling_load_rt * 3.517) / self.total_power_kw

    @computed_field
    @property
    def running_chillers(self) -> List[ChillerState]:
        return [c for c in self.chillers.values() if c.is_running]

    @computed_field
    @property
    def tower_approach_temps(self) -> Dict[str, float]:
        return {
            tid: t.water_out_temp - self.outdoor_wb_temp
            for tid, t in self.cooling_towers.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlantSnapshot":
        return cls(
            chillers={c["device_id"]: ChillerState(**c) for c in data.get("chillers", [])},
            cooling_towers={t["device_id"]: CoolingTowerState(**t) for t in data.get("cooling_towers", [])},
            chw_pumps={p["device_id"]: PumpState(**p) for p in data.get("chw_pumps", [])},
            cw_pumps={p["device_id"]: PumpState(**p) for p in data.get("cw_pumps", [])},
            outdoor_wb_temp=data.get("outdoor_wb_temp", 26.0),
            outdoor_db_temp=data.get("outdoor_db_temp", 33.0),
            timestamp=data.get("timestamp", 0.0),
        )
