import httpx
from common.config import get_settings


class AssetForwarder:
    def __init__(self, asset_service_url: str | None = None):
        s = get_settings()
        self._url = (asset_service_url or s.asset_service_url).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10)
        return self._client

    async def update_current_values(self, updates: list[dict]) -> None:
        client = await self._get_client()
        resp = await client.post(f"{self._url}/api/equipment/points/batch-update", json={"updates": updates})
        resp.raise_for_status()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
