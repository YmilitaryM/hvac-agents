ACTION_RULES = [
    {
        "condition": {"field": "cop_degradation_pct", "op": ">", "value": 15},
        "action": "Schedule tube cleaning / refrigerant charge check",
        "severity": "critical",
    },
    {
        "condition": {"field": "cop_degradation_pct", "op": ">", "value": 7},
        "action": "Plan condenser coil inspection within 2 weeks",
        "severity": "degrading",
    },
    {
        "condition": {"field": "approach_temp_drift_k", "op": ">", "value": 5.0},
        "action": "Inspect cooling tower fill and water distribution",
        "severity": "critical",
    },
    {
        "condition": {"field": "approach_temp_drift_k", "op": ">", "value": 3.0},
        "action": "Monitor approach temperature trend weekly",
        "severity": "degrading",
    },
    {
        "condition": {"field": "vibration_trend", "op": ">", "value": 7.0},
        "action": "Check pump alignment and bearing condition",
        "severity": "critical",
    },
]


def advise(degradation_result: dict) -> list[dict]:
    recommendations = []
    for rule in ACTION_RULES:
        cond = rule["condition"]
        field_val = degradation_result.get(cond["field"])
        if field_val is None:
            continue
        if cond["op"] == ">" and field_val > cond["value"]:
            recommendations.append({"action": rule["action"], "severity": rule["severity"]})
    return recommendations
