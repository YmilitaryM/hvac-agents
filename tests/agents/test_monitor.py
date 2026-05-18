"""Tests for the Monitor Agent."""

import pytest
from src.agents.monitor import detect_anomalies, MonitorAgent


class TestDetectAnomalies:
    def test_normal_plant_no_alerts(self):
        snapshot = {
            "chillers": {
                "ch1": {
                    "device_id": "ch1", "capacity_rt": 500,
                    "status": "RUNNING", "current_load_rt": 300,
                    "power_kw": 200, "chw_supply_temp": 7.0,
                    "is_running": True, "plr": 0.6, "instant_cop": 5.5,
                    "surge_risk": False,
                }
            },
            "cooling_towers": {
                "ct1": {
                    "device_id": "ct1", "status": "RUNNING",
                    "fan_speed_hz": 50, "water_out_temp": 30.0,
                }
            },
            "chw_pumps": {
                "p1": {"device_id": "p1", "status": "RUNNING", "speed_hz": 50}
            },
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 300, "total_power_kw": 200,
            "system_cop": 5.5, "running_chillers": 1,
            "tower_approach_temps": {"ct1": 2.0},
        }
        result = detect_anomalies(snapshot)
        assert result["anomaly_detected"] is False
        assert len(result["alerts"]) == 0
        assert result["health_scores"]["ch1"] == 100

    def test_fault_status_detected(self):
        snapshot = {
            "chillers": {
                "ch1": {
                    "device_id": "ch1", "capacity_rt": 500,
                    "status": "FAULT", "current_load_rt": 0,
                    "power_kw": 0, "chw_supply_temp": 7.0,
                    "is_running": False, "plr": 0.0, "instant_cop": 0.0,
                    "surge_risk": False,
                }
            },
            "cooling_towers": {},
            "chw_pumps": {},
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 0, "total_power_kw": 0,
            "system_cop": 0, "running_chillers": 0,
            "tower_approach_temps": {},
        }
        result = detect_anomalies(snapshot)
        assert result["anomaly_detected"] is True
        alerts = result["alerts"]
        criticals = [a for a in alerts if a["level"] == "critical"]
        assert len(criticals) >= 1
        assert any("FAULT" in a["message"].upper() for a in criticals)

    def test_low_system_cop_alert(self):
        snapshot = {
            "chillers": {
                "ch1": {
                    "device_id": "ch1", "capacity_rt": 500,
                    "status": "RUNNING", "current_load_rt": 300,
                    "power_kw": 350, "chw_supply_temp": 7.0,
                    "is_running": True, "plr": 0.6, "instant_cop": 2.8,
                    "surge_risk": False,
                }
            },
            "cooling_towers": {},
            "chw_pumps": {},
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 300, "total_power_kw": 350,
            "system_cop": 2.8, "running_chillers": 1,
            "tower_approach_temps": {},
        }
        result = detect_anomalies(snapshot)
        assert result["anomaly_detected"] is True
        messages = [a["message"].lower() for a in result["alerts"]]
        assert any("cop" in m for m in messages)

    def test_high_approach_temp_alert(self):
        snapshot = {
            "chillers": {},
            "cooling_towers": {
                "ct1": {
                    "device_id": "ct1", "status": "RUNNING",
                    "fan_speed_hz": 30, "water_out_temp": 35.0,
                }
            },
            "chw_pumps": {},
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 0, "total_power_kw": 0,
            "system_cop": 0, "running_chillers": 0,
            "tower_approach_temps": {"ct1": 6.5},
        }
        result = detect_anomalies(snapshot)
        assert result["anomaly_detected"] is True
        messages = [a["message"].lower() for a in result["alerts"]]
        assert any("approach" in m for m in messages)

    def test_pump_mismatch_alert(self):
        snapshot = {
            "chillers": {},
            "cooling_towers": {},
            "chw_pumps": {
                "p1": {"device_id": "p1", "status": "RUNNING", "speed_hz": 0}
            },
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 0, "total_power_kw": 0,
            "system_cop": 0, "running_chillers": 0,
            "tower_approach_temps": {},
        }
        result = detect_anomalies(snapshot)
        assert result["anomaly_detected"] is True
        messages = [a["message"].lower() for a in result["alerts"]]
        assert any("pump" in m for m in messages)

    def test_surge_risk_warning(self):
        snapshot = {
            "chillers": {
                "ch1": {
                    "device_id": "ch1", "capacity_rt": 500,
                    "status": "RUNNING", "current_load_rt": 110,
                    "power_kw": 80, "chw_supply_temp": 7.0,
                    "is_running": True, "plr": 0.22, "instant_cop": 4.0,
                    "surge_risk": True,
                }
            },
            "cooling_towers": {},
            "chw_pumps": {},
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 110, "total_power_kw": 80,
            "system_cop": 4.0, "running_chillers": 1,
            "tower_approach_temps": {},
        }
        result = detect_anomalies(snapshot)
        warnings = [a for a in result["alerts"] if a["level"] == "warning"]
        assert any("surge" in a["message"].lower() for a in warnings)

    def test_maintenance_status_info_alert(self):
        snapshot = {
            "chillers": {
                "ch1": {
                    "device_id": "ch1", "capacity_rt": 500,
                    "status": "MAINTENANCE", "current_load_rt": 0,
                    "power_kw": 0, "chw_supply_temp": 7.0,
                    "is_running": False, "plr": 0.0, "instant_cop": 0.0,
                    "surge_risk": False,
                }
            },
            "cooling_towers": {},
            "chw_pumps": {},
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 0, "total_power_kw": 0,
            "system_cop": 0, "running_chillers": 0,
            "tower_approach_temps": {},
        }
        result = detect_anomalies(snapshot)
        infos = [a for a in result["alerts"] if a["level"] == "info"]
        assert any("MAINTENANCE" in a["message"].upper() for a in infos)

    def test_health_scores_reflect_issues(self):
        snapshot = {
            "chillers": {
                "ch1": {
                    "device_id": "ch1", "capacity_rt": 500,
                    "status": "FAULT", "current_load_rt": 0,
                    "power_kw": 0, "chw_supply_temp": 7.0,
                    "is_running": False, "plr": 0.0, "instant_cop": 0.0,
                    "surge_risk": False,
                },
                "ch2": {
                    "device_id": "ch2", "capacity_rt": 500,
                    "status": "RUNNING", "current_load_rt": 300,
                    "power_kw": 200, "chw_supply_temp": 7.0,
                    "is_running": True, "plr": 0.6, "instant_cop": 5.5,
                    "surge_risk": False,
                }
            },
            "cooling_towers": {},
            "chw_pumps": {},
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 300, "total_power_kw": 200,
            "system_cop": 5.5, "running_chillers": 1,
            "tower_approach_temps": {},
        }
        result = detect_anomalies(snapshot)
        assert result["health_scores"]["ch1"] < 50  # FAULT -> critical
        assert result["health_scores"]["ch2"] == 100  # normal


class TestMonitorAgent:
    @pytest.mark.asyncio
    async def test_run_calls_detect_anomalies(self):
        agent = MonitorAgent()
        snapshot = {
            "chillers": {
                "ch1": {
                    "device_id": "ch1", "capacity_rt": 500,
                    "status": "FAULT", "current_load_rt": 0,
                    "power_kw": 0, "chw_supply_temp": 7.0,
                    "is_running": False, "plr": 0.0, "instant_cop": 0.0,
                    "surge_risk": False,
                }
            },
            "cooling_towers": {},
            "chw_pumps": {},
            "cw_pumps": {},
            "outdoor_wb_temp": 26.0, "outdoor_db_temp": 32.0,
            "total_cooling_load_rt": 0, "total_power_kw": 0,
            "system_cop": 0, "running_chillers": 0,
            "tower_approach_temps": {},
        }
        result = await agent.run({"plant_snapshot": snapshot})
        assert result["anomaly_detected"] is True
        assert len(result["alerts"]) > 0
