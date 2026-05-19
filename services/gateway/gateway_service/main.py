from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from common.db import create_engine, create_session_factory, Base

from .auth import router as auth_router
from .proxy import proxy_request, SERVICE_URLS
from .audit_middleware import AuditMiddleware
from .api.audit import router as audit_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from common.config import get_settings
    s = get_settings()
    engine = create_engine(s.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    SERVICE_URLS.update({
        "asset": s.asset_service_url,
        "environment": s.env_service_url,
        "simulation": s.sim_service_url,
        "agent": s.agent_service_url,
    })
    yield
    await engine.dispose()


app = FastAPI(title="HVAC API Gateway", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

app.include_router(auth_router, tags=["Auth"])
app.include_router(audit_router, prefix="/api/audit", tags=["Audit"])


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def api_proxy(request: Request, path: str):
    return await proxy_request(request)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway"}
