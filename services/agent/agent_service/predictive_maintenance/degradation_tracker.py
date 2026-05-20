from typing import Optional


def cop_degradation(design_cop: float, window_values: list[float]) -> float:
    if not window_values:
        return 0.0
    current_avg = sum(window_values) / len(window_values)
    return (design_cop - current_avg) / design_cop * 100


def cusum_detect(values: list[float], threshold: float = 1.0) -> tuple[bool, Optional[int]]:
    """CUSUM change-point detection. Returns (triggered, change_point_index).

    Uses the mean of the first half of values as the in-control reference mean,
    then scans all values for a cumulative sum exceeding the threshold.
    """
    if len(values) < 4:
        return False, None

    # Use first half as reference period for in-control mean
    ref_n = max(len(values) // 2, 2)
    ref_mean = sum(values[:ref_n]) / ref_n

    k = 0.5 * threshold  # slack / allowance
    cusum_pos = 0.0
    cusum_neg = 0.0
    change_point = None

    for i, v in enumerate(values):
        cusum_pos = max(0, cusum_pos + (v - ref_mean) - k)
        cusum_neg = max(0, cusum_neg + (ref_mean - v) - k)
        if cusum_pos > threshold or cusum_neg > threshold:
            change_point = i
            break

    triggered = change_point is not None
    return triggered, change_point


class DegradationTracker:
    def __init__(self, equipment_id: str, equipment_type: str):
        self.equipment_id = equipment_id
        self.equipment_type = equipment_type

    def evaluate(self, design_cop: float, cop_window: list[float],
                 approach_temp_avg: float, vibration_window: list[float]) -> dict:
        cop_drift = cop_degradation(design_cop, cop_window)
        cusum_triggered, _ = cusum_detect(cop_window, threshold=1.0)

        severity = "normal"
        if cop_drift > 15 or approach_temp_avg > 5.0:
            severity = "critical"
        elif cop_drift > 7 or approach_temp_avg > 3.0:
            severity = "degrading"

        recommendation = None
        if severity == "critical":
            recommendation = f"Schedule immediate maintenance for {self.equipment_id}"
        elif severity == "degrading":
            recommendation = f"Plan maintenance for {self.equipment_id} within next 2 weeks"

        return {
            "equipment_id": self.equipment_id,
            "equipment_type": self.equipment_type,
            "severity": severity,
            "cop_degradation_pct": round(cop_drift, 1),
            "approach_temp_drift_k": round(approach_temp_avg, 1),
            "vibration_trend": sum(vibration_window) / len(vibration_window) if vibration_window else 0,
            "cusum_triggered": cusum_triggered,
            "recommended_action": recommendation,
        }
