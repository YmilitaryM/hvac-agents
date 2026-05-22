from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import bcrypt
from sqlalchemy import select

from common.db import create_engine, create_session_factory, Base
from common.metrics import MetricsMiddleware, metrics_endpoint

from .auth import router as auth_router
from .models import UserModel
from .proxy import proxy_request, SERVICE_URLS, register_ws_client, unregister_ws_client, broadcast_ws
from .audit_middleware import AuditMiddleware
from .rate_limiter import RateLimitMiddleware
from .circuit_breaker import CircuitBreakerMiddleware
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

    # Seed default admin user if no users exist
    async with app.state.session_factory() as session:
        result = await session.execute(select(UserModel).limit(1))
        if not result.scalar_one_or_none():
            session.add(UserModel(
                username="admin",
                hashed_password=bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode(),
                role="admin",
            ))
            await session.commit()

    SERVICE_URLS.update({
        "asset": s.asset_service_url,
        "environment": s.env_service_url,
        "simulation": s.sim_service_url,
        "agent": s.agent_service_url,
        "acquisition": s.acquisition_service_url,
        "edgemanager": s.edgemanager_service_url,
        "energy": s.energy_service_url,
        "health": s.health_service_url,
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
app.add_middleware(MetricsMiddleware, service_name="gateway")
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware, rate=100, burst=200)
app.add_middleware(CircuitBreakerMiddleware, failure_threshold=5, recovery_timeout=30.0)

app.include_router(auth_router, tags=["Auth"])
app.include_router(audit_router, prefix="/api/audit", tags=["Audit"])


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def api_proxy(request: Request, path: str):
    return await proxy_request(request)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway"}


@app.get("/metrics")
async def get_metrics():
    return metrics_endpoint()


@app.websocket("/ws/monitor")
async def ws_monitor(ws: WebSocket):
    await register_ws_client(ws)
    try:
        while True:
            # Keep-alive: accept messages from client (subscribe/unsubscribe)
            data = await ws.receive_text()
            # Client can send subscribe preferences, echoed for now
    except WebSocketDisconnect:
        pass
    finally:
        await unregister_ws_client(ws)
