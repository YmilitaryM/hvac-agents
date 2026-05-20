DEFAULT_ROLE_MAP = {
    "chiller": "hvac-technician",
    "cooling_tower": "hvac-technician",
    "pump": "mechanic",
    "valve": "mechanic",
    "sensor": "instrumentation-tech",
}


def assign_work_order(equipment_type: str, severity: str) -> str:
    role = DEFAULT_ROLE_MAP.get(equipment_type, "general-maintenance")
    if severity == "critical":
        return f"{role}-lead"
    return role
