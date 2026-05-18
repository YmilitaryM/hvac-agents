"""Monitoring API endpoints for real-time plant data."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

router = APIRouter()


# In-memory storage for demo/testing (would be TimescaleDB in production)
_plant_snapshots: List[Dict[str, Any]] = []
_alerts: List[Dict[str, Any]] = []
_health_scores: Dict[str, float] = {}


@router.get("/snapshot")
async def get_latest_snapshot():
    """Get the most recent plant snapshot."""
    if _plant_snapshots:
        return {"snapshot": _plant_snapshots[-1]}
    return {"snapshot": None, "message": "No snapshots available"}


@router.get("/snapshots")
async def get_snapshots(limit: int = Query(default=100, le=1000)):
    """Get recent plant snapshots."""
    return {"snapshots": _plant_snapshots[-limit:], "count": len(_plant_snapshots[-limit:])}


@router.post("/snapshot")
async def ingest_snapshot(snapshot: Dict[str, Any]):
    """Ingest a new plant snapshot."""
    # Add timestamp if missing
    if "timestamp" not in snapshot:
        import time as _time
        snapshot["timestamp"] = _time.time()
    _plant_snapshots.append(snapshot)
    # Keep only last 10000 snapshots
    if len(_plant_snapshots) > 10000:
        _plant_snapshots[:] = _plant_snapshots[-10000:]
    return {"status": "ok", "snapshot_count": len(_plant_snapshots)}


@router.get("/alerts")
async def get_alerts(limit: int = Query(default=50, le=500)):
    """Get recent alerts."""
    return {"alerts": _alerts[-limit:], "count": len(_alerts[-limit:])}


@router.post("/alerts")
async def ingest_alert(alert: Dict[str, Any]):
    """Ingest a new alert."""
    if "timestamp" not in alert:
        import time as _time
        alert["timestamp"] = _time.time()
    _alerts.append(alert)
    if len(_alerts) > 5000:
        _alerts[:] = _alerts[-5000:]
    return {"status": "ok", "alert_count": len(_alerts)}


@router.get("/health")
async def get_health_scores():
    """Get current equipment health scores."""
    return {"health_scores": _health_scores}


@router.post("/health")
async def update_health_scores(scores: Dict[str, float]):
    """Update equipment health scores."""
    _health_scores.update(scores)
    return {"status": "ok", "devices": len(_health_scores)}


@router.get("/kpi")
async def get_realtime_kpi():
    """Get real-time KPI from the latest snapshot."""
    if not _plant_snapshots:
        return {"kpi": None, "message": "No data"}

    latest = _plant_snapshots[-1]
    total_load = latest.get("total_cooling_load_rt", 0)
    total_power = latest.get("total_power_kw", 0)
    cop = (total_load * 3.517) / total_power if total_power > 0 else 0.0

    return {
        "kpi": {
            "total_cooling_load_rt": total_load,
            "total_power_kw": total_power,
            "system_cop": round(cop, 2),
            "outdoor_wb_temp": latest.get("outdoor_wb_temp", 0),
            "outdoor_db_temp": latest.get("outdoor_db_temp", 0),
        }
    }
