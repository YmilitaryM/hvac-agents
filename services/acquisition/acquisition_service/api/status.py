from datetime import datetime, timezone

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
async def acquisition_status(request: Request):
    poller = request.app.state.poller
    points = list(poller._points.keys())
    return {
        "service": "acquisition",
        "running": poller._running,
        "registered_points": len(points),
        "uptime_seconds": "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status/health")
async def adapter_health(request: Request):
    poller = request.app.state.poller
    health = {}
    for pid, (pt, adapter) in poller._points.items():
        health[pt.point_code] = {
            "protocol": pt.binding.protocol,
            "last_poll": pt.last_poll,
            "last_value": pt.last_value,
            "interval": pt.poll_interval_sec,
        }
    return {"adapters": health}
