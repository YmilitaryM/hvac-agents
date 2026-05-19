"""Report API endpoints.

Supports dual-mode: PostgreSQL via repositories (when configured),
or in-memory storage (default/dev).
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import require_auth

from src.api.deps import use_db as _use_db

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory report store for dev/testing fallback
_reports: Dict[str, Dict[str, Any]] = {}


@router.get("/daily")
async def get_daily_report(date: str = Query(default="", description="ISO date string")):
    """Get a daily report for a specific date."""
    if _use_db():
        from src.api.deps import get_db_session, get_report_repo

        async for session in get_db_session():
            repo = get_report_repo(session)
            if date:
                r = await repo.get_by_date(date, "daily")
                if r:
                    return {"report": r.content, "date": r.date}
                return {"report": None, "message": "No report for this date"}
            dates = await repo.list_dates("daily")
            if dates:
                r = await repo.get_by_date(dates[0], "daily")
                if r:
                    return {"report": r.content, "date": r.date}
            return {"report": None, "message": "No reports available"}

    key = date
    if date and key in _reports:
        return {"report": _reports[key]}
    elif not date and _reports:
        latest_date = sorted(_reports.keys())[-1]
        return {"report": _reports[latest_date], "date": latest_date}
    return {"report": None, "message": "No reports available"}


@router.post("/daily")
async def save_daily_report(report: Dict[str, Any], user: bool = Depends(require_auth)):
    """Save a daily report."""
    date = report.get("date", "")
    if not date:
        raise HTTPException(status_code=400, detail="date field is required")

    if _use_db():
        from src.api.deps import get_db_session, get_report_repo

        async for session in get_db_session():
            repo = get_report_repo(session)
            await repo.save({
                "date": date,
                "period": "daily",
                "content": report,
                "format": report.get("format", "json"),
            })
            return {"status": "ok", "date": date}

    _reports[date] = report
    return {"status": "ok", "date": date}


@router.post("/generate")
async def generate_report(data: Dict[str, Any], user: bool = Depends(require_auth)):
    """Generate a report from snapshots and memory entries using ReportAgent."""
    date = data.get("date", "")
    period = data.get("period", "daily")
    report_format = data.get("format", "json")

    from src.agents.report import ReportAgent
    from src.agents.base import create_llm_client

    llm = create_llm_client(deep=False)
    agent = ReportAgent(llm=llm)

    result = await agent.run({
        "snapshots": data.get("snapshots", []),
        "memory_entries": data.get("memory_entries", []),
        "date": date,
        "report_period": period,
        "format": report_format,
        "electricity_price": data.get("electricity_price", 0.12),
        "carbon_price": data.get("carbon_price", 0.08),
        "design_cop": data.get("design_cop", 6.0),
    })

    if _use_db():
        from src.api.deps import get_db_session, get_report_repo

        async for session in get_db_session():
            repo = get_report_repo(session)
            await repo.save({
                "date": date,
                "period": period,
                "content": result.get("report", {}),
                "format": report_format,
            })
            return {
                "status": "ok",
                "date": date,
                "report": result.get("report", {}),
                "rendered": result.get("rendered", ""),
            }

    store_date = date or result.get("report", {}).get("date", "")
    if store_date:
        _reports[store_date] = result.get("report", {})

    return {
        "status": "ok",
        "date": store_date,
        "report": result.get("report", {}),
        "rendered": result.get("rendered", ""),
    }


@router.get("/daily/rendered")
async def get_daily_report_rendered(
    date: str = Query(default="", description="ISO date string"),
    format: str = Query(default="markdown", description="Output format: json, markdown, csv"),
):
    """Get a daily report in the requested format."""
    report_data = None

    if _use_db():
        from src.api.deps import get_db_session, get_report_repo

        async for session in get_db_session():
            repo = get_report_repo(session)
            if date:
                r = await repo.get_by_date(date, "daily")
                if r:
                    report_data = r.content
            else:
                dates = await repo.list_dates("daily")
                if dates:
                    r = await repo.get_by_date(dates[0], "daily")
                    if r:
                        report_data = r.content

    if report_data is None:
        key = date if date else ""
        if date and key in _reports:
            report_data = _reports[key]
        elif _reports:
            latest_date = sorted(_reports.keys())[-1]
            report_data = _reports[latest_date]

    if report_data is None:
        return {"report": None, "message": "No report available"}

    from src.reports.renderer import render_report_json, render_report_markdown, render_report_csv

    renderers = {
        "json": render_report_json,
        "markdown": render_report_markdown,
        "csv": render_report_csv,
    }
    renderer = renderers.get(format, render_report_markdown)

    from src.reports.generator import DailyReport

    if isinstance(report_data, dict):
        report = DailyReport(
            date=report_data.get("date", ""),
            kpis=None,
            summary=report_data.get("summary", ""),
            alerts_summary=report_data.get("alerts_summary", ""),
            strategies_executed=report_data.get("strategies_executed", 0),
            top_concerns=report_data.get("top_concerns", []),
            recommendations=report_data.get("recommendations", []),
        )
        rendered = renderer(report)
        return {"report": report_data, "rendered": rendered, "format": format}

    return {"report": report_data, "rendered": str(report_data), "format": format}


@router.get("/monthly")
async def get_monthly_report(month: str = Query(default="", description="YYYY-MM format")):
    """Get a monthly report."""
    if _use_db():
        from src.api.deps import get_db_session, get_report_repo

        async for session in get_db_session():
            repo = get_report_repo(session)
            if month:
                r = await repo.get_by_date(month, "monthly")
                if r:
                    return {"report": r.content, "month": r.date}
                return {"report": None, "message": "No monthly report available"}
            return {"report": None, "message": "No month specified"}

    key = month
    if month and key in _reports:
        return {"report": _reports[key]}
    return {"report": None, "message": "No monthly report available"}


@router.get("/list")
async def list_reports():
    """List all available report dates."""
    if _use_db():
        from src.api.deps import get_db_session, get_report_repo

        async for session in get_db_session():
            repo = get_report_repo(session)
            daily = await repo.list_dates("daily")
            monthly = await repo.list_dates("monthly")
            return {"daily": daily, "monthly": monthly}

    return {"available_dates": sorted(_reports.keys())}
