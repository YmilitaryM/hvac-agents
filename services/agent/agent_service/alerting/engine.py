import time
import yaml
from typing import Optional

from .rule_models import AlertRule, AlertCondition, AlertOperator, Severity


class AlertEngine:
    def __init__(self):
        self.rules: list[AlertRule] = []
        self._last_triggered: dict[str, float] = {}  # rule_name -> last_trigger_time
        self._condition_start: dict[str, float] = {}  # "rule_name:field" -> start_time of condition being true

    def load_rules(self, yaml_path: Optional[str] = None):
        """Load rules from YAML file. If no path given, use default rules."""
        if yaml_path:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            self.rules = [AlertRule(**r) for r in data.get("rules", [])]
        else:
            self._load_default_rules()

    def _load_default_rules(self):
        """Built-in default rules."""
        self.rules = [
            AlertRule(
                name="chiller_surge_risk",
                description="Chiller surge risk high",
                conditions=[AlertCondition(field="surge_risk", operator=AlertOperator.GT, threshold=0.8, duration_seconds=60)],
                severity=Severity.CRITICAL,
                group="equipment_protection",
                cooldown_seconds=300,
            ),
            AlertRule(
                name="low_system_cop",
                description="System COP too low",
                conditions=[AlertCondition(field="system_cop", operator=AlertOperator.LT, threshold=3.5, duration_seconds=300)],
                severity=Severity.WARNING,
                group="energy_efficiency",
                cooldown_seconds=900,
            ),
            AlertRule(
                name="high_chw_supply_temp",
                description="CHW supply temp too high",
                conditions=[AlertCondition(field="chw_supply_temp", operator=AlertOperator.GT, threshold=10.0, duration_seconds=120)],
                severity=Severity.WARNING,
                group="energy_efficiency",
                cooldown_seconds=600,
            ),
            AlertRule(
                name="sensor_failure",
                description="Sensor reading failure detected",
                conditions=[AlertCondition(field="sensor_status", operator=AlertOperator.EQ, threshold=0, duration_seconds=30)],
                severity=Severity.CRITICAL,
                group="equipment_protection",
                cooldown_seconds=120,
            ),
            AlertRule(
                name="cooling_deficit",
                description="Cooling capacity insufficient",
                conditions=[AlertCondition(field="cooling_deficit_rt", operator=AlertOperator.GT, threshold=50.0, duration_seconds=60)],
                severity=Severity.CRITICAL,
                group="equipment_protection",
                cooldown_seconds=300,
            ),
        ]

    def _evaluate_condition(self, condition: AlertCondition, snapshot: dict, now: float) -> bool:
        """Evaluate a single condition against snapshot data.

        Extract field value from snapshot (support dot notation like 'chillers.CH-1.surge_risk').
        """
        value = self._get_field_value(snapshot, condition.field)
        if value is None:
            return False

        op = condition.operator
        threshold = condition.threshold
        if op == AlertOperator.GT:
            result = value > threshold
        elif op == AlertOperator.LT:
            result = value < threshold
        elif op == AlertOperator.GTE:
            result = value >= threshold
        elif op == AlertOperator.LTE:
            result = value <= threshold
        elif op == AlertOperator.EQ:
            result = abs(value - threshold) < 0.001
        elif op == AlertOperator.NEQ:
            result = abs(value - threshold) >= 0.001
        else:
            result = False

        # Debounce: condition must be true for duration_seconds continuously
        cond_key = f"{condition.field}"
        if result:
            if cond_key not in self._condition_start:
                self._condition_start[cond_key] = now
            return (now - self._condition_start[cond_key]) >= condition.duration_seconds
        else:
            self._condition_start.pop(cond_key, None)
            return False

    def _get_field_value(self, snapshot: dict, field: str) -> Optional[float]:
        """Extract nested value using dot notation.

        e.g. 'chillers.CH-1.surge_risk' -> snapshot['chillers']['CH-1']['surge_risk']
        """
        parts = field.split(".")
        value = snapshot
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value if isinstance(value, (int, float)) else None

    def evaluate(self, snapshot: dict) -> list[dict]:
        """Evaluate all rules against snapshot. Returns list of triggered alerts."""
        now = time.time()
        triggered = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check cooldown
            last = self._last_triggered.get(rule.name, 0)
            if now - last < rule.cooldown_seconds:
                continue

            # ALL conditions must pass
            all_passed = all(self._evaluate_condition(c, snapshot, now) for c in rule.conditions)

            if all_passed:
                self._last_triggered[rule.name] = now
                # Extract device_id from first condition's field path
                device = ""
                if rule.conditions:
                    parts = rule.conditions[0].field.split(".")
                    if len(parts) >= 2:
                        device = parts[1]  # e.g. "chillers.CH-1.surge_risk" -> "CH-1"
                triggered.append({
                    "timestamp": now,
                    "level": rule.severity.value,
                    "device": device,
                    "message": f"[{rule.name}] {rule.description}",
                    "rule_name": rule.name,
                    "group": rule.group,
                    "metadata": {
                        "rule_name": rule.name,
                        "group": rule.group,
                        "severity": rule.severity.value,
                    },
                })

        return triggered

    def get_rules(self) -> list[dict]:
        return [r.model_dump() for r in self.rules]

    def update_rules(self, rules_data: list[dict]):
        self.rules = [AlertRule(**r) for r in rules_data]
