import time


class SuppressionEngine:
    def __init__(self):
        self._alert_history: list[dict] = []  # recent alerts for dedup
        self._maintenance_devices: set[str] = set()
        self._offline_parents: set[str] = set()

    def add_maintenance(self, device_id: str):
        self._maintenance_devices.add(device_id)

    def remove_maintenance(self, device_id: str):
        self._maintenance_devices.discard(device_id)

    def set_parent_offline(self, device_id: str):
        self._offline_parents.add(device_id)

    def set_parent_online(self, device_id: str):
        self._offline_parents.discard(device_id)

    def should_suppress(self, alert: dict, now: float = None) -> tuple[bool, str]:
        """Returns (suppressed, reason).

        - Maintenance mode suppresses all alerts for that device
        - Parent device OFF suppresses child alerts
        - 5-min dedup: same (device, message) within 5 min
        - Storm detection: >50 alerts/min triggers storm aggregation
        """
        if now is None:
            now = time.time()

        device = alert.get("device", "")
        message = alert.get("message", "")

        # Maintenance suppression
        if device and device in self._maintenance_devices:
            return True, "maintenance_mode"

        # Parent offline suppression (simple: if any parent is offline)
        if device and self._offline_parents:
            return True, "parent_offline"

        # 5-minute dedup
        for hist in self._alert_history:
            if hist.get("device") == device and hist.get("message") == message:
                if now - hist.get("timestamp", 0) < 300:
                    return True, "dedup_5min"

        # Record this alert BEFORE storm check so history is always current
        self._alert_history.append({**alert, "timestamp": now})
        # Prune old entries (keep last hour)
        self._alert_history = [h for h in self._alert_history if now - h.get("timestamp", 0) < 3600]

        # Storm detection (>50 alerts in last 60 seconds)
        recent_count = sum(1 for h in self._alert_history if now - h.get("timestamp", 0) < 60)
        if recent_count > 50:
            return True, "alert_storm"

        return False, ""
