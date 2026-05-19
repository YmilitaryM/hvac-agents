"""Fetch prediction input data from Environment and Asset services."""
import httpx
from typing import Optional

class PredictionDataFetcher:
    def __init__(self, env_service_url: str = "http://localhost:8002",
                 asset_service_url: str = "http://localhost:8001"):
        self.env_url = env_service_url
        self.asset_url = asset_service_url

    async def fetch_weather(self, timestamp: float = None) -> dict:
        """Fetch current weather from Environment Service."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.env_url}/api/env/weather", timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("records", [])
                    if records:
                        return records[0]
        except Exception:
            pass
        return {"db_temp": 33.0, "wb_temp": 26.0, "rh": 60, "solar_radiation": 500}

    async def fetch_building(self, building_id: str) -> dict:
        """Fetch building parameters from Environment Service."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.env_url}/api/env/buildings/{building_id}", timeout=5.0)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {"area_m2": 5000, "floor_count": 3, "building_type": "office"}

    async def fetch_indoor_conditions(self, building_id: str) -> dict:
        """Fetch indoor conditions from Environment Service."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.env_url}/api/env/buildings/{building_id}/indoor", timeout=5.0)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {"indoor_temp": 24.0, "occupancy_count": 20, "lighting_power_kw": 50, "equipment_power_kw": 75}

    async def fetch_all(self, building_id: str, timestamp: float = None) -> dict:
        """Fetch all prediction inputs concurrently."""
        import asyncio
        weather, building, indoor = await asyncio.gather(
            self.fetch_weather(timestamp),
            self.fetch_building(building_id),
            self.fetch_indoor_conditions(building_id),
        )
        return {"weather": weather, "building": building, "indoor": indoor}
