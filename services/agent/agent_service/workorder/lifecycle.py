VALID_TRANSITIONS = {
    "open": ["acknowledged", "rejected"],
    "acknowledged": ["in_progress", "rejected"],
    "in_progress": ["resolved"],
    "resolved": ["closed", "in_progress"],
    "closed": [],
    "rejected": [],
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, [])


def transition(work_order, to_status: str, changed_by: str = "system", note: str = None) -> dict:
    if not can_transition(work_order.status, to_status):
        raise ValueError(f"Cannot transition from {work_order.status} to {to_status}")

    from_status = work_order.status
    work_order.status = to_status

    if to_status == "resolved":
        from datetime import datetime, timezone
        work_order.resolved_at = datetime.now(timezone.utc)

    return {
        "work_order_id": work_order.id,
        "from_status": from_status,
        "to_status": to_status,
        "changed_by": changed_by,
        "note": note,
    }
