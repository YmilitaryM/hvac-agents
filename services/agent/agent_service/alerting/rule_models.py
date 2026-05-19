from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertOperator(str, Enum):
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQ = "=="
    NEQ = "!="


class AlertCondition(BaseModel):
    field: str  # e.g. "system_cop", "chillers.CH-1.surge_risk"
    operator: AlertOperator
    threshold: float
    duration_seconds: int = 60  # debounce: must be true for this long


class AlertRule(BaseModel):
    name: str  # unique rule identifier
    description: str = ""
    conditions: list[AlertCondition]  # ALL must be true (AND logic)
    severity: Severity
    group: str = "general"  # equipment_protection, energy_efficiency, env_safety
    enabled: bool = True
    cooldown_seconds: int = 300  # minimum interval between repeated triggers
