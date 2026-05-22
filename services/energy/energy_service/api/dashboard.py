from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/dashboard")
async def energy_dashboard(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "current_cop": 5.2,
        "total_power_kw": 450.0,
        "cooling_load_rt": 200.0,
        "electricity_cost_per_hour": 360.0,
        "outdoor_wb_temp": 28.5,
        "trend": {
            "cop": [5.1, 5.3, 5.2, 5.4, 5.2],
            "power_kw": [440, 460, 455, 445, 450],
            "load_rt": [190, 210, 205, 195, 200],
        },
        "equipment_breakdown": {
            "chillers": 320.0,
            "pumps": 80.0,
            "cooling_towers": 50.0,
        },
    }


@router.get("/breakdown")
async def energy_breakdown(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "items": [
            {"equipment_name": "1号冷水机组", "power_kw": 180.0, "cop": 5.4, "load_rt": 85.0},
            {"equipment_name": "2号冷水机组", "power_kw": 140.0, "cop": 5.0, "load_rt": 65.0},
            {"equipment_name": "冷冻水泵组", "power_kw": 55.0, "flow_rate": 320.0},
            {"equipment_name": "冷却水泵组", "power_kw": 25.0, "flow_rate": 280.0},
            {"equipment_name": "冷却塔组", "power_kw": 50.0, "approach_temp": 3.2},
        ],
    }
