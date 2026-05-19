import json
import time

from fastapi import APIRouter, HTTPException, Request

from ..plant_builder import build_plant_from_services
from ..solver import run_plant_snapshot

router = APIRouter()


@router.post("/run")
async def run_simulation(data: dict, request: Request):
    """Run a single simulation snapshot for a plant."""
    plant_id = data["plant_id"]
    config = data.get("config", {})
    asset_url = request.app.state.asset_service_url
    env_url = request.app.state.env_service_url

    try:
        assembly = await build_plant_from_services(plant_id, asset_url, env_url)
    except Exception as e:
        raise HTTPException(500, f"Failed to build plant: {e}")

    outdoor_wb = data.get("outdoor_wb_temp", 26.0)
    outdoor_db = data.get("outdoor_db_temp", 33.0)

    result = run_plant_snapshot(assembly, config, outdoor_wb, outdoor_db)

    if hasattr(request.app.state, "redis") and request.app.state.redis:
        await request.app.state.redis.publish(
            "simulation:complete",
            json.dumps({
                "plant_id": plant_id,
                "timestamp": time.time(),
                "total_cooling_load_rt": result.get("total_cooling_load_rt", 0),
                "system_cop": result.get("system_cop", 0),
            }),
        )

    return {"status": "ok", "snapshot": result}
