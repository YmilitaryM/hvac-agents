def compute_health_score(metrics: dict) -> dict:
    """
    AHP-weighted health score (0-100).
    GB/T 6075 A/B/C/D zones used for vibration thresholds.
    """
    score = 100.0
    component_scores = {}

    cop_deg = metrics.get("cop_degradation_pct", 0)
    cop_score = max(0, 100 - cop_deg * 2)
    component_scores["performance"] = round(cop_score, 1)
    score = min(score, cop_score)

    vib = metrics.get("vibration_rms", 0)
    if vib < 4.5:
        vib_score, zone = 95, "A"
    elif vib < 7.1:
        vib_score, zone = 75, "B"
    elif vib < 11.0:
        vib_score, zone = 50, "C"
    else:
        vib_score, zone = 25, "D"
    component_scores["vibration"] = round(vib_score, 1)
    component_scores["vibration_zone"] = zone
    score = min(score, vib_score)

    drift = metrics.get("approach_temp_drift_k", 0)
    drift_score = max(0, 100 - drift * 10)
    component_scores["heat_transfer"] = round(drift_score, 1)
    score = min(score, drift_score)

    days = metrics.get("days_since_maintenance", 0)
    maint_score = max(30, 100 - days * 0.4)
    component_scores["maintenance"] = round(maint_score, 1)
    score = min(score, maint_score)

    trend = "stable"
    if cop_deg > 10:
        trend = "down"
    elif cop_deg < 3:
        trend = "up"

    return {
        "overall_score": round(score, 1),
        "component_scores": component_scores,
        "trend_direction": trend,
    }
