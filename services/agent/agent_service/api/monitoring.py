"""Monitoring API endpoints for real-time plant data.

Supports dual-mode: PostgreSQL via repositories (when configured),
or in-memory storage (default/dev).
"""

import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query, Request

from common.auth import require_role, Role

from ..models import PlantSnapshotModel, AlertModel
from ..repositories import SnapshotRepository, AlertRepository

logger = logging.getLogger(__name__)
router = APIRouter()

# Conversion constant
KW_PER_RT = 3.517  # kW of cooling per Refrigeration Ton

# In-memory storage for dev/testing fallback
_plant_snapshots: List[Dict[str, Any]] = []
_alerts: List[Dict[str, Any]] = []
_health_scores: Dict[str, float] = {}


def _has_db(request: Request) -> bool:
    """Check if a database session factory is available."""
    return getattr(request.app.state, "session_factory", None) is not None


# --- Snapshot endpoints ---

@router.get("/snapshot")
async def get_latest_snapshot(request: Request):
    """Get the most recent plant snapshot."""
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = SnapshotRepository(session)
            sn = await repo.get_latest()
            if sn:
                return {"snapshot": {
                    "timestamp": sn.timestamp,
                    "total_cooling_load_rt": sn.total_cooling_load_rt,
                    "total_power_kw": sn.total_power_kw,
                    "system_cop": sn.system_cop,
                    "outdoor_wb_temp": sn.outdoor_wb_temp,
                    "outdoor_db_temp": sn.outdoor_db_temp,
                    "chillers": sn.chiller_data or {},
                }}
            return {"snapshot": None, "message": "No snapshots available"}

    if _plant_snapshots:
        return {"snapshot": _plant_snapshots[-1]}
    return {"snapshot": None, "message": "No snapshots available"}


@router.get("/snapshots")
async def get_snapshots(request: Request, limit: int = Query(default=100, le=1000)):
    """Get recent plant snapshots."""
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = SnapshotRepository(session)
            results = await repo.get_range(0, time.time(), limit=limit)
            return {
                "snapshots": [
                    {
                        "timestamp": s.timestamp,
                        "total_cooling_load_rt": s.total_cooling_load_rt,
                        "total_power_kw": s.total_power_kw,
                        "system_cop": s.system_cop,
                    }
                    for s in results
                ],
                "count": len(results),
            }

    return {"snapshots": _plant_snapshots[-limit:], "count": len(_plant_snapshots[-limit:])}


@router.post("/snapshot")
async def ingest_snapshot(
    request: Request,
    snapshot: Dict[str, Any],
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Ingest a new plant snapshot."""
    if "timestamp" not in snapshot:
        snapshot["timestamp"] = time.time()

    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = SnapshotRepository(session)
            chillers = snapshot.get("chillers", {})
            towers = snapshot.get("cooling_towers", {})
            pumps = {
                "chw": snapshot.get("chw_pumps", {}),
                "cw": snapshot.get("cw_pumps", {}),
            }
            await repo.create({
                "timestamp": snapshot["timestamp"],
                "total_cooling_load_rt": snapshot.get("total_cooling_load_rt", 0),
                "total_power_kw": snapshot.get("total_power_kw", 0),
                "system_cop": snapshot.get("system_cop", 0),
                "outdoor_wb_temp": snapshot.get("outdoor_wb_temp", 0),
                "outdoor_db_temp": snapshot.get("outdoor_db_temp", 0),
                "chiller_data": chillers,
                "tower_data": towers,
                "pump_data": pumps,
                "raw_snapshot": snapshot,
            })
            return {"status": "ok", "snapshot_count": 1}

    _plant_snapshots.append(snapshot)
    if len(_plant_snapshots) > 10000:
        _plant_snapshots[:] = _plant_snapshots[-10000:]
    return {"status": "ok", "snapshot_count": len(_plant_snapshots)}


# --- Alert endpoints ---

@router.get("/alerts")
async def get_alerts(request: Request, limit: int = Query(default=50, le=500)):
    """Get recent alerts."""
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = AlertRepository(session)
            results = await repo.get_recent(limit=limit)
            return {
                "alerts": [
                    {
                        "timestamp": a.timestamp,
                        "level": a.level,
                        "device": a.device,
                        "message": a.message,
                        "acknowledged": a.acknowledged,
                    }
                    for a in results
                ],
                "count": len(results),
            }

    return {"alerts": _alerts[-limit:], "count": len(_alerts[-limit:])}


@router.post("/alerts")
async def ingest_alert(
    request: Request,
    alert: Dict[str, Any],
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Ingest a new alert."""
    if "timestamp" not in alert:
        alert["timestamp"] = time.time()

    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = AlertRepository(session)
            await repo.create({
                "timestamp": alert["timestamp"],
                "level": alert.get("level", "info"),
                "device": alert.get("device", ""),
                "message": alert.get("message", ""),
            })
            return {"status": "ok", "alert_count": 1}

    _alerts.append(alert)
    if len(_alerts) > 5000:
        _alerts[:] = _alerts[-5000:]
    return {"status": "ok", "alert_count": len(_alerts)}


# --- Health endpoints ---

@router.get("/health")
async def get_health_scores():
    """Get current equipment health scores."""
    return {"health_scores": _health_scores}


@router.post("/health")
async def update_health_scores(
    scores: Dict[str, float],
    user: dict = Depends(require_role(Role.OPERATOR, Role.ENGINEER, Role.ADMIN)),
):
    """Update equipment health scores."""
    _health_scores.update(scores)
    return {"status": "ok", "devices": len(_health_scores)}


# --- KPI endpoint ---

@router.get("/kpi")
async def get_realtime_kpi(request: Request):
    """Get real-time KPI from the latest snapshot."""
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = SnapshotRepository(session)
            latest = await repo.get_latest()
            if latest:
                cop = (
                    (latest.total_cooling_load_rt * KW_PER_RT) / latest.total_power_kw
                    if latest.total_power_kw > 0
                    else 0.0
                )
                return {
                    "kpi": {
                        "total_cooling_load_rt": latest.total_cooling_load_rt,
                        "total_power_kw": latest.total_power_kw,
                        "system_cop": round(cop, 2),
                        "outdoor_wb_temp": latest.outdoor_wb_temp,
                        "outdoor_db_temp": latest.outdoor_db_temp,
                    }
                }
            return {"kpi": None, "message": "No data"}

    if not _plant_snapshots:
        return {"kpi": None, "message": "No data"}

    latest = _plant_snapshots[-1]
    total_load = latest.get("total_cooling_load_rt", 0)
    total_power = latest.get("total_power_kw", 0)
    cop = (total_load * KW_PER_RT) / total_power if total_power > 0 else 0.0

    return {
        "kpi": {
            "total_cooling_load_rt": total_load,
            "total_power_kw": total_power,
            "system_cop": round(cop, 2),
            "outdoor_wb_temp": latest.get("outdoor_wb_temp", 0),
            "outdoor_db_temp": latest.get("outdoor_db_temp", 0),
        }
    }
