import time
from enum import Enum


class EscalationLevel(str, Enum):
    NONE = "none"
    PHONE = "phone"
    SUPERIOR = "superior"
    UPGRADED = "upgraded"


class EscalationEngine:
    def __init__(self):
        self._unacked_alerts: dict[str, dict] = {}  # alert_id -> {alert, created_at}

    def add_alert(self, alert_id: str, alert: dict):
        self._unacked_alerts[alert_id] = {"alert": alert, "created_at": time.time()}

    def acknowledge(self, alert_id: str):
        self._unacked_alerts.pop(alert_id, None)

    def check_escalations(self, now: float = None) -> list[dict]:
        """Check all unacked alerts and return escalation actions needed."""
        if now is None:
            now = time.time()

        actions = []
        for alert_id, data in list(self._unacked_alerts.items()):
            alert = data["alert"]
            age = now - data["created_at"]
            severity = alert.get("level", "warning")
            already_escalated = alert.get("escalated_to", "")

            if severity == "critical":
                if age > 1800 and "superior" not in already_escalated:  # 30 min
                    actions.append({
                        "alert_id": alert_id,
                        "action": "notify_superior",
                        "level": EscalationLevel.SUPERIOR,
                    })
                    alert["escalated_to"] = (
                        already_escalated + ",superior" if already_escalated else "superior"
                    )
                elif age > 300 and "phone" not in already_escalated:  # 5 min
                    actions.append({
                        "alert_id": alert_id,
                        "action": "notify_phone",
                        "level": EscalationLevel.PHONE,
                    })
                    alert["escalated_to"] = (
                        already_escalated + ",phone" if already_escalated else "phone"
                    )
            elif severity == "warning":
                if age > 14400:  # 4 hours
                    actions.append({
                        "alert_id": alert_id,
                        "action": "upgrade_to_critical",
                        "level": EscalationLevel.UPGRADED,
                    })
                    alert["level"] = "critical"
                    alert["escalated_to"] = (
                        already_escalated + ",upgraded" if already_escalated else "upgraded"
                    )

        return actions
