"""Monitor Agent — checks equipment health and detects anomalies.

Uses a pure-Python detection function for core logic. LLM integration
will be added later for more sophisticated anomaly classification.
"""

from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent, AgentContext


def detect_anomalies(plant_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Core detection logic — no LLM required for basic patterns.

    Analyzes a plant snapshot (dict from PlantSnapshot.model_dump()) for:
    - Equipment status (FAULT / MAINTENANCE)
    - Chiller surge risk
    - Cooling tower approach temps
    - System COP degradation
    - Pump mismatch (RUNNING but zero speed)

    Returns a dict with:
        alerts: list of {"level": str, "device": str, "message": str}
        health_scores: dict of device_id -> int (0-100)
        anomaly_detected: bool
        anomaly_details: str
    """
    alerts: List[Dict[str, str]] = []
    health_scores: Dict[str, int] = {}

    # Initialize health scores for all equipment
    for category in ("chillers", "cooling_towers", "chw_pumps", "cw_pumps"):
        for device_id, device in plant_snapshot.get(category, {}).items():
            health_scores[device_id] = 100

    # 1. Check equipment status — FAULT and MAINTENANCE
    for category_name, category in (
        ("chiller", plant_snapshot.get("chillers", {})),
        ("cooling_tower", plant_snapshot.get("cooling_towers", {})),
        ("CHW pump", plant_snapshot.get("chw_pumps", {})),
        ("CW pump", plant_snapshot.get("cw_pumps", {})),
    ):
        for device_id, device in category.items():
            status = device.get("status", "")
            if status == "FAULT":
                alerts.append({
                    "level": "critical",
                    "device": device_id,
                    "message": f"{category_name} {device_id} has FAULT status — immediate attention required.",
                })
                health_scores[device_id] = 20
            elif status == "MAINTENANCE":
                alerts.append({
                    "level": "info",
                    "device": device_id,
                    "message": f"{category_name} {device_id} is in MAINTENANCE mode.",
                })
                health_scores[device_id] = 85

    # 2. Chiller surge risk — warn if surge_risk is True and chiller is running
    for device_id, chiller in plant_snapshot.get("chillers", {}).items():
        if chiller.get("surge_risk") and chiller.get("is_running"):
            alerts.append({
                "level": "warning",
                "device": device_id,
                "message": f"Chiller {device_id} has surge risk (PLR={chiller.get('plr', 0):.2f}).",
            })
            # Only lower score if not already lowered by FAULT
            if health_scores.get(device_id, 100) >= 50:
                health_scores[device_id] = 75

    # 3. High cooling tower approach temp (>5°C)
    tower_approaches = plant_snapshot.get("tower_approach_temps", {})
    for device_id, approach_temp in tower_approaches.items():
        if approach_temp > 5.0:
            alerts.append({
                "level": "warning",
                "device": device_id,
                "message": f"Cooling tower {device_id} has high approach temperature ({approach_temp:.1f}°C).",
            })
            # Only lower score if not already lowered by FAULT
            if health_scores.get(device_id, 100) >= 50:
                health_scores[device_id] = 70

    # 4. System COP degradation (< 3.0 while under load)
    system_cop = plant_snapshot.get("system_cop", 0)
    total_load = plant_snapshot.get("total_cooling_load_rt", 0)
    if system_cop < 3.0 and total_load > 0:
        alerts.append({
            "level": "warning",
            "device": "system",
            "message": f"System COP is low ({system_cop:.2f}) — possible efficiency degradation.",
        })

    # 5. Pump mismatch — RUNNING status but zero speed
    for category_name, category in (
        ("CHW pump", plant_snapshot.get("chw_pumps", {})),
        ("CW pump", plant_snapshot.get("cw_pumps", {})),
    ):
        for device_id, pump in category.items():
            if pump.get("status") == "RUNNING" and pump.get("speed_hz", 1) == 0:
                alerts.append({
                    "level": "warning",
                    "device": device_id,
                    "message": f"{category_name} {device_id} reports RUNNING but speed is 0 Hz — possible sensor or VFD fault.",
                })
                # Only lower score if not already lowered by FAULT
                if health_scores.get(device_id, 100) >= 50:
                    health_scores[device_id] = 60

    # Build result
    anomaly_detected = len(alerts) > 0
    anomaly_details = ""
    if anomaly_detected:
        summary_parts = []
        for level in ("critical", "warning", "info"):
            count = sum(1 for a in alerts if a["level"] == level)
            if count > 0:
                summary_parts.append(f"{count} {level}")
        anomaly_details = "Anomalies detected: " + ", ".join(summary_parts) + "."

    return {
        "alerts": alerts,
        "health_scores": health_scores,
        "anomaly_detected": anomaly_detected,
        "anomaly_details": anomaly_details,
    }


class MonitorAgent(BaseAgent):
    """Monitor Agent — checks equipment health and detects anomalies.

    Uses the QUICK model (Haiku) for fast, frequent monitoring.
    Core detection logic is in detect_anomalies().
    """

    def __init__(self, llm=None, context: Optional[AgentContext] = None):
        super().__init__(name="monitor", llm=llm, context=context)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a plant snapshot and return monitoring results.

        Args:
            input_data: dict with "plant_snapshot" key containing a plant state dict.

        Returns:
            dict with alerts, health_scores, anomaly_detected, anomaly_details.
        """
        snapshot = input_data.get("plant_snapshot", {})
        result = detect_anomalies(snapshot)
        return result
