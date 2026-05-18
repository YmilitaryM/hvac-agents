"""Report API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# In-memory report store
_reports: Dict[str, Dict[str, Any]] = {}


@router.get("/daily")
async def get_daily_report(date: str = Query(default="", description="ISO date string")):
    """Get a daily report for a specific date."""
    if date and date in _reports:
        return {"report": _reports[date]}
    elif not date and _reports:
        latest_date = sorted(_reports.keys())[-1]
        return {"report": _reports[latest_date], "date": latest_date}
    return {"report": None, "message": "No reports available"}


@router.post("/daily")
async def save_daily_report(report: Dict[str, Any]):
    """Save a daily report."""
    date = report.get("date", "")
    if not date:
        raise HTTPException(status_code=400, detail="date field is required")
    _reports[date] = report
    return {"status": "ok", "date": date}


@router.get("/monthly")
async def get_monthly_report(month: str = Query(default="", description="YYYY-MM format")):
    """Get a monthly report."""
    if month and month in _reports:
        return {"report": _reports[month]}
    return {"report": None, "message": "No monthly report available"}


@router.get("/list")
async def list_reports():
    """List all available report dates."""
    return {"available_dates": sorted(_reports.keys())}
