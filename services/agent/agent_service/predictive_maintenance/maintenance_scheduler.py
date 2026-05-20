from datetime import datetime, timedelta, timezone


def recommend_window(severity: str, current_time: datetime | None = None) -> dict:
    now = current_time or datetime.now(timezone.utc)

    if severity == "critical":
        start = now + timedelta(hours=4)
        deadline = now + timedelta(days=2)
    elif severity == "degrading":
        start = now + timedelta(days=3)
        deadline = now + timedelta(days=14)
    else:
        start = now + timedelta(days=7)
        deadline = now + timedelta(days=30)

    return {
        "severity": severity,
        "recommended_start": start.isoformat(),
        "deadline": deadline.isoformat(),
        "urgency": "immediate" if severity == "critical" else "planned",
    }
