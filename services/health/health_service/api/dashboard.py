from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/dashboard")
async def health_dashboard(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "overall_health": 82.0,
        "equipment_health": [
            {"equipment_id": 1, "name": "1号冷水机组", "overall_score": 85, "status": "healthy", "trend": "stable"},
            {"equipment_id": 2, "name": "2号冷水机组", "overall_score": 72, "status": "degrading", "trend": "down"},
            {"equipment_id": 3, "name": "1号冷却塔", "overall_score": 90, "status": "healthy", "trend": "stable"},
            {"equipment_id": 4, "name": "冷冻水泵A", "overall_score": 68, "status": "degrading", "trend": "down"},
        ],
        "top_degrading": [
            {"equipment_name": "冷冻水泵A", "component": "bearing", "score": 68, "degradation_rate": 1.2},
        ],
    }
