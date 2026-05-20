from datetime import datetime, timezone

from .models import WorkOrder


def generate_from_anomaly(edge_id: str, equipment_id: str, severity: str,
                          check_id: str, detail: str) -> WorkOrder:
    return WorkOrder(
        edge_id=edge_id,
        equipment_id=equipment_id,
        severity=severity,
        title=f"Inspection failed: {check_id}",
        description=detail,
        source="auto",
    )


def generate_from_degradation(edge_id: str, equipment_id: str,
                              severity: str, recommendation: str) -> WorkOrder:
    return WorkOrder(
        edge_id=edge_id,
        equipment_id=equipment_id,
        severity=severity,
        title=f"Degradation detected: {equipment_id}",
        description=recommendation,
        source="auto",
    )
