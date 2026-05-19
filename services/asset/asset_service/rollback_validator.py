import httpx


async def validate_rollback(
    entity_type: str,
    entity_id: str,
    target_snapshot: dict,
    asset_service_url: str,
    sim_service_url: str,
) -> dict:
    """Validate a rollback by running a quick simulation.

    Returns: {"passed": bool, "errors": list[str], "warnings": list[str], "cop_estimated": float}
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{sim_service_url}/api/simulation/run",
                json={
                    "plant_id": entity_id,
                    "outdoor_wb_temp": 26.0,
                    "outdoor_db_temp": 33.0,
                },
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                cop = data.get("snapshot", {}).get("system_cop", 0)
                if cop > 0:
                    return {
                        "passed": True,
                        "errors": [],
                        "warnings": [],
                        "cop_estimated": cop,
                    }
                return {
                    "passed": False,
                    "errors": ["Simulation returned COP <= 0"],
                    "warnings": [],
                    "cop_estimated": cop,
                }
            return {
                "passed": False,
                "errors": [f"Simulation failed: {resp.text}"],
                "warnings": [],
                "cop_estimated": 0,
            }
    except Exception as e:
        return {
            "passed": False,
            "errors": [str(e)],
            "warnings": [],
            "cop_estimated": 0,
        }
