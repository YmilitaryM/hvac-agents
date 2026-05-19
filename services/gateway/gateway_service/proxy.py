import httpx
from fastapi import Request, HTTPException

SERVICE_ROUTES = {
    "/api/equipment": "asset",
    "/api/plants": "asset",
    "/api/templates": "asset",
    "/api/env": "environment",
    "/api/simulation": "simulation",
    "/api/faults": "simulation",
    "/api/monitoring": "agent",
    "/api/strategies": "agent",
    "/api/reports": "agent",
}

SERVICE_URLS = {}


def get_backend(path: str) -> str | None:
    for prefix, svc in SERVICE_ROUTES.items():
        if path.startswith(prefix):
            return svc
    return None


async def proxy_request(request: Request):
    backend = get_backend(request.url.path)
    if not backend:
        raise HTTPException(404, "No backend for path")

    target_url = f"{SERVICE_URLS[backend]}{request.url.path}"
    params = dict(request.query_params)

    async with httpx.AsyncClient() as client:
        if request.method == "GET":
            resp = await client.get(target_url, params=params)
        elif request.method == "POST":
            body = await request.json()
            resp = await client.post(target_url, json=body, params=params)
        elif request.method == "PUT":
            body = await request.json()
            resp = await client.put(target_url, json=body, params=params)
        elif request.method == "DELETE":
            resp = await client.delete(target_url, params=params)
        else:
            raise HTTPException(405, "Method not allowed")

    content_type = resp.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        return resp.json()
    return resp.text
