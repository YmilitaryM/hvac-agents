"""Report generation API endpoints.

Supports dual-mode: PostgreSQL via repositories (when configured),
or in-memory storage (default/dev).
"""

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from ..repositories import SnapshotRepository, ReportRepository

logger = logging.getLogger(__name__)
router = APIRouter()

KW_PER_RT = 3.517  # kW of cooling per Refrigeration Ton

# In-memory storage for dev/testing fallback
_plant_snapshots: List[Dict[str, Any]] = []
_reports: Dict[str, Dict[str, Any]] = {}

# Share the in-memory store with the monitoring module
from . import monitoring as _mon


def _has_db(request: Request) -> bool:
    """Check if a database session factory is available."""
    return getattr(request.app.state, "session_factory", None) is not None


def _date_to_timestamp_range(date_str: str) -> tuple:
    """Convert an ISO date string (e.g. '2024-01-15') to (start_ts, end_ts) Unix timestamps."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        start_ts = d.replace(tzinfo=timezone.utc).timestamp()
        end_ts = start_ts + 86400  # 24 hours
        return start_ts, end_ts
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}, expected YYYY-MM-DD")


async def _get_day_snapshots(request: Request, date_str: str) -> List[Dict[str, Any]]:
    """Get snapshots for a given date from DB or in-memory store."""
    start_ts, end_ts = _date_to_timestamp_range(date_str)

    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = SnapshotRepository(session)
            results = await repo.get_range(start_ts, end_ts, limit=10000)
            return [
                {
                    "timestamp": s.timestamp,
                    "total_cooling_load_rt": s.total_cooling_load_rt,
                    "total_power_kw": s.total_power_kw,
                    "system_cop": s.system_cop,
                    "outdoor_wb_temp": s.outdoor_wb_temp,
                    "outdoor_db_temp": s.outdoor_db_temp,
                }
                for s in results
            ]

    # In-memory fallback
    return [
        s for s in _mon._plant_snapshots
        if start_ts <= s.get("timestamp", 0) < end_ts
    ]


def _compute_daily_report(snapshots: List[Dict[str, Any]], date_str: str) -> Dict[str, Any]:
    """Compute a daily report from a list of snapshots."""
    if not snapshots:
        return {
            "date": date_str,
            "period": "daily",
            "snapshot_count": 0,
            "message": "No data for this date",
        }

    n = len(snapshots)
    total_cooling_kw = sum(s.get("total_cooling_load_rt", 0) * KW_PER_RT for s in snapshots)
    total_power_kw = sum(s.get("total_power_kw", 0) for s in snapshots)
    avg_cop = (total_cooling_kw / total_power_kw) if total_power_kw > 0 else 0.0

    wb_temps = [s.get("outdoor_wb_temp", 0) for s in snapshots if s.get("outdoor_wb_temp", 0) > 0]
    db_temps = [s.get("outdoor_db_temp", 0) for s in snapshots if s.get("outdoor_db_temp", 0) > 0]

    cop_values = [s.get("system_cop", 0) for s in snapshots if s.get("system_cop", 0) > 0]

    return {
        "date": date_str,
        "period": "daily",
        "snapshot_count": n,
        "energy": {
            "total_cooling_energy_kwh": round(total_cooling_kw, 2),
            "total_power_consumption_kwh": round(total_power_kw, 2),
        },
        "performance": {
            "average_cop": round(avg_cop, 2),
            "min_cop": round(min(cop_values), 2) if cop_values else 0,
            "max_cop": round(max(cop_values), 2) if cop_values else 0,
        },
        "environment": {
            "avg_outdoor_wb_temp": round(sum(wb_temps) / len(wb_temps), 1) if wb_temps else 0,
            "avg_outdoor_db_temp": round(sum(db_temps) / len(db_temps), 1) if db_temps else 0,
        },
    }


@router.get("/daily")
async def get_daily_report(request: Request, date: str = Query(...)):
    """Get a daily report for a specific date (format: YYYY-MM-DD)."""
    try:
        snapshots = await _get_day_snapshots(request, date)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))

    report = _compute_daily_report(snapshots, date)

    # Persist report to DB if available
    if _has_db(request):
        async with request.app.state.session_factory() as session:
            repo = ReportRepository(session)
            await repo.save({
                "date": date,
                "period": "daily",
                "content": report,
                "format": "json",
            })

    return {"report": report}


@router.get("/csv")
async def get_csv_report(request: Request, date: str = Query(...)):
    """Get a daily report as CSV download (format: YYYY-MM-DD)."""
    try:
        snapshots = await _get_day_snapshots(request, date)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "timestamp", "total_cooling_load_rt", "total_power_kw",
        "system_cop", "outdoor_wb_temp", "outdoor_db_temp",
    ])

    # Data rows
    for s in snapshots:
        writer.writerow([
            s.get("timestamp", ""),
            s.get("total_cooling_load_rt", ""),
            s.get("total_power_kw", ""),
            s.get("system_cop", ""),
            s.get("outdoor_wb_temp", ""),
            s.get("outdoor_db_temp", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{date}.csv"},
    )
