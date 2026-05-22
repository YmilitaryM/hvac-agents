from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/reports")
async def list_reports(plant_id: int = Query(...), period: str = None, report_type: str = None):
    return {
        "items": [
            {"id": 1, "period": "day", "report_type": "daily", "created_at": "2026-05-20T08:00:00"},
            {"id": 2, "period": "month", "report_type": "audit", "created_at": "2026-05-01T08:00:00"},
        ],
    }


@router.post("/reports/generate")
async def generate_report(plant_id: int = Query(...), period: str = "day", report_type: str = "daily"):
    return {"task_id": "abc-123", "status": "processing", "period": period, "report_type": report_type}
