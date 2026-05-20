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
    "/api/alerts": "agent",
    "/api/versions": "asset",
    "/api/prediction": "agent",
    "/api/benchmarking": "agent",
    "/api/rl": "agent",
    "/api/acquisition": "acquisition",
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

    # Forward relevant headers to backend services
    headers = {}
    for key in ("authorization", "content-type", "accept", "x-request-id", "x-correlation-id"):
        val = request.headers.get(key)
        if val:
            headers[key] = val

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if request.method == "GET":
                resp = await client.get(target_url, params=params, headers=headers)
            elif request.method == "POST":
                body = await request.json()
                resp = await client.post(target_url, json=body, params=params, headers=headers)
            elif request.method == "PUT":
                body = await request.json()
                resp = await client.put(target_url, json=body, params=params, headers=headers)
            elif request.method == "DELETE":
                resp = await client.delete(target_url, params=params, headers=headers)
            else:
                raise HTTPException(405, "Method not allowed")
    except httpx.ConnectError:
        raise HTTPException(502, f"Backend {backend} unavailable")
    except httpx.TimeoutException:
        raise HTTPException(504, f"Backend {backend} timed out")

    content_type = resp.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        return resp.json()
    return resp.text
