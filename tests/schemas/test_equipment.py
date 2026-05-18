import pytest
from src.schemas.equipment import (
    EquipmentStatus, ChillerState, PumpState,
    CoolingTowerState, PlantSnapshot,
)


class TestChillerState:
    def test_chiller_state_defaults(self):
        s = ChillerState(device_id="chiller_1", capacity_rt=500)
        assert s.status == EquipmentStatus.OFF
        assert s.current_load_rt == 0.0
        assert s.chw_supply_temp == 7.0
        assert s.is_running is False

    def test_chiller_cop_calculation(self):
        s = ChillerState(
            device_id="chiller_1",
            capacity_rt=500,
            status=EquipmentStatus.RUNNING,
            current_load_rt=375,
            power_kw=75.0,
            chw_supply_temp=7.0,
            chw_return_temp=12.0,
            cw_entering_temp=30.0,
            cw_leaving_temp=35.0,
        )
        assert s.power_kw == 75.0
        assert abs(s.instant_cop - (375 * 3.517 / 75)) < 0.1

    def test_chiller_surge_risk(self):
        s = ChillerState(
            device_id="chiller_1",
            capacity_rt=500,
            status=EquipmentStatus.RUNNING,
            current_load_rt=100,       # 20% -- near surge
            chw_supply_temp=7.0,
            cw_entering_temp=33.0,     # high condensing temp
        )
        assert s.surge_risk > 0.5


class TestPumpState:
    def test_pump_state_defaults(self):
        p = PumpState(device_id="pump_1")
        assert p.status == EquipmentStatus.OFF
        assert p.speed_hz == 0.0
        assert p.is_running is False
        assert p.power_kw == 0.0
        assert p.flow_lps == 0.0

    def test_pump_affinity_power(self):
        p = PumpState(
            device_id="pump_1",
            status=EquipmentStatus.RUNNING,
            speed_hz=50.0,
            rated_power_kw=37.0,
        )
        assert p.is_running is True
        assert abs(p.power_kw - 37.0) < 0.01

    def test_pump_affinity_flow(self):
        p = PumpState(
            device_id="pump_1",
            status=EquipmentStatus.RUNNING,
            speed_hz=25.0,
            rated_flow_lps=100.0,
        )
        assert abs(p.flow_lps - 50.0) < 0.01

    def test_pump_zero_speed_not_running(self):
        p = PumpState(
            device_id="pump_1",
            status=EquipmentStatus.RUNNING,
            speed_hz=0.0,
        )
        assert p.is_running is False
        assert p.power_kw == 0.0


class TestCoolingTowerState:
    def test_tower_state_defaults(self):
        t = CoolingTowerState(device_id="tower_1")
        assert t.status == EquipmentStatus.OFF
        assert t.is_running is False
        assert t.fan_power_kw == 0.0

    def test_tower_fan_power(self):
        t = CoolingTowerState(
            device_id="tower_1",
            status=EquipmentStatus.RUNNING,
            fan_speed_hz=50.0,
            rated_fan_power_kw=15.0,
        )
        assert t.is_running is True
        assert abs(t.fan_power_kw - 15.0) < 0.01

    def test_tower_fan_power_half_speed(self):
        t = CoolingTowerState(
            device_id="tower_1",
            status=EquipmentStatus.RUNNING,
            fan_speed_hz=25.0,
            rated_fan_power_kw=15.0,
        )
        assert abs(t.fan_power_kw - 15.0 * (25/50)**3) < 0.01


class TestPlantSnapshot:
    def test_plant_snapshot_creation(self, sample_plant_params):
        p = sample_plant_params
        snap = PlantSnapshot(
            chillers={
                f"chiller_{i+1}": ChillerState(
                    device_id=f"chiller_{i+1}",
                    capacity_rt=p["chiller_capacity_rt"],
                    status=EquipmentStatus.RUNNING,
                    current_load_rt=350,
                    power_kw=70,
                )
                for i in range(p["num_chillers"])
            },
            cooling_towers={
                f"tower_{i+1}": CoolingTowerState(
                    device_id=f"tower_{i+1}", fan_speed_hz=40
                )
                for i in range(p["num_cooling_towers"])
            },
            chw_pumps={
                f"chw_pump_{i+1}": PumpState(
                    device_id=f"chw_pump_{i+1}", speed_hz=45
                )
                for i in range(p["num_chw_pumps"])
            },
            cw_pumps={
                f"cw_pump_{i+1}": PumpState(
                    device_id=f"cw_pump_{i+1}", speed_hz=45
                )
                for i in range(p["num_cw_pumps"])
            },
            outdoor_wb_temp=26.0,
            outdoor_db_temp=33.0,
        )
        assert snap.total_cooling_load_rt > 0
        assert len(snap.running_chillers) == 3

    def test_plant_snapshot_from_dict(self):
        data = {
            "chillers": [
                {"device_id": "chiller_1", "capacity_rt": 500,
                 "status": "running", "current_load_rt": 375, "power_kw": 75,
                 "chw_supply_temp": 7.0, "chw_return_temp": 12.0,
                 "cw_entering_temp": 30.0, "cw_leaving_temp": 35.0},
            ],
            "chw_pumps": [
                {"device_id": "chw_pump_1", "status": "running", "speed_hz": 45},
            ],
            "cw_pumps": [
                {"device_id": "cw_pump_1", "status": "running", "speed_hz": 40},
            ],
            "cooling_towers": [
                {"device_id": "tower_1", "status": "running", "fan_speed_hz": 35},
            ],
            "outdoor_wb_temp": 26.0,
            "outdoor_db_temp": 33.0,
        }
        snap = PlantSnapshot.from_dict(data)
        assert snap.chillers["chiller_1"].status == EquipmentStatus.RUNNING
        assert snap.total_cooling_load_rt == 375

    def test_tower_approach_temps(self):
        snap = PlantSnapshot(
            cooling_towers={
                "tower_1": CoolingTowerState(
                    device_id="tower_1", water_out_temp=30.0,
                    status=EquipmentStatus.RUNNING, fan_speed_hz=35,
                ),
            },
            outdoor_wb_temp=26.0,
        )
        assert snap.tower_approach_temps["tower_1"] == pytest.approx(4.0)
