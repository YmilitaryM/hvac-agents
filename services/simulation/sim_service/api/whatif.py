"""What-if scenario comparison API."""
import asyncio
import math

from fastapi import APIRouter, Request, HTTPException

from ..plant_builder import build_plant_from_services
from ..solver import run_plant_snapshot
from ..task_manager import TaskManager
from ..whatif_report import generate_comparison_report

router = APIRouter()

# Module-level task manager singleton, initialized during lifespan
_task_manager: TaskManager = None


def init_task_manager(redis_client=None) -> TaskManager:
    """Initialise (or re-initialise) the module-level task manager."""
    global _task_manager
    _task_manager = TaskManager(redis_client)
    return _task_manager


def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


@router.post("/whatif")
async def create_whatif(request: Request, data: dict):
    """Submit a what-if comparison job.

    Body: {
        "plant_id": "...",
        "weather_data": [...],   // optional, sequence of weather records
        "scenarios": [
            {"name": "baseline", "config": {"t_chw_setpoints": {"CH-1": 7.0}}},
            {"name": "optimized", "config": {"t_chw_setpoints": {"CH-1": 9.0}}}
        ],
        "num_hours": 8760       // optional, default 8760
    }
    Returns: {job_id, status: "running"}
    """
    plant_id = data["plant_id"]
    scenarios = data.get("scenarios", [])
    num_hours = data.get("num_hours", 8760)
    weather_data = data.get("weather_data", _generate_default_weather(num_hours))

    if len(scenarios) < 2:
        raise HTTPException(400, "At least 2 scenarios required for comparison")
    if len(scenarios) > 5:
        raise HTTPException(400, "Maximum 5 scenarios allowed")

    tm = get_task_manager()
    task_id = tm.create_task(
        "whatif",
        {
            "plant_id": plant_id,
            "num_hours": num_hours,
            "scenario_names": [s["name"] for s in scenarios],
        },
    )

    # Capture service URLs from app state before launching background task
    asset_url = request.app.state.asset_service_url
    env_url = request.app.state.env_service_url

    asyncio.create_task(
        _run_whatif(task_id, plant_id, scenarios, weather_data, num_hours, asset_url, env_url)
    )

    return {"job_id": task_id, "status": "running"}


@router.get("/whatif/{job_id}")
async def get_whatif_status(job_id: str):
    """Get what-if job status and progress."""
    tm = get_task_manager()
    task = tm.get_task(job_id)
    if not task:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job_id,
        "status": task["status"],
        "progress_pct": task["progress_pct"],
        "created_at": task.get("created_at"),
        "completed_at": task.get("completed_at"),
    }


@router.get("/whatif/{job_id}/report")
async def get_whatif_report(job_id: str):
    """Get the comparison report for a completed what-if job."""
    tm = get_task_manager()
    task = tm.get_task(job_id)
    if not task:
        raise HTTPException(404, "Job not found")
    if task["status"] != "completed":
        raise HTTPException(400, f"Job not completed (status: {task['status']})")
    return task["result"]


async def _run_whatif(
    task_id: str,
    plant_id: str,
    scenarios: list[dict],
    weather_data: list[dict],
    num_hours: int,
    asset_url: str,
    env_url: str,
):
    """Background task: run all scenarios and generate comparison."""
    tm = get_task_manager()
    sem = asyncio.Semaphore(10)  # max 10 concurrent simulation steps

    async def run_scenario(scenario: dict) -> dict:
        """Run a single scenario for all hours."""
        snapshots = []
        config = scenario.get("config", {})

        # Build the plant assembly once per scenario (avoids accumulating in-place mutation)
        assembly = await build_plant_from_services(plant_id, asset_url, env_url)

        async def run_hour(hour_idx: int):
            async with sem:
                weather = (
                    weather_data[hour_idx]
                    if hour_idx < len(weather_data)
                    else {"db_temp": 33.0, "wb_temp": 26.0}
                )
                try:
                    result = await run_plant_snapshot(
                        assembly, config,
                        weather.get("wb_temp", 26.0),
                        weather.get("db_temp", 33.0),
                        injector=None,
                    )
                    return result
                except Exception:
                    pass
                # Return error placeholder so failed hours are visible
                return {"_error": True, "total_power_kw": 0, "system_cop": 0, "total_cooling_load_rt": 0}

        # Run in batches for progress tracking
        batch_size = 100
        for batch_start in range(0, num_hours, batch_size):
            batch_end = min(batch_start + batch_size, num_hours)
            tasks = [run_hour(i) for i in range(batch_start, batch_end)]
            batch_results = await asyncio.gather(*tasks)
            snapshots.extend([r for r in batch_results if r])

            progress = batch_end / num_hours * 100
            tm.update_progress(task_id, progress)

        return {"name": scenario["name"], "snapshots": snapshots}

    try:
        # Run all scenarios
        scenario_tasks = [run_scenario(s) for s in scenarios]
        scenario_results = await asyncio.gather(*scenario_tasks)

        # Generate report
        report = generate_comparison_report(scenario_results)
        tm.complete_task(task_id, report)
    except Exception as e:
        tm.fail_task(task_id, str(e))


def _generate_default_weather(num_hours: int) -> list[dict]:
    """Generate default weather profile for simulation."""
    weather = []
    for h in range(num_hours):
        hour_of_day = h % 24
        month = (h // 730) % 12 + 1
        # Typical daily temperature cycle
        t_base = 28 + 8 * math.sin(2 * math.pi * (month - 1) / 12)  # seasonal
        t_daily = 6 * math.sin(2 * math.pi * (hour_of_day - 14) / 24)  # daily swing
        db_temp = t_base + t_daily
        wb_temp = db_temp - 5 - 3 * math.sin(2 * math.pi * (hour_of_day - 14) / 24)
        weather.append({"db_temp": round(db_temp, 1), "wb_temp": round(wb_temp, 1)})
    return weather
