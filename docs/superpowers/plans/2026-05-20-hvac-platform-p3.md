# HVAC Platform P3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build edge-cloud ops automation with predictive maintenance, auto-inspection work orders, and edge-cloud sync — deployable on both Docker servers and bare-metal industrial PCs.

**Architecture:** Add a new cloud microservice (Edge Manager :8006) and an independent edge monolith (`hvac-edge`) with DuckDB + ONNX runtime. Extend Agent Service with predictive maintenance and work order modules. Introduce MQTT for edge-cloud real-time communication while keeping HTTP for bulk data sync.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL, DuckDB, MQTT (eclipse-mosquitto), ONNX Runtime, XGBoost (sklearn), Pydantic v2, asyncio, Docker Compose, bare-metal systemd

---

## File Structure Map

```
# === New: Edge Manager Service ===
services/edgemanager/
├── pyproject.toml
├── Dockerfile
├── edgemanager_service/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan
│   ├── models.py                  # EdgeDevice, Heartbeat, OTATask, SyncWatermark
│   ├── mqtt_client.py             # MQTT subscriber (status alerts)
│   └── api/
│       ├── __init__.py
│       ├── registry.py            # POST register, GET list
│       ├── heartbeat.py           # POST heartbeat, GET status
│       ├── config.py              # POST config, GET config
│       ├── data.py                # POST ingest (bulk readings)
│       └── ota.py                 # POST create task, GET task status
└── tests/

# === New: Edge Monolith (standalone package, not in workspace) ===
hvac-edge/
├── pyproject.toml
├── edge/
│   ├── __init__.py
│   ├── main.py                    # asyncio entry point + lifecycle
│   ├── config.py                  # YAML config loader
│   ├── db.py                      # DuckDB connection + table init
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── collector.py           # polling engine + 3 protocol adapters
│   │   ├── controller.py          # safety gate + pid + interlock
│   │   └── inspector.py           # inspection plans + L1 anomaly + local work orders
│   ├── ml/
│   │   ├── __init__.py
│   │   └── runtime.py             # ONNX inference wrapper
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── agent.py               # MQTT publisher + HTTP bulk upload + offline buffer
│   │   └── queue.py               # DuckDB-backed persistent outbox
│   └── templates/
│       └── default_inspection.yaml
├── models/                        # placeholder for .onnx files
└── tests/

# === Modified: Agent Service ===
services/agent/agent_service/
├── predictive_maintenance/
│   ├── __init__.py
│   ├── models.py                  # DegradationResult, FailurePrediction, MaintenancePlan
│   ├── degradation_tracker.py     # CUSUM + COP drift + approach temp + vibration
│   ├── failure_predictor.py       # XGBoost training + ONNX export
│   ├── maintenance_scheduler.py   # window recommendation
│   ├── rule_advisor.py            # threshold → action mapping
│   └── api/
│       ├── __init__.py
│       └── maintenance.py         # REST endpoints
├── workorder/
│   ├── __init__.py
│   ├── models.py                  # WorkOrder, WorkOrderLog
│   ├── lifecycle.py               # state machine
│   ├── auto_generator.py          # anomaly → work order
│   ├── assignment.py              # role/skill-based assignment
│   └── api/
│       ├── __init__.py
│       └── workorders.py          # REST endpoints
└── api/
    └── (existing files, add router registrations)

# === Modified: Docker Compose ===
docker-compose.yml              # +mosquitto, +edgemanager, +edge_db

# === Modified: Common ===
common/common/
└── mqtt.py                     # shared MQTT client helper (optional)
```

---

## Phase 1: Edge Manager Service + MQTT Broker (P3-A)

### Task 1: Edge Manager Service scaffold

**Files:**
- Create: `services/edgemanager/pyproject.toml`
- Create: `services/edgemanager/Dockerfile`
- Create: `services/edgemanager/edgemanager_service/__init__.py` (empty)
- Create: `services/edgemanager/edgemanager_service/main.py`
- Create: `services/edgemanager/edgemanager_service/models.py`
- Create: `services/edgemanager/edgemanager_service/api/__init__.py`
- Create: `services/edgemanager/tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "edgemanager-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "hvac-common",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "httpx>=0.28",
    "aiomqtt>=2.0",
]

[tool.uv.sources]
hvac-common = { workspace = true }
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
COPY common common/
COPY services/edgemanager services/edgemanager/
RUN uv sync --frozen --package edgemanager-service --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY common common/
COPY services/edgemanager services/edgemanager/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "edgemanager_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write models.py**

```python
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Float, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from common.db import Base


class EdgeDevice(Base):
    __tablename__ = "edge_devices"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    plant_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(16), default="hybrid")
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    config_hash: Mapped[Optional[str]] = mapped_column(String(64))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Heartbeat(Base):
    __tablename__ = "heartbeats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(32), ForeignKey("edge_devices.id"), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    cpu_pct: Mapped[Optional[float]] = mapped_column(Float)
    mem_mb: Mapped[Optional[float]] = mapped_column(Float)
    disk_pct: Mapped[Optional[float]] = mapped_column(Float)
    collector_ok: Mapped[Optional[bool]] = mapped_column(Boolean)
    controller_ok: Mapped[Optional[bool]] = mapped_column(Boolean)
    inspector_ok: Mapped[Optional[bool]] = mapped_column(Boolean)


class OTATask(Base):
    __tablename__ = "ota_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(32), ForeignKey("edge_devices.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class SyncWatermark(Base):
    __tablename__ = "sync_watermarks"

    edge_id: Mapped[str] = mapped_column(String(32), ForeignKey("edge_devices.id"), primary_key=True)
    table_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_synced_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 4: Write main.py**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.config import get_settings
from common.db import create_engine, create_session_factory
from common.common.metrics import setup_metrics
from .models import Base
from .api import registry, heartbeat, config, data, ota


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    engine = create_engine(s.database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


app = FastAPI(title="Edge Manager Service", version="0.1.0", lifespan=lifespan)
setup_metrics(app)

app.include_router(registry.router, prefix="/api/edges", tags=["Registry"])
app.include_router(heartbeat.router, prefix="/api/edges", tags=["Heartbeat"])
app.include_router(config.router, prefix="/api/edges", tags=["Config"])
app.include_router(data.router, prefix="/api/edges", tags=["Data"])
app.include_router(ota.router, prefix="/api/edges", tags=["OTA"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "edgemanager"}
```

- [ ] **Step 5: Commit**

```bash
git add services/edgemanager/
git commit -m "feat(p3): add Edge Manager Service scaffold with models"
```

---

### Task 2: Edge Manager API — registry & heartbeat

**Files:**
- Create: `services/edgemanager/edgemanager_service/api/registry.py`
- Create: `services/edgemanager/edgemanager_service/api/heartbeat.py`
- Create: `services/edgemanager/tests/test_registry.py`
- Create: `services/edgemanager/tests/test_heartbeat.py`

- [ ] **Step 1: Write failing tests for registry**

```python
# services/edgemanager/tests/test_registry.py
import pytest
from httpx import ASGITransport, AsyncClient
from edgemanager_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register_edge_device(client):
    payload = {
        "id": "edge-001",
        "name": "Station A Edge",
        "plant_id": "plant-001",
        "mode": "hybrid",
        "version": "0.1.0",
    }
    resp = await client.post("/api/edges/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "edge-001"
    assert data["mode"] == "hybrid"


@pytest.mark.asyncio
async def test_list_edge_devices(client):
    resp = await client.get("/api/edges/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_register_duplicate_rejected(client):
    payload = {"id": "edge-002", "name": "Dup", "plant_id": "p1", "version": "0.1.0"}
    await client.post("/api/edges/register", json=payload)
    resp = await client.post("/api/edges/register", json=payload)
    assert resp.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/edgemanager && python -m pytest tests/test_registry.py -v
```
Expected: 404/405 errors (routes not defined)

- [ ] **Step 3: Implement registry.py**

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import create_session_factory
from ..models import EdgeDevice

router = APIRouter()


class RegisterRequest(BaseModel):
    id: str
    name: str
    plant_id: str
    mode: str = "hybrid"
    version: str


class EdgeDeviceResponse(BaseModel):
    id: str
    name: str
    plant_id: str
    mode: str
    version: str
    registered_at: str | None = None
    last_seen_at: str | None = None


async def get_db(request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


@router.post("/register", status_code=201, response_model=EdgeDeviceResponse)
async def register_device(body: RegisterRequest, session: AsyncSession = Depends(get_db)):
    existing = await session.get(EdgeDevice, body.id)
    if existing:
        raise HTTPException(status_code=409, detail="Edge device already registered")

    device = EdgeDevice(
        id=body.id,
        name=body.name,
        plant_id=body.plant_id,
        mode=body.mode,
        version=body.version,
        registered_at=datetime.now(timezone.utc),
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return _to_response(device)


@router.get("/", response_model=list[EdgeDeviceResponse])
async def list_devices(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(EdgeDevice).order_by(EdgeDevice.registered_at.desc()))
    return [_to_response(d) for d in result.scalars().all()]


@router.get("/{edge_id}", response_model=EdgeDeviceResponse)
async def get_device(edge_id: str, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")
    return _to_response(device)


def _to_response(d: EdgeDevice) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "plant_id": d.plant_id,
        "mode": d.mode,
        "version": d.version,
        "registered_at": d.registered_at.isoformat() if d.registered_at else None,
        "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
    }
```

- [ ] **Step 4: Run registry tests to verify pass**

```bash
cd services/edgemanager && python -m pytest tests/test_registry.py -v
```
Expected: all 3 pass

- [ ] **Step 5: Write failing tests for heartbeat**

```python
# services/edgemanager/tests/test_heartbeat.py
import pytest
from httpx import ASGITransport, AsyncClient
from edgemanager_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Register an edge first
        await c.post("/api/edges/register", json={
            "id": "edge-hb-001",
            "name": "HB Test",
            "plant_id": "plant-001",
            "version": "0.1.0",
        })
        yield c


@pytest.mark.asyncio
async def test_post_heartbeat(client):
    payload = {
        "cpu_pct": 45.2,
        "mem_mb": 512.0,
        "disk_pct": 30.1,
        "collector_ok": True,
        "controller_ok": True,
        "inspector_ok": False,
    }
    resp = await client.post("/api/edges/edge-hb-001/heartbeat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_heartbeat_updates_last_seen(client):
    await client.post("/api/edges/edge-hb-001/heartbeat", json={"cpu_pct": 10.0})
    resp = await client.get("/api/edges/edge-hb-001")
    assert resp.json()["last_seen_at"] is not None


@pytest.mark.asyncio
async def test_heartbeat_unknown_edge(client):
    resp = await client.post("/api/edges/edge-unknown/heartbeat", json={"cpu_pct": 10.0})
    assert resp.status_code == 404
```

- [ ] **Step 6: Run heartbeat tests to verify they fail**

```bash
cd services/edgemanager && python -m pytest tests/test_heartbeat.py -v
```
Expected: FAIL (route not found)

- [ ] **Step 7: Implement heartbeat.py**

```python
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EdgeDevice, Heartbeat

router = APIRouter()


class HeartbeatRequest(BaseModel):
    cpu_pct: Optional[float] = None
    mem_mb: Optional[float] = None
    disk_pct: Optional[float] = None
    collector_ok: Optional[bool] = None
    controller_ok: Optional[bool] = None
    inspector_ok: Optional[bool] = None


async def get_db(request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


@router.post("/{edge_id}/heartbeat")
async def post_heartbeat(edge_id: str, body: HeartbeatRequest, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    now = datetime.now(timezone.utc)
    hb = Heartbeat(
        edge_id=edge_id,
        received_at=now,
        cpu_pct=body.cpu_pct,
        mem_mb=body.mem_mb,
        disk_pct=body.disk_pct,
        collector_ok=body.collector_ok,
        controller_ok=body.controller_ok,
        inspector_ok=body.inspector_ok,
    )
    device.last_seen_at = now
    session.add(hb)
    await session.commit()
    return {"status": "ok"}


@router.get("/{edge_id}/status")
async def get_status(edge_id: str, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    from sqlalchemy import select, desc
    result = await session.execute(
        select(Heartbeat).where(Heartbeat.edge_id == edge_id).order_by(desc(Heartbeat.received_at)).limit(1)
    )
    latest = result.scalar_one_or_none()

    return {
        "device_id": edge_id,
        "online": device.last_seen_at is not None,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "latest_heartbeat": {
            "cpu_pct": latest.cpu_pct,
            "mem_mb": latest.mem_mb,
            "disk_pct": latest.disk_pct,
            "collector_ok": latest.collector_ok,
            "controller_ok": latest.controller_ok,
            "inspector_ok": latest.inspector_ok,
        } if latest else None,
    }
```

- [ ] **Step 8: Run heartbeat tests to verify pass**

```bash
cd services/edgemanager && python -m pytest tests/test_heartbeat.py -v
```
Expected: all 3 pass

- [ ] **Step 9: Commit**

```bash
git add services/edgemanager/
git commit -m "feat(p3): add Edge Manager registry and heartbeat API"
```

---

### Task 3: Edge Manager API — config & OTA

**Files:**
- Create: `services/edgemanager/edgemanager_service/api/config.py`
- Create: `services/edgemanager/edgemanager_service/api/ota.py`
- Create: `services/edgemanager/tests/test_config.py`
- Create: `services/edgemanager/tests/test_ota.py`

- [ ] **Step 1: Write failing config test**

```python
# services/edgemanager/tests/test_config.py
import pytest
from httpx import ASGITransport, AsyncClient
from edgemanager_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/edges/register", json={
            "id": "edge-cfg-001",
            "name": "Config Test",
            "plant_id": "plant-001",
            "version": "0.1.0",
        })
        yield c


@pytest.mark.asyncio
async def test_set_config(client):
    payload = {"mode": "live", "acquisition": {"poll_interval_ms": 500}}
    resp = await client.post("/api/edges/edge-cfg-001/config", json=payload)
    assert resp.status_code == 200
    assert resp.json()["config_hash"] is not None


@pytest.mark.asyncio
async def test_get_config(client):
    resp = await client.get("/api/edges/edge-cfg-001/config")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_set_config_unknown_edge(client):
    resp = await client.post("/api/edges/edge-unknown/config", json={"mode": "live"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run config tests to verify they fail**

```bash
cd services/edgemanager && python -m pytest tests/test_config.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement config.py**

```python
import hashlib, json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import EdgeDevice

router = APIRouter()


class ConfigPayload(BaseModel):
    mode: str | None = None
    acquisition: dict | None = None
    control: dict | None = None
    inspection: dict | None = None
    ml: dict | None = None


async def get_db(request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


def _hash_config(cfg: dict) -> str:
    raw = json.dumps(cfg, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@router.post("/{edge_id}/config")
async def set_config(edge_id: str, body: ConfigPayload, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    device.config_hash = _hash_config(body.model_dump(exclude_none=True))
    await session.commit()

    return {
        "edge_id": edge_id,
        "config_hash": device.config_hash,
        "config": body.model_dump(exclude_none=True),
    }


@router.get("/{edge_id}/config")
async def get_config(edge_id: str, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    return {
        "edge_id": edge_id,
        "config_hash": device.config_hash,
    }
```

- [ ] **Step 4: Run config tests to verify pass**

```bash
cd services/edgemanager && python -m pytest tests/test_config.py -v
```
Expected: all 3 pass

- [ ] **Step 5: Write failing OTA test**

```python
# services/edgemanager/tests/test_ota.py
import pytest
from httpx import ASGITransport, AsyncClient
from edgemanager_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/edges/register", json={
            "id": "edge-ota-001",
            "name": "OTA Test",
            "plant_id": "plant-001",
            "version": "0.1.0",
        })
        yield c


@pytest.mark.asyncio
async def test_create_ota_task(client):
    payload = {
        "target_type": "model",
        "version": "anomaly_v2.onnx",
        "payload_url": "https://models.example.com/anomaly_v2.onnx",
    }
    resp = await client.post("/api/edges/edge-ota-001/ota", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_ota_task(client):
    payload = {"target_type": "model", "version": "v1", "payload_url": "https://x.com/m.onnx"}
    create = await client.post("/api/edges/edge-ota-001/ota", json=payload)
    task_id = create.json()["id"]

    resp = await client.get(f"/api/edges/edge-ota-001/ota/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == task_id
```

- [ ] **Step 6: Run OTA tests to verify they fail**

```bash
cd services/edgemanager && python -m pytest tests/test_ota.py -v
```
Expected: FAIL

- [ ] **Step 7: Implement ota.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import EdgeDevice, OTATask

router = APIRouter()


class OTACreateRequest(BaseModel):
    target_type: str
    version: str
    payload_url: str


class OTATaskResponse(BaseModel):
    id: int
    edge_id: str
    target_type: str
    version: str
    payload_url: str
    status: str
    created_at: str | None
    completed_at: str | None


async def get_db(request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


def _to_response(t: OTATask) -> dict:
    return {
        "id": t.id,
        "edge_id": t.edge_id,
        "target_type": t.target_type,
        "version": t.version,
        "payload_url": t.payload_url,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


@router.post("/{edge_id}/ota", status_code=201, response_model=OTATaskResponse)
async def create_ota(edge_id: str, body: OTACreateRequest, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    task = OTATask(
        edge_id=edge_id,
        target_type=body.target_type,
        version=body.version,
        payload_url=body.payload_url,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return _to_response(task)


@router.get("/{edge_id}/ota/{task_id}", response_model=OTATaskResponse)
async def get_ota(edge_id: str, task_id: int, session: AsyncSession = Depends(get_db)):
    task = await session.get(OTATask, task_id)
    if not task or task.edge_id != edge_id:
        raise HTTPException(status_code=404, detail="OTA task not found")
    return _to_response(task)


@router.get("/{edge_id}/ota/", response_model=list[OTATaskResponse])
async def list_ota(edge_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(OTATask).where(OTATask.edge_id == edge_id).order_by(OTATask.created_at.desc())
    )
    return [_to_response(t) for t in result.scalars().all()]
```

- [ ] **Step 8: Run OTA tests to verify pass**

```bash
cd services/edgemanager && python -m pytest tests/test_ota.py -v
```
Expected: all 2 pass

- [ ] **Step 9: Commit**

```bash
git add services/edgemanager/
git commit -m "feat(p3): add Edge Manager config and OTA API"
```

---

### Task 4: Edge Manager — data ingest & MQTT client

**Files:**
- Create: `services/edgemanager/edgemanager_service/api/data.py`
- Create: `services/edgemanager/edgemanager_service/mqtt_client.py`
- Create: `services/edgemanager/tests/test_data.py`

- [ ] **Step 1: Write failing data ingest test**

```python
# services/edgemanager/tests/test_data.py
import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from edgemanager_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/edges/register", json={
            "id": "edge-data-001",
            "name": "Data Test",
            "plant_id": "plant-001",
            "version": "0.1.0",
        })
        yield c


@pytest.mark.asyncio
async def test_ingest_readings(client):
    payload = {
        "readings": [
            {"time": "2026-05-20T10:00:00Z", "point_id": "p1", "value": 23.5, "quality": "good"},
            {"time": "2026-05-20T10:15:00Z", "point_id": "p1", "value": 24.0, "quality": "good"},
        ],
        "inspections": [],
        "work_orders": [],
    }
    resp = await client.post("/api/edges/edge-data-001/data/ingest", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["readings_received"] == 2
    assert "watermark" in data


@pytest.mark.asyncio
async def test_ingest_updates_watermark(client):
    payload = {"readings": [
        {"time": "2026-05-20T11:00:00Z", "point_id": "p2", "value": 30.0, "quality": "good"},
    ], "inspections": [], "work_orders": []}
    await client.post("/api/edges/edge-data-001/data/ingest", json=payload)

    from sqlalchemy import select
    from edgemanager_service.models import SyncWatermark

    async with app.state.session_factory() as session:
        result = await session.execute(
            select(SyncWatermark).where(
                SyncWatermark.edge_id == "edge-data-001",
                SyncWatermark.table_name == "readings",
            )
        )
        wm = result.scalar_one_or_none()
        assert wm is not None
```

- [ ] **Step 2: Run data tests to verify they fail**

```bash
cd services/edgemanager && python -m pytest tests/test_data.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement data.py**

```python
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import EdgeDevice, SyncWatermark

router = APIRouter()


class ReadingPoint(BaseModel):
    time: str
    point_id: str
    value: float
    quality: str = "good"


class InspectionRecord(BaseModel):
    id: int
    started_at: str
    ended_at: Optional[str] = None
    plan_id: str
    status: str
    result: Optional[dict] = None


class WorkOrderRecord(BaseModel):
    id: int
    created_at: str
    equipment_id: str
    severity: str
    title: str
    description: Optional[str] = None
    status: str


class IngestPayload(BaseModel):
    readings: list[ReadingPoint]
    inspections: list[InspectionRecord] = []
    work_orders: list[WorkOrderRecord] = []


async def get_db(request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


@router.post("/{edge_id}/data/ingest")
async def ingest_data(edge_id: str, body: IngestPayload, session: AsyncSession = Depends(get_db)):
    device = await session.get(EdgeDevice, edge_id)
    if not device:
        raise HTTPException(status_code=404, detail="Edge device not found")

    latest_time = None
    if body.readings:
        latest_time = max(r.time for r in body.readings)
        # In production, upsert readings into a timeseries store
        # For P3, we track the watermark and forward to Agent Service

    # Update sync watermark
    if latest_time:
        wm = await session.get(SyncWatermark, {"edge_id": edge_id, "table_name": "readings"})
        parsed_time = datetime.fromisoformat(latest_time.replace("Z", "+00:00"))
        if wm:
            if parsed_time > wm.last_synced_until:
                wm.last_synced_until = parsed_time
        else:
            wm = SyncWatermark(edge_id=edge_id, table_name="readings", last_synced_until=parsed_time)
            session.add(wm)

    await session.commit()

    return {
        "readings_received": len(body.readings),
        "inspections_received": len(body.inspections),
        "work_orders_received": len(body.work_orders),
        "watermark": latest_time,
    }
```

- [ ] **Step 4: Run data tests to verify pass**

```bash
cd services/edgemanager && python -m pytest tests/test_data.py -v
```
Expected: all 2 pass

- [ ] **Step 5: Implement mqtt_client.py (skeleton)**

```python
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class EdgeMQTTClient:
    """Cloud-side MQTT client for edge communication."""

    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self._connected = False
        self._handlers: dict[str, list] = {}

    def on_topic(self, topic: str, handler):
        self._handlers.setdefault(topic, []).append(handler)

    async def start(self):
        # In production, use aiomqtt client.connect()
        # For now, log setup intent
        logger.info(f"MQTT client configured for {self.broker_host}:{self.broker_port}")
        self._connected = True

    async def stop(self):
        self._connected = False

    async def publish(self, topic: str, payload: dict, qos: int = 1):
        logger.info(f"MQTT publish → {topic}: {json.dumps(payload)}")
```

- [ ] **Step 6: Commit**

```bash
git add services/edgemanager/
git commit -m "feat(p3): add data ingest API and MQTT client skeleton"
```

---

### Task 5: Add Mosquitto + Edge Manager to docker-compose

**Files:**
- Modify: `docker-compose.yml`
- Modify: `services/gateway/gateway_service/main.py` (optional: route edgemanager)

- [ ] **Step 1: Add Mosquitto and edgemanager services**

In `docker-compose.yml`, add after the existing services:

```yaml
  postgres_edge:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: edge_db
      POSTGRES_USER: hvac
      POSTGRES_PASSWORD: hvac_dev
    ports: ["5438:5432"]
    volumes: [pg_edge:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hvac -d edge_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  mosquitto:
    image: eclipse-mosquitto:2.0
    ports: ["1883:1883", "9001:9001"]
    volumes:
      - ./services/edgemanager/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - mosquitto_data:/mosquitto/data

  edgemanager:
    build:
      context: .
      dockerfile: services/edgemanager/Dockerfile
    ports: ["8006:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://hvac:hvac_dev@postgres_edge:5432/edge_db
      MQTT_HOST: mosquitto
      JWT_SECRET: dev-secret-change-in-prod
    depends_on:
      postgres_edge:
        condition: service_healthy
      mosquitto:
        condition: service_started
```

Add to volumes:

```yaml
volumes:
  pg_asset: ~
  tsdb: ~
  pg_sim: ~
  pg_agent: ~
  pg_edge: ~
  mosquitto_data: ~
  mosquitto_config: ~
```

- [ ] **Step 2: Create mosquitto.conf**

```bash
mkdir -p services/edgemanager
```

Create `services/edgemanager/mosquitto.conf`:

```
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data
max_queued_messages 10000
max_inflight_messages 100
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml services/edgemanager/mosquitto.conf
git commit -m "feat(p3): add Mosquitto MQTT broker and Edge Manager to Docker Compose"
```

---

## Phase 2: Edge Monolith hvac-edge (P3-A)

### Task 6: hvac-edge project scaffold + config + DuckDB

**Files:**
- Create: `hvac-edge/pyproject.toml`
- Create: `hvac-edge/edge/__init__.py`
- Create: `hvac-edge/edge/main.py`
- Create: `hvac-edge/edge/config.py`
- Create: `hvac-edge/edge/db.py`
- Create: `hvac-edge/edge/templates/default_inspection.yaml`
- Create: `hvac-edge/tests/test_db.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "hvac-edge"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "duckdb>=1.1",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "aiomqtt>=2.0",
    "httpx>=0.28",
    "onnxruntime>=1.19",
    "pymodbus>=3.7",
    "BAC0>=23.0",
    "asyncua>=1.0",
]
```

- [ ] **Step 2: Write config.py**

```python
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel


class AcquisitionConfig(BaseModel):
    poll_interval_ms: int = 1000
    protocols: list[dict] = []


class ControlConfig(BaseModel):
    safety_gate: bool = True
    pid_enabled: bool = True
    interlock_enabled: bool = True


class InspectionConfig(BaseModel):
    plans_dir: str = "/etc/hvac-edge/plans"
    default_interval_hours: int = 4


class MLConfig(BaseModel):
    onnx_model_path: str = ""
    feature_window_hours: int = 24


class EdgeConfig(BaseModel):
    edge_id: str = ""
    plant_id: str = ""
    mode: str = "hybrid"
    cloud_api_url: str = "http://localhost:8006"
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    acquisition: AcquisitionConfig = AcquisitionConfig()
    control: ControlConfig = ControlConfig()
    inspection: InspectionConfig = InspectionConfig()
    ml: MLConfig = MLConfig()
    db_path: str = "edge_data.duckdb"


def load_config(path: str | Path = "edge_config.yaml") -> EdgeConfig:
    path = Path(path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    return EdgeConfig(**data)
```

- [ ] **Step 3: Write db.py**

```python
import duckdb


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS readings (
    time       TIMESTAMPTZ NOT NULL,
    point_id   VARCHAR(32) NOT NULL,
    value      DOUBLE NOT NULL,
    quality    VARCHAR(16) DEFAULT 'good',
    PRIMARY KEY (time, point_id)
);

CREATE TABLE IF NOT EXISTS inspections (
    id         BIGINT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at   TIMESTAMPTZ,
    plan_id    VARCHAR(64) NOT NULL,
    status     VARCHAR(16) DEFAULT 'running',
    result     JSON
);

CREATE TABLE IF NOT EXISTS work_orders (
    id            BIGINT PRIMARY KEY,
    created_at    TIMESTAMPTZ NOT NULL,
    equipment_id  VARCHAR(32) NOT NULL,
    severity      VARCHAR(16) NOT NULL,
    title         VARCHAR(256) NOT NULL,
    description   TEXT,
    status        VARCHAR(16) DEFAULT 'open',
    synced_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sync_queue (
    id         BIGINT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    topic      VARCHAR(128) NOT NULL,
    payload    JSON NOT NULL,
    qos        TINYINT DEFAULT 1,
    retries    INT DEFAULT 0,
    synced     BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS sync_meta (
    table_name   VARCHAR(64) PRIMARY KEY,
    last_sent_at TIMESTAMPTZ NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS seq_inspection_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_work_order_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_sync_queue_id START 1;
"""


def init_db(path: str = "edge_data.duckdb") -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(path)
    conn.execute(SCHEMA_SQL)
    return conn
```

- [ ] **Step 4: Write failing db test**

```python
# hvac-edge/tests/test_db.py
import tempfile, os
from edge.db import init_db


def test_init_db_creates_tables():
    db_path = os.path.join(tempfile.mkdtemp(), "test.duckdb")
    conn = init_db(db_path)

    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    table_names = [t[0] for t in tables]

    assert "readings" in table_names
    assert "inspections" in table_names
    assert "work_orders" in table_names
    assert "sync_queue" in table_names
    assert "sync_meta" in table_names
    conn.close()


def test_insert_and_query_reading():
    db_path = os.path.join(tempfile.mkdtemp(), "test2.duckdb")
    conn = init_db(db_path)

    conn.execute(
        "INSERT INTO readings (time, point_id, value, quality) VALUES ('2026-05-20T10:00:00Z', 'p1', 23.5, 'good')"
    )
    result = conn.execute("SELECT value FROM readings WHERE point_id = 'p1'").fetchone()
    assert result[0] == 23.5
    conn.close()
```

- [ ] **Step 5: Run db tests to verify pass**

```bash
cd hvac-edge && python -m pytest tests/test_db.py -v
```
Expected: PASS (no FastAPI needed, pure DuckDB)

- [ ] **Step 6: Write main.py skeleton**

```python
import asyncio
import logging

from .config import load_config
from .db import init_db

logger = logging.getLogger(__name__)


async def main():
    cfg = load_config()
    logger.info(f"Starting hvac-edge {cfg.edge_id} in {cfg.mode} mode")

    db = init_db(cfg.db_path)
    logger.info(f"DuckDB initialized at {cfg.db_path}")

    # Engines will be started here in later tasks
    try:
        while True:
            await asyncio.sleep(60)
            logger.debug("Edge heartbeat tick")
    except asyncio.CancelledError:
        logger.info("Shutting down hvac-edge")
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

- [ ] **Step 7: Write default inspection template**

```yaml
# hvac-edge/edge/templates/default_inspection.yaml
plan_id: default-daily
description: Daily chiller plant inspection checklist
interval_hours: 4
items:
  - id: chk-chiller-cop
    equipment_type: chiller
    check: cop_degradation
    params:
      threshold_pct: 10
    severity: warning

  - id: chk-chiller-approach
    equipment_type: chiller
    check: approach_temp
    params:
      max_delta_k: 3.0
    severity: warning

  - id: chk-tower-approach
    equipment_type: cooling_tower
    check: approach_temp
    params:
      max_delta_k: 5.0
    severity: warning

  - id: chk-pump-vibration
    equipment_type: pump
    check: vibration_rms
    params:
      max_rms: 7.0
    severity: critical

  - id: chk-valve-stuck
    equipment_type: valve
    check: stuck_detection
    params:
      min_position_change: 0.02
      window_minutes: 30
    severity: warning
```

- [ ] **Step 8: Commit**

```bash
git add hvac-edge/
git commit -m "feat(p3): add hvac-edge project scaffold with config, DuckDB, and inspection templates"
```

---

### Task 7: hvac-edge collector engine

**Files:**
- Create: `hvac-edge/edge/engine/__init__.py`
- Create: `hvac-edge/edge/engine/collector.py`
- Create: `hvac-edge/tests/test_collector.py`

- [ ] **Step 1: Write failing collector test**

```python
# hvac-edge/tests/test_collector.py
import os, tempfile, asyncio
import pytest
from edge.db import init_db
from edge.engine.collector import Collector


class FakeAdapter:
    """Simulates a protocol adapter returning fixed values."""
    def __init__(self, points: dict[str, float]):
        self.points = points
        self.connected = False

    async def connect(self, binding: dict):
        self.connected = True

    async def read_point(self, point_id: str, binding: dict) -> float:
        return self.points.get(point_id, 0.0)

    async def disconnect(self):
        self.connected = False


@pytest.fixture
def db():
    path = os.path.join(tempfile.mkdtemp(), "test_collector.duckdb")
    return init_db(path)


@pytest.mark.asyncio
async def test_collector_poll_and_store(db):
    config = {
        "p1": {"protocol": "fake", "binding": {}, "poll_interval_ms": 100},
        "p2": {"protocol": "fake", "binding": {}, "poll_interval_ms": 100},
    }
    adapter = FakeAdapter({"p1": 23.5, "p2": 45.0})
    collector = Collector(db, config, {"fake": adapter})

    await collector.poll_once()

    rows = db.execute("SELECT point_id, value FROM readings ORDER BY point_id").fetchall()
    assert len(rows) == 2
    assert rows[0] == ("p1", 23.5)
    assert rows[1] == ("p2", 45.0)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd hvac-edge && python -m pytest tests/test_collector.py -v
```
Expected: FAIL (Collector not defined)

- [ ] **Step 3: Implement collector.py**

```python
import asyncio
import logging
from datetime import datetime, timezone

import duckdb

logger = logging.getLogger(__name__)


class Collector:
    """Polls hardware points via protocol adapters and writes readings to DuckDB."""

    def __init__(self, db: duckdb.DuckDBPyConnection, point_configs: dict, adapters: dict):
        self.db = db
        self.point_configs = point_configs
        self.adapters = adapters
        self._running = False
        self._task: asyncio.Task | None = None

    async def poll_once(self):
        now = datetime.now(timezone.utc).isoformat()
        for point_id, cfg in self.point_configs.items():
            adapter = self.adapters.get(cfg["protocol"])
            if not adapter:
                continue
            try:
                value = await adapter.read_point(point_id, cfg.get("binding", {}))
                self.db.execute(
                    "INSERT INTO readings (time, point_id, value, quality) VALUES (?, ?, ?, 'good')",
                    [now, point_id, value],
                )
            except Exception as e:
                logger.error(f"Failed to read {point_id}: {e}")
                self.db.execute(
                    "INSERT INTO readings (time, point_id, value, quality) VALUES (?, ?, ?, 'bad')",
                    [now, point_id, 0.0],
                )

    async def start(self, interval_ms: int = 1000):
        self._running = True
        self._task = asyncio.create_task(self._run_loop(interval_ms))

    async def _run_loop(self, interval_ms: int):
        while self._running:
            await self.poll_once()
            await asyncio.sleep(interval_ms / 1000.0)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd hvac-edge && python -m pytest tests/test_collector.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hvac-edge/
git commit -m "feat(p3): add hvac-edge collector engine with poll-and-store"
```

---

### Task 8: hvac-edge controller engine

**Files:**
- Create: `hvac-edge/edge/engine/controller.py`
- Create: `hvac-edge/tests/test_controller.py`

- [ ] **Step 1: Write failing controller test**

```python
# hvac-edge/tests/test_controller.py
import pytest
from edge.engine.controller import SafetyGate, PIDController, Interlock


class TestSafetyGate:
    def test_passes_valid_value(self):
        gate = SafetyGate(limits={"CH-1.cop": (3.0, 8.0)})
        assert gate.check("CH-1.cop", 5.5) is True

    def test_rejects_out_of_range(self):
        gate = SafetyGate(limits={"CH-1.cop": (3.0, 8.0)})
        assert gate.check("CH-1.cop", 1.0) is False

    def test_unknown_param_passes(self):
        gate = SafetyGate(limits={})
        assert gate.check("unknown.param", 999) is True


class TestPIDController:
    def test_pid_compute(self):
        pid = PIDController(kp=2.0, ki=0.1, kd=0.05, setpoint=7.0)
        output = pid.compute(6.0, dt=1.0)
        assert output > 0  # Below setpoint → positive output

    def test_pid_converges(self):
        pid = PIDController(kp=1.0, ki=0.1, kd=0.0, setpoint=5.0, output_min=-10, output_max=10)
        value = 0.0
        for _ in range(50):
            output = pid.compute(value, dt=1.0)
            value += output * 0.1
        assert abs(value - 5.0) < 0.5


class TestInterlock:
    def test_chiller_pump_interlock(self):
        il = Interlock(rules=[
            {"if": "CH-1.status == 'off'", "then": "P-1.cmd = 0"},
        ])
        actions = il.evaluate({"CH-1.status": "off", "P-1.cmd": 1})
        assert actions == ["P-1.cmd = 0"]

    def test_no_action_when_ok(self):
        il = Interlock(rules=[
            {"if": "CH-1.status == 'off'", "then": "P-1.cmd = 0"},
        ])
        actions = il.evaluate({"CH-1.status": "on", "P-1.cmd": 1})
        assert actions == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd hvac-edge && python -m pytest tests/test_controller.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement controller.py**

```python
import logging

logger = logging.getLogger(__name__)


class SafetyGate:
    """Rejects control outputs that violate hard limits."""

    def __init__(self, limits: dict[str, tuple[float, float]]):
        self.limits = limits

    def check(self, param: str, value: float) -> bool:
        if param not in self.limits:
            return True
        lo, hi = self.limits[param]
        return lo <= value <= hi


class PIDController:
    """Discrete PID controller."""

    def __init__(self, kp: float, ki: float = 0.0, kd: float = 0.0,
                 setpoint: float = 0.0, output_min: float = -1e6, output_max: float = 1e6):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, measurement: float, dt: float = 1.0) -> float:
        error = self.setpoint - measurement
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt if dt > 0 else 0.0
        self._prev_error = error

        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(self.output_min, min(self.output_max, output))

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0


class Interlock:
    """Device interlock engine — evaluates rules and returns enforcement actions."""

    def __init__(self, rules: list[dict]):
        self.rules = rules

    def evaluate(self, state: dict) -> list[str]:
        actions = []
        for rule in self.rules:
            condition = rule["if"]
            if self._eval_condition(condition, state):
                actions.append(rule["then"])
        return actions

    def _eval_condition(self, cond: str, state: dict) -> bool:
        # Simple parser: "CH-1.status == 'off'"
        parts = cond.split(" == ")
        if len(parts) != 2:
            return False
        key = parts[0].strip()
        expected = parts[1].strip().strip("'\"")
        return str(state.get(key)) == expected
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd hvac-edge && python -m pytest tests/test_controller.py -v
```
Expected: all 6 pass

- [ ] **Step 5: Commit**

```bash
git add hvac-edge/
git commit -m "feat(p3): add hvac-edge controller engine (SafetyGate + PID + Interlock)"
```

---

### Task 9: hvac-edge sync agent

**Files:**
- Create: `hvac-edge/edge/sync/__init__.py`
- Create: `hvac-edge/edge/sync/queue.py`
- Create: `hvac-edge/edge/sync/agent.py`
- Create: `hvac-edge/tests/test_sync.py`

- [ ] **Step 1: Write failing sync tests**

```python
# hvac-edge/tests/test_sync.py
import os, tempfile, json
import pytest
from edge.db import init_db
from edge.sync.queue import SyncQueue


@pytest.fixture
def db():
    path = os.path.join(tempfile.mkdtemp(), "test_sync.duckdb")
    return init_db(path)


class TestSyncQueue:
    def test_enqueue_and_dequeue(self, db):
        q = SyncQueue(db)
        q.enqueue("hvac/edge-1/alert", {"severity": "critical"}, qos=1)

        items = q.get_unsent()
        assert len(items) == 1
        assert items[0]["topic"] == "hvac/edge-1/alert"
        assert json.loads(items[0]["payload"]) == {"severity": "critical"}

    def test_mark_synced(self, db):
        q = SyncQueue(db)
        q.enqueue("hvac/edge-1/status", {"ok": True}, qos=1)
        items = q.get_unsent()
        q.mark_synced([items[0]["id"]])

        remaining = q.get_unsent()
        assert len(remaining) == 0

    def test_fifo_order(self, db):
        q = SyncQueue(db)
        q.enqueue("a/b/c", {"n": 1}, qos=1)
        q.enqueue("a/b/c", {"n": 2}, qos=1)
        q.enqueue("a/b/c", {"n": 3}, qos=1)

        items = q.get_unsent()
        payloads = [json.loads(i["payload"])["n"] for i in items]
        assert payloads == [1, 2, 3]

    def test_retry_count(self, db):
        q = SyncQueue(db)
        q.enqueue("a/b/c", {"x": 1}, qos=1)
        items = q.get_unsent()
        assert items[0]["retries"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd hvac-edge && python -m pytest tests/test_sync.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement queue.py**

```python
import json
from datetime import datetime, timezone

import duckdb


class SyncQueue:
    """DuckDB-backed persistent outbox for offline-tolerant MQTT publishing."""

    def __init__(self, db: duckdb.DuckDBPyConnection):
        self.db = db

    def enqueue(self, topic: str, payload: dict, qos: int = 1):
        now = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload)
        self.db.execute(
            "INSERT INTO sync_queue (id, created_at, topic, payload, qos, retries, synced) "
            "VALUES (nextval('seq_sync_queue_id'), ?, ?, ?, ?, 0, FALSE)",
            [now, topic, payload_str, qos],
        )

    def get_unsent(self, limit: int = 100) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, created_at, topic, payload, qos, retries "
            "FROM sync_queue WHERE synced = FALSE ORDER BY id ASC LIMIT ?",
            [limit],
        ).fetchall()
        return [
            {"id": r[0], "created_at": r[1], "topic": r[2], "payload": r[3], "qos": r[4], "retries": r[5]}
            for r in rows
        ]

    def mark_synced(self, ids: list[int]):
        if not ids:
            return
        placeholders = ",".join(["?"] * len(ids))
        self.db.execute(
            f"UPDATE sync_queue SET synced = TRUE WHERE id IN ({placeholders})", ids
        )
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd hvac-edge && python -m pytest tests/test_sync.py::TestSyncQueue -v
```
Expected: all 4 pass

- [ ] **Step 5: Implement agent.py**

```python
import asyncio
import json
import logging

import duckdb
import httpx

from .queue import SyncQueue

logger = logging.getLogger(__name__)


class SyncAgent:
    """Handles edge-to-cloud sync via MQTT (real-time) and HTTP (bulk)."""

    def __init__(self, db: duckdb.DuckDBPyConnection, config):
        self.db = db
        self.cfg = config
        self.queue = SyncQueue(db)
        self._http = httpx.AsyncClient(base_url=config.cloud_api_url, timeout=30.0)
        self._running = False
        self._task: asyncio.Task | None = None

    async def send_alert(self, severity: str, title: str, equipment_id: str = ""):
        """Queue an alert for MQTT delivery (or direct HTTP if MQTT unavailable)."""
        payload = {
            "edge_id": self.cfg.edge_id,
            "severity": severity,
            "title": title,
            "equipment_id": equipment_id,
        }
        topic = f"hvac/{self.cfg.edge_id}/alert"
        self.queue.enqueue(topic, payload, qos=1)

    async def flush_mqtt(self, publish_fn):
        """Replay queued messages through a publish callback."""
        items = self.queue.get_unsent()
        synced = []
        for item in items:
            try:
                payload = json.loads(item["payload"])
                await publish_fn(item["topic"], payload, item["qos"])
                synced.append(item["id"])
            except Exception as e:
                logger.warning(f"Failed to publish {item['id']}: {e}")
                self.db.execute(
                    "UPDATE sync_queue SET retries = retries + 1 WHERE id = ?", [item["id"]]
                )
        self.queue.mark_synced(synced)

    async def upload_readings(self):
        """Upload recent readings to cloud via HTTP bulk."""
        last_sent = self.db.execute(
            "SELECT last_sent_at FROM sync_meta WHERE table_name = 'readings'"
        ).fetchone()
        since = last_sent[0] if last_sent else "1970-01-01T00:00:00Z"

        # 15-min window aggregation
        agg_rows = self.db.execute("""
            SELECT
                time_bucket(INTERVAL '15 minutes', time) AS bucket,
                point_id,
                MIN(value) AS v_min,
                MAX(value) AS v_max,
                AVG(value) AS v_avg,
                STDDEV(value) AS v_std
            FROM readings
            WHERE time > ?
            GROUP BY bucket, point_id
            ORDER BY bucket
        """, [since]).fetchall()

        if not agg_rows:
            return

        readings = [
            {"time": r[0].isoformat(), "point_id": r[1],
             "min": r[2], "max": r[3], "avg": r[4], "std": r[5]}
            for r in agg_rows
        ]

        try:
            resp = await self._http.post(
                f"/api/edges/{self.cfg.edge_id}/data/ingest",
                json={"readings": readings, "inspections": [], "work_orders": []},
            )
            if resp.status_code == 200:
                latest = max(r["time"] for r in readings)
                self.db.execute(
                    "INSERT OR REPLACE INTO sync_meta (table_name, last_sent_at) VALUES ('readings', ?)",
                    [latest],
                )
        except Exception as e:
            logger.error(f"Upload failed: {e}")

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())

    async def _sync_loop(self):
        while self._running:
            try:
                await self.upload_readings()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            await asyncio.sleep(30)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        await self._http.aclose()
```

- [ ] **Step 6: Commit**

```bash
git add hvac-edge/
git commit -m "feat(p3): add hvac-edge sync agent with MQTT outbox and HTTP bulk upload"
```

---

### Task 10: hvac-edge main lifecycle integration

**Files:**
- Modify: `hvac-edge/edge/main.py`

- [ ] **Step 1: Update main.py with full lifecycle**

```python
import asyncio
import logging

from .config import load_config
from .db import init_db
from .engine.collector import Collector
from .engine.controller import SafetyGate, PIDController, Interlock
from .sync.agent import SyncAgent

logger = logging.getLogger(__name__)


async def main():
    cfg = load_config()
    logger.info(f"Starting hvac-edge {cfg.edge_id} in {cfg.mode} mode")

    db = init_db(cfg.db_path)
    logger.info(f"DuckDB initialized at {cfg.db_path}")

    # Build point configs from acquisition config
    point_configs = {}
    adapters = {}
    for proto_cfg in cfg.acquisition.protocols:
        proto_type = proto_cfg["type"]
        # Adapter loading is deferred — adapters imported lazily
        # For now, protocol configs are registered
        for pt in proto_cfg.get("points", []):
            point_configs[pt["point_id"]] = {
                "protocol": proto_type,
                "binding": pt.get("binding", {}),
                "poll_interval_ms": cfg.acquisition.poll_interval_ms,
            }

    # Init engines
    collector = Collector(db, point_configs, adapters)
    safety_gate = SafetyGate(limits={
        "CH-1.cop": (2.0, 10.0),
        "CH-1.evap_delta_t": (2.0, 12.0),
        "CH-1.cond_delta_t": (2.0, 15.0),
    })
    pid = PIDController(kp=2.0, ki=0.05, kd=0.0, setpoint=7.0, output_min=0, output_max=100)
    interlock = Interlock(rules=[
        {"if": "CH-1.status == 'off'", "then": "P-1.cmd = 0"},
        {"if": "CH-1.status == 'off'", "then": "CT-1.fan_cmd = 0"},
    ])
    sync_agent = SyncAgent(db, cfg)

    logger.info("Engines initialized, starting loops")

    # Start engines
    await collector.start(interval_ms=cfg.acquisition.poll_interval_ms)
    await sync_agent.start()

    try:
        while True:
            await asyncio.sleep(60)

            # Run inspection logic on latest readings
            result = db.execute(
                "SELECT point_id, AVG(value) FROM readings "
                "WHERE time > NOW() - INTERVAL '60 seconds' GROUP BY point_id"
            ).fetchall()
            latest = {r[0]: r[1] for r in result}

            # Check interlock conditions
            actions = interlock.evaluate(latest)
            for action in actions:
                logger.info(f"Interlock action: {action}")

            # Safety gate check on key params
            for param, value in latest.items():
                if not safety_gate.check(param, value):
                    await sync_agent.send_alert("critical", f"Safety gate violation: {param}={value}")

    except asyncio.CancelledError:
        logger.info("Shutting down hvac-edge")
    finally:
        await collector.stop()
        await sync_agent.stop()
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add hvac-edge/
git commit -m "feat(p3): integrate hvac-edge main lifecycle with all engines"
```

---

## Phase 3: Inspection + Work Order (P3-B)

### Task 11: hvac-edge inspector engine

**Files:**
- Create: `hvac-edge/edge/engine/inspector.py`
- Create: `hvac-edge/tests/test_inspector.py`

- [ ] **Step 1: Write failing inspector test**

```python
# hvac-edge/tests/test_inspector.py
import os, tempfile
import pytest
from datetime import datetime, timezone
from edge.db import init_db
from edge.engine.inspector import Inspector, InspectionPlan


@pytest.fixture
def db():
    path = os.path.join(tempfile.mkdtemp(), "test_inspector.duckdb")
    return init_db(path)


SAMPLE_PLAN = InspectionPlan(
    plan_id="test-plan",
    description="Test plan",
    interval_hours=1,
    items=[
        {"id": "chk-1", "equipment_type": "chiller", "check": "cop_degradation",
         "params": {"threshold_pct": 10}, "severity": "warning"},
        {"id": "chk-2", "equipment_type": "pump", "check": "vibration_rms",
         "params": {"max_rms": 7.0}, "severity": "critical"},
    ]
)


@pytest.mark.asyncio
async def test_inspector_runs_checks(db):
    # Seed some readings
    db.execute("INSERT INTO readings (time, point_id, value) VALUES ('2026-05-20T10:00:00Z', 'CH-1.cop', 4.5)")
    db.execute("INSERT INTO readings (time, point_id, value) VALUES ('2026-05-20T10:00:00Z', 'P-1.vibration_rms', 8.5)")

    inspector = Inspector(db, SAMPLE_PLAN)
    result = await inspector.run_inspection()

    assert result["plan_id"] == "test-plan"
    assert result["status"] in ("passed", "failed")
    # P-1 vibration is 8.5 > 7.0 max → should fail
    assert any("vibration" in str(item).lower() for item in result.get("failures", []))


@pytest.mark.asyncio
async def test_inspector_creates_work_order_on_critical(db):
    db.execute("INSERT INTO readings (time, point_id, value) VALUES ('2026-05-20T10:00:00Z', 'P-1.vibration_rms', 9.0)")

    inspector = Inspector(db, SAMPLE_PLAN)
    result = await inspector.run_inspection()

    # Should create a work order for critical vibration
    orders = db.execute("SELECT COUNT(*) FROM work_orders").fetchone()
    assert orders[0] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd hvac-edge && python -m pytest tests/test_inspector.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement inspector.py**

```python
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb

logger = logging.getLogger(__name__)


@dataclass
class InspectionPlan:
    plan_id: str
    description: str
    interval_hours: int
    items: list[dict]


class Inspector:
    """Runs inspection checklists against recent readings and generates work orders."""

    def __init__(self, db: duckdb.DuckDBPyConnection, plan: InspectionPlan):
        self.db = db
        self.plan = plan

    async def run_inspection(self) -> dict:
        now = datetime.now(timezone.utc)
        inspection_id = self.db.execute("SELECT nextval('seq_inspection_id')").fetchone()[0]

        self.db.execute(
            "INSERT INTO inspections (id, started_at, plan_id, status) VALUES (?, ?, ?, 'running')",
            [inspection_id, now.isoformat(), self.plan.plan_id],
        )

        failures = []
        for item in self.plan.items:
            check_result = self._run_check(item)
            if not check_result["passed"]:
                failures.append(check_result)
                if item["severity"] == "critical":
                    self._create_work_order(item, check_result)

        status = "failed" if failures else "passed"
        self.db.execute(
            "UPDATE inspections SET ended_at = ?, status = ?, result = ? WHERE id = ?",
            [datetime.now(timezone.utc).isoformat(), status, str({"failures": len(failures)}), inspection_id],
        )

        return {"inspection_id": inspection_id, "plan_id": self.plan.plan_id, "status": status, "failures": failures}

    def _run_check(self, item: dict) -> dict:
        check_type = item["check"]
        params = item.get("params", {})

        if check_type == "cop_degradation":
            return self._check_cop(item, params)
        elif check_type == "vibration_rms":
            return self._check_vibration(item, params)
        elif check_type == "approach_temp":
            return self._check_approach_temp(item, params)
        elif check_type == "stuck_detection":
            return self._check_stuck(item, params)
        else:
            return {"item_id": item["id"], "passed": True, "detail": "unknown check type — skipped"}

    def _check_cop(self, item: dict, params: dict) -> dict:
        threshold_pct = params.get("threshold_pct", 10)
        point_id = f"{item['equipment_type']}.cop" if "." not in item.get("id", "") else item["id"]

        rows = self.db.execute(
            "SELECT AVG(value) FROM readings WHERE point_id LIKE ? AND time > NOW() - INTERVAL '1 hour'",
            ["%cop%"],
        ).fetchone()
        current_cop = rows[0] if rows[0] else None

        if current_cop is None:
            return {"item_id": item["id"], "passed": True, "detail": "no data", "value": None}

        # Assume design COP = 5.5 for a typical chiller
        design_cop = 5.5
        degradation = (design_cop - current_cop) / design_cop * 100
        passed = degradation < threshold_pct

        return {
            "item_id": item["id"],
            "passed": passed,
            "detail": f"COP={current_cop:.2f}, degradation={degradation:.1f}%",
            "value": current_cop,
        }

    def _check_vibration(self, item: dict, params: dict) -> dict:
        max_rms = params.get("max_rms", 7.0)
        rows = self.db.execute(
            "SELECT AVG(value) FROM readings WHERE point_id LIKE ? AND time > NOW() - INTERVAL '1 hour'",
            ["%vibration%"],
        ).fetchone()
        current = rows[0] if rows[0] else None

        if current is None:
            return {"item_id": item["id"], "passed": True, "detail": "no data", "value": None}

        passed = current <= max_rms
        return {
            "item_id": item["id"],
            "passed": passed,
            "detail": f"Vibration={current:.2f} mm/s RMS (limit={max_rms})",
            "value": current,
        }

    def _check_approach_temp(self, item: dict, params: dict) -> dict:
        max_delta = params.get("max_delta_k", 5.0)
        rows = self.db.execute(
            "SELECT AVG(value) FROM readings WHERE point_id LIKE ? AND time > NOW() - INTERVAL '1 hour'",
            ["%approach%"],
        ).fetchone()
        current = rows[0] if rows[0] else None

        if current is None:
            return {"item_id": item["id"], "passed": True, "detail": "no data", "value": None}

        passed = current <= max_delta
        return {
            "item_id": item["id"],
            "passed": passed,
            "detail": f"Approach ΔT={current:.1f}K (limit={max_delta}K)",
            "value": current,
        }

    def _check_stuck(self, item: dict, params: dict) -> dict:
        min_change = params.get("min_position_change", 0.02)
        window_min = params.get("window_minutes", 30)

        rows = self.db.execute(
            "SELECT MIN(value), MAX(value) FROM readings WHERE point_id LIKE ? AND time > NOW() - INTERVAL '30 minutes'",
            ["%valve%position%"],
        ).fetchone()
        if rows[0] is None:
            return {"item_id": item["id"], "passed": True, "detail": "no data", "value": None}

        range_val = rows[1] - rows[0]
        passed = range_val > min_change
        return {
            "item_id": item["id"],
            "passed": passed,
            "detail": f"Position range={range_val:.3f} (min={min_change})",
            "value": range_val,
        }

    def _create_work_order(self, item: dict, check_result: dict):
        wo_id = self.db.execute("SELECT nextval('seq_work_order_id')").fetchone()[0]
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO work_orders (id, created_at, equipment_id, severity, title, description, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'open')",
            [
                wo_id, now,
                item.get("equipment_type", "unknown"),
                item["severity"],
                f"Inspection failed: {item['id']}",
                check_result.get("detail", ""),
            ],
        )
        logger.info(f"Auto-created work order {wo_id} for {item['id']}")
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd hvac-edge && python -m pytest tests/test_inspector.py -v
```
Expected: all 2 pass

- [ ] **Step 5: Commit**

```bash
git add hvac-edge/
git commit -m "feat(p3): add hvac-edge inspector engine with auto work order generation"
```

---

## Phase 4: Predictive Maintenance + Work Order Cloud (P3-C)

### Task 12: Predictive maintenance — degradation tracker

**Files:**
- Create: `services/agent/agent_service/predictive_maintenance/__init__.py`
- Create: `services/agent/agent_service/predictive_maintenance/models.py`
- Create: `services/agent/agent_service/predictive_maintenance/degradation_tracker.py`
- Create: `services/agent/tests/test_degradation_tracker.py`

- [ ] **Step 1: Write models.py**

```python
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from common.db import Base


class DegradationResult(Base):
    __tablename__ = "degradation_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    equipment_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    severity: Mapped[str] = mapped_column(String(16), default="normal")
    cop_degradation_pct: Mapped[Optional[float]] = mapped_column(Float)
    approach_temp_drift_k: Mapped[Optional[float]] = mapped_column(Float)
    vibration_trend: Mapped[Optional[float]] = mapped_column(Float)
    cusum_triggered: Mapped[bool] = mapped_column(default=False)
    recommended_action: Mapped[Optional[str]] = mapped_column(String(256))
    detail: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
```

- [ ] **Step 2: Write failing degradation test**

```python
# services/agent/tests/test_degradation_tracker.py
import pytest
from agent_service.predictive_maintenance.degradation_tracker import (
    DegradationTracker, cop_degradation, cusum_detect
)


def test_cop_degradation_normal():
    # Design COP = 5.5, current window avg = 5.3
    degradation = cop_degradation(design_cop=5.5, window_values=[5.2, 5.3, 5.4, 5.3, 5.35])
    assert 2 < degradation < 5  # roughly 3.6%


def test_cop_degradation_severe():
    degradation = cop_degradation(design_cop=5.5, window_values=[3.8, 3.9, 3.7, 3.85, 3.9])
    assert degradation > 25  # roughly 29%


def test_cusum_no_change():
    values = [5.0, 5.1, 4.9, 5.0, 5.1, 4.9, 5.0, 5.1]
    triggered, change_point = cusum_detect(values, threshold=1.0)
    assert not triggered


def test_cusum_detects_shift():
    values = [5.0, 5.1, 4.9, 5.0, 4.0, 3.9, 3.8, 3.7, 3.6, 3.5]
    triggered, change_point = cusum_detect(values, threshold=1.0)
    assert triggered
    assert change_point is not None


def test_degradation_tracker_evaluate():
    tracker = DegradationTracker(equipment_id="CH-1", equipment_type="chiller")
    # Simulate degraded readings
    report = tracker.evaluate(design_cop=5.5, cop_window=[3.8, 3.9, 3.7, 3.85, 3.9],
                              approach_temp_avg=4.5, vibration_window=[1.2, 1.3, 1.1])
    assert report["severity"] in ("normal", "degrading", "critical")
    assert report["cop_degradation_pct"] > 25
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd services/agent && python -m pytest tests/test_degradation_tracker.py -v
```
Expected: FAIL

- [ ] **Step 4: Implement degradation_tracker.py**

```python
from typing import Optional


def cop_degradation(design_cop: float, window_values: list[float]) -> float:
    if not window_values:
        return 0.0
    current_avg = sum(window_values) / len(window_values)
    return (design_cop - current_avg) / design_cop * 100


def cusum_detect(values: list[float], threshold: float = 1.0) -> tuple[bool, Optional[int]]:
    """CUSUM change-point detection. Returns (triggered, change_point_index)."""
    if len(values) < 4:
        return False, None

    mean = sum(values) / len(values)
    cusum_pos = 0.0
    cusum_neg = 0.0
    change_point = None

    for i, v in enumerate(values):
        cusum_pos = max(0, cusum_pos + (v - mean) - 0.5 * threshold)
        cusum_neg = max(0, cusum_neg + (mean - v) - 0.5 * threshold)
        if cusum_pos > threshold or cusum_neg > threshold:
            change_point = i
            break

    triggered = change_point is not None
    return triggered, change_point


class DegradationTracker:
    def __init__(self, equipment_id: str, equipment_type: str):
        self.equipment_id = equipment_id
        self.equipment_type = equipment_type

    def evaluate(self, design_cop: float, cop_window: list[float],
                 approach_temp_avg: float, vibration_window: list[float]) -> dict:
        cop_drift = cop_degradation(design_cop, cop_window)
        cusum_triggered, _ = cusum_detect(cop_window, threshold=1.0)

        severity = "normal"
        if cop_drift > 15 or approach_temp_avg > 5.0:
            severity = "critical"
        elif cop_drift > 7 or approach_temp_avg > 3.0:
            severity = "degrading"

        recommendation = None
        if severity == "critical":
            recommendation = f"Schedule immediate maintenance for {self.equipment_id}"
        elif severity == "degrading":
            recommendation = f"Plan maintenance for {self.equipment_id} within next 2 weeks"

        return {
            "equipment_id": self.equipment_id,
            "equipment_type": self.equipment_type,
            "severity": severity,
            "cop_degradation_pct": round(cop_drift, 1),
            "approach_temp_drift_k": round(approach_temp_avg, 1),
            "vibration_trend": sum(vibration_window) / len(vibration_window) if vibration_window else 0,
            "cusum_triggered": cusum_triggered,
            "recommended_action": recommendation,
        }
```

- [ ] **Step 5: Run test to verify pass**

```bash
cd services/agent && python -m pytest tests/test_degradation_tracker.py -v
```
Expected: all 5 pass

- [ ] **Step 6: Commit**

```bash
git add services/agent/agent_service/predictive_maintenance/ services/agent/tests/
git commit -m "feat(p3): add degradation tracker with CUSUM detection"
```

---

### Task 13: Predictive maintenance — failure predictor + ONNX export

**Files:**
- Create: `services/agent/agent_service/predictive_maintenance/failure_predictor.py`
- Create: `services/agent/tests/test_failure_predictor.py`

- [ ] **Step 1: Write failing predictor test**

```python
# services/agent/tests/test_failure_predictor.py
import numpy as np
import pytest
from agent_service.predictive_maintenance.failure_predictor import (
    FailurePredictor, build_training_data, export_onnx
)


def test_build_training_data():
    features, labels = build_training_data()
    assert len(features) > 0
    assert len(features) == len(labels)
    assert all(isinstance(f, list) for f in features)
    assert all(isinstance(l, int) for l in labels)


def test_train_predictor():
    X, y = build_training_data()
    predictor = FailurePredictor()
    predictor.train(X, y)
    assert predictor.model is not None

    # Predict on a sample
    sample = [3.5, 8.0, 2.1]  # cop, vibration, approach_temp
    proba = predictor.predict_proba(sample)
    assert 0 <= proba <= 1


def test_export_onnx_roundtrip(tmp_path):
    X, y = build_training_data()
    predictor = FailurePredictor()
    predictor.train(X, y)

    model_path = tmp_path / "test_model.onnx"
    export_onnx(predictor.model, str(model_path), n_features=len(X[0]))
    assert model_path.exists()
    assert model_path.stat().st_size > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/agent && python -m pytest tests/test_failure_predictor.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement failure_predictor.py**

```python
import logging
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)


def build_training_data() -> tuple[list[list[float]], list[int]]:
    """Generate synthetic training data for initial model.
    In production, this is replaced by real labeled data from work order feedback loop.
    """
    np.random.seed(42)
    n_samples = 200

    features = []
    labels = []

    for _ in range(n_samples):
        cop = np.random.normal(5.5, 1.2)
        vibration = np.random.normal(3.0, 2.5)
        approach_temp = np.random.normal(3.0, 2.0)

        # Label: failure if cop < 3.0 or vibration > 7.0 or approach_temp > 5.0
        is_failure = int(cop < 3.0 or vibration > 7.0 or approach_temp > 5.0)
        features.append([cop, vibration, approach_temp])
        labels.append(is_failure)

    return features, labels


class FailurePredictor:
    def __init__(self):
        self.model = None
        self.feature_names = ["cop", "vibration_rms", "approach_temp"]

    def train(self, X: list[list[float]], y: list[int]):
        self.model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
        self.model.fit(X, y)
        logger.info(f"Trained FailurePredictor on {len(X)} samples, "
                     f"classes: {dict(zip(*np.unique(y, return_counts=True)))}")

    def predict_proba(self, features: list[float]) -> float:
        if self.model is None:
            return 0.0
        return float(self.model.predict_proba([features])[0][1])

    def predict(self, features: list[float]) -> int:
        if self.model is None:
            return 0
        return int(self.model.predict([features])[0])


def export_onnx(model, path: str, n_features: int = 3):
    """Export a trained sklearn model to ONNX format."""
    try:
        from skl2onnx import to_onnx
        from skl2onnx.common.data_types import FloatTensorType

        initial_type = [("float_input", FloatTensorType([None, n_features]))]
        onx = to_onnx(model, initial_types=initial_type, target_opset=12)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(onx.SerializeToString())
        logger.info(f"Exported ONNX model to {path}")
    except ImportError:
        logger.warning("skl2onnx not installed, skipping ONNX export")
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd services/agent && python -m pytest tests/test_failure_predictor.py -v
```
Expected: all 3 pass

- [ ] **Step 5: Commit**

```bash
git add services/agent/agent_service/predictive_maintenance/ services/agent/tests/
git commit -m "feat(p3): add failure predictor with sklearn training and ONNX export"
```

---

### Task 14: Predictive maintenance API + Agent Service wiring

**Files:**
- Create: `services/agent/agent_service/predictive_maintenance/api/__init__.py`
- Create: `services/agent/agent_service/predictive_maintenance/api/maintenance.py`
- Create: `services/agent/tests/test_maintenance_api.py`

- [ ] **Step 1: Write failing API test**

```python
# services/agent/tests/test_maintenance_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from agent_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_evaluate_degradation(client):
    payload = {
        "edge_id": "edge-001",
        "equipment_id": "CH-1",
        "equipment_type": "chiller",
        "design_cop": 5.5,
        "cop_window": [3.8, 3.9, 3.7, 3.85, 3.9],
        "approach_temp_avg": 2.5,
        "vibration_window": [1.2, 1.3, 1.1],
    }
    resp = await client.post("/api/maintenance/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "severity" in data
    assert data["cop_degradation_pct"] > 20


@pytest.mark.asyncio
async def test_predict_failure(client):
    payload = {
        "cop_current": 3.2,
        "vibration_rms": 8.5,
        "approach_temp": 6.0,
    }
    resp = await client.post("/api/maintenance/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "failure_probability" in data
    assert data["failure_probability"] > 0.5  # clearly failing features
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/agent && python -m pytest tests/test_maintenance_api.py -v
```
Expected: FAIL (routes not registered)

- [ ] **Step 3: Implement maintenance.py**

```python
from fastapi import APIRouter
from pydantic import BaseModel

from ..degradation_tracker import DegradationTracker
from ..failure_predictor import FailurePredictor, build_training_data

router = APIRouter()

# Lazy-init predictor, train on first use
_predictor: FailurePredictor | None = None


def _get_predictor() -> FailurePredictor:
    global _predictor
    if _predictor is None:
        _predictor = FailurePredictor()
        X, y = build_training_data()
        _predictor.train(X, y)
    return _predictor


class DegradationRequest(BaseModel):
    edge_id: str
    equipment_id: str
    equipment_type: str
    design_cop: float = 5.5
    cop_window: list[float]
    approach_temp_avg: float = 0.0
    vibration_window: list[float] = []


class PredictRequest(BaseModel):
    cop_current: float
    vibration_rms: float
    approach_temp: float


@router.post("/evaluate")
async def evaluate_degradation(body: DegradationRequest):
    tracker = DegradationTracker(body.equipment_id, body.equipment_type)
    result = tracker.evaluate(
        design_cop=body.design_cop,
        cop_window=body.cop_window,
        approach_temp_avg=body.approach_temp_avg,
        vibration_window=body.vibration_window,
    )
    result["edge_id"] = body.edge_id
    return result


@router.post("/predict")
async def predict_failure(body: PredictRequest):
    p = _get_predictor()
    proba = p.predict_proba([body.cop_current, body.vibration_rms, body.approach_temp])
    return {
        "failure_probability": round(proba, 4),
        "features": {
            "cop_current": body.cop_current,
            "vibration_rms": body.vibration_rms,
            "approach_temp": body.approach_temp,
        },
    }
```

- [ ] **Step 4: Register router in Agent Service main.py**

In `services/agent/agent_service/main.py`, add after existing router registrations:

```python
from .predictive_maintenance.api.maintenance import router as maintenance_router
app.include_router(maintenance_router, prefix="/api/maintenance", tags=["Maintenance"])
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd services/agent && python -m pytest tests/test_maintenance_api.py -v
```
Expected: all 2 pass

- [ ] **Step 6: Commit**

```bash
git add services/agent/
git commit -m "feat(p3): add predictive maintenance REST API with degradation evaluation and failure prediction"
```

---

### Task 15: Work order system — models + state machine

**Files:**
- Create: `services/agent/agent_service/workorder/__init__.py`
- Create: `services/agent/agent_service/workorder/models.py`
- Create: `services/agent/agent_service/workorder/lifecycle.py`
- Create: `services/agent/tests/test_workorder.py`

- [ ] **Step 1: Write models.py**

```python
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from common.db import Base


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    edge_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    equipment_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open")
    assigned_to: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(32), default="auto")


class WorkOrderLog(Base):
    __tablename__ = "work_order_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(Integer, ForeignKey("work_orders.id"), nullable=False)
    from_status: Mapped[str] = mapped_column(String(16), nullable=False)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(64), default="system")
    note: Mapped[Optional[str]] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: Write lifecycle.py**

```python
VALID_TRANSITIONS = {
    "open": ["acknowledged", "rejected"],
    "acknowledged": ["in_progress", "rejected"],
    "in_progress": ["resolved"],
    "resolved": ["closed", "in_progress"],
    "closed": [],
    "rejected": [],
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, [])


def transition(work_order, to_status: str, changed_by: str = "system", note: str = None) -> dict:
    if not can_transition(work_order.status, to_status):
        raise ValueError(f"Cannot transition from {work_order.status} to {to_status}")

    from_status = work_order.status
    work_order.status = to_status

    if to_status == "resolved":
        from datetime import datetime, timezone
        work_order.resolved_at = datetime.now(timezone.utc)

    return {
        "work_order_id": work_order.id,
        "from_status": from_status,
        "to_status": to_status,
        "changed_by": changed_by,
        "note": note,
    }
```

- [ ] **Step 3: Write failing work order tests**

```python
# services/agent/tests/test_workorder.py
import pytest
from agent_service.workorder.lifecycle import can_transition, transition


class FakeWorkOrder:
    id = 1
    status = "open"
    resolved_at = None


def test_valid_transitions():
    assert can_transition("open", "acknowledged") is True
    assert can_transition("open", "rejected") is True
    assert can_transition("acknowledged", "in_progress") is True
    assert can_transition("in_progress", "resolved") is True
    assert can_transition("resolved", "closed") is True
    assert can_transition("resolved", "in_progress") is True  # reopen


def test_invalid_transitions():
    assert can_transition("open", "resolved") is False
    assert can_transition("closed", "in_progress") is False
    assert can_transition("rejected", "acknowledged") is False


def test_transition_mutates_status():
    wo = FakeWorkOrder()
    result = transition(wo, "acknowledged")
    assert wo.status == "acknowledged"
    assert result["from_status"] == "open"
    assert result["to_status"] == "acknowledged"


def test_transition_invalid_raises():
    wo = FakeWorkOrder()
    with pytest.raises(ValueError, match="Cannot transition"):
        transition(wo, "resolved")
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd services/agent && python -m pytest tests/test_workorder.py -v
```
Expected: all 4 pass (models and lifecycle are pure logic, no DB needed)

- [ ] **Step 5: Commit**

```bash
git add services/agent/agent_service/workorder/ services/agent/tests/test_workorder.py
git commit -m "feat(p3): add work order models and state machine (open→acknowledged→in_progress→resolved→closed)"
```

---

### Task 16: Work order API

**Files:**
- Create: `services/agent/agent_service/workorder/api/__init__.py`
- Create: `services/agent/agent_service/workorder/api/workorders.py`
- Create: `services/agent/tests/test_workorder_api.py`

- [ ] **Step 1: Write failing API test**

```python
# services/agent/tests/test_workorder_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from agent_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_work_order(client):
    payload = {
        "edge_id": "edge-001",
        "equipment_id": "CH-1",
        "severity": "critical",
        "title": "COP degradation detected",
        "description": "COP dropped from 5.5 to 3.8",
    }
    resp = await client.post("/api/workorders/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "open"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_work_orders(client):
    resp = await client.get("/api/workorders/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_transition_work_order(client):
    # Create
    create_resp = await client.post("/api/workorders/", json={
        "edge_id": "edge-001",
        "equipment_id": "P-1",
        "severity": "warning",
        "title": "Test order",
    })
    wo_id = create_resp.json()["id"]

    # Transition
    resp = await client.post(f"/api/workorders/{wo_id}/transition", json={
        "to_status": "acknowledged",
        "changed_by": "operator-1",
        "note": "Acknowledged, will inspect",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "acknowledged"


@pytest.mark.asyncio
async def test_invalid_transition_rejected(client):
    create_resp = await client.post("/api/workorders/", json={
        "edge_id": "edge-001",
        "equipment_id": "P-1",
        "severity": "warning",
        "title": "Test order",
    })
    wo_id = create_resp.json()["id"]

    resp = await client.post(f"/api/workorders/{wo_id}/transition", json={
        "to_status": "resolved",
    })
    assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/agent && python -m pytest tests/test_workorder_api.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement workorders.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkOrder, WorkOrderLog
from ..lifecycle import transition as do_transition

router = APIRouter()


class CreateWorkOrderRequest(BaseModel):
    edge_id: str
    equipment_id: str
    severity: str
    title: str
    description: str | None = None
    source: str = "auto"


class TransitionRequest(BaseModel):
    to_status: str
    changed_by: str = "system"
    note: str | None = None


async def get_db(request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


@router.post("/", status_code=201)
async def create_work_order(body: CreateWorkOrderRequest, session: AsyncSession = Depends(get_db)):
    wo = WorkOrder(
        edge_id=body.edge_id,
        equipment_id=body.equipment_id,
        severity=body.severity,
        title=body.title,
        description=body.description,
        source=body.source,
    )
    session.add(wo)
    await session.commit()
    await session.refresh(wo)
    return _to_dict(wo)


@router.get("/")
async def list_work_orders(status: str | None = None, edge_id: str | None = None,
                           session: AsyncSession = Depends(get_db)):
    q = select(WorkOrder).order_by(WorkOrder.created_at.desc())
    if status:
        q = q.where(WorkOrder.status == status)
    if edge_id:
        q = q.where(WorkOrder.edge_id == edge_id)
    result = await session.execute(q)
    return [_to_dict(wo) for wo in result.scalars().all()]


@router.get("/{wo_id}")
async def get_work_order(wo_id: int, session: AsyncSession = Depends(get_db)):
    wo = await session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return _to_dict(wo)


@router.post("/{wo_id}/transition")
async def transition_work_order(wo_id: int, body: TransitionRequest, session: AsyncSession = Depends(get_db)):
    wo = await session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    try:
        log_data = do_transition(wo, body.to_status, body.changed_by, body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    log = WorkOrderLog(
        work_order_id=wo_id,
        from_status=log_data["from_status"],
        to_status=log_data["to_status"],
        changed_by=log_data["changed_by"],
        note=log_data["note"],
    )
    session.add(log)
    await session.commit()
    await session.refresh(wo)
    return _to_dict(wo)


def _to_dict(wo: WorkOrder) -> dict:
    return {
        "id": wo.id,
        "edge_id": wo.edge_id,
        "equipment_id": wo.equipment_id,
        "severity": wo.severity,
        "title": wo.title,
        "description": wo.description,
        "status": wo.status,
        "assigned_to": wo.assigned_to,
        "source": wo.source,
        "created_at": wo.created_at.isoformat() if wo.created_at else None,
        "updated_at": wo.updated_at.isoformat() if wo.updated_at else None,
        "resolved_at": wo.resolved_at.isoformat() if wo.resolved_at else None,
    }
```

- [ ] **Step 4: Register router in Agent Service main.py**

```python
from .workorder.api.workorders import router as workorder_router
app.include_router(workorder_router, prefix="/api/workorders", tags=["WorkOrders"])
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd services/agent && python -m pytest tests/test_workorder_api.py -v
```
Expected: all 4 pass

- [ ] **Step 6: Commit**

```bash
git add services/agent/
git commit -m "feat(p3): add work order REST API with CRUD and state transitions"
```

---

## Phase 5: Edge ONNX Runtime (P3-C)

### Task 17: hvac-edge ML runtime

**Files:**
- Create: `hvac-edge/edge/ml/__init__.py`
- Create: `hvac-edge/edge/ml/runtime.py`
- Create: `hvac-edge/tests/test_ml_runtime.py`

- [ ] **Step 1: Write failing ML runtime test**

```python
# hvac-edge/tests/test_ml_runtime.py
import pytest
import numpy as np
from edge.ml.runtime import ONNXInferenceRuntime

# Skip if onnxruntime not installed
pytestmark = pytest.mark.skipif(
    __import__("importlib.util").util.find_spec("onnxruntime") is None,
    reason="onnxruntime not installed"
)


@pytest.fixture
def mock_model(tmp_path):
    """Create a simple sklearn model, export to ONNX, return path."""
    from sklearn.ensemble import RandomForestClassifier
    import numpy as np

    X = np.random.randn(100, 3)
    y = (X[:, 0] + X[:, 1] - X[:, 2] > 0).astype(int)
    model = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
    model.fit(X, y)

    try:
        from skl2onnx import to_onnx
        from skl2onnx.common.data_types import FloatTensorType

        onx = to_onnx(model, initial_types=[("float_input", FloatTensorType([None, 3]))],
                      target_opset=12)
        path = tmp_path / "test_model.onnx"
        with open(path, "wb") as f:
            f.write(onx.SerializeToString())
        return str(path)
    except ImportError:
        pytest.skip("skl2onnx not installed")


def test_runtime_load_and_infer(mock_model):
    rt = ONNXInferenceRuntime(mock_model)
    assert rt.is_loaded

    score = rt.predict([5.0, 3.0, 1.0])
    assert 0 <= score <= 1


def test_runtime_unloaded_model():
    rt = ONNXInferenceRuntime("/nonexistent/model.onnx")
    assert not rt.is_loaded
    assert rt.predict([1.0, 2.0, 3.0]) == 0.0
```

- [ ] **Step 2: Run test (expected skip if onnxruntime missing, or FAIL if not defined)**

```bash
cd hvac-edge && python -m pytest tests/test_ml_runtime.py -v
```

- [ ] **Step 3: Implement runtime.py**

```python
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class ONNXInferenceRuntime:
    """Loads an ONNX model and provides predict() for edge inference."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._session = None
        self._input_name = None
        self._load_model()

    def _load_model(self):
        if not Path(self.model_path).exists():
            logger.warning(f"ONNX model not found at {self.model_path}")
            return

        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(self.model_path)
            self._input_name = self._session.get_inputs()[0].name
            logger.info(f"Loaded ONNX model from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            self._session = None

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    def predict(self, features: list[float]) -> float:
        """Run inference, returns probability score [0, 1]."""
        if not self._session:
            return 0.0

        try:
            arr = np.array([features], dtype=np.float32)
            result = self._session.run(None, {self._input_name: arr})
            return float(result[0][0][1]) if result[0].shape[1] > 1 else float(result[0][0][0])
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return 0.0
```

- [ ] **Step 4: Run test to verify pass**

```bash
cd hvac-edge && python -m pytest tests/test_ml_runtime.py -v
```

- [ ] **Step 5: Commit**

```bash
git add hvac-edge/edge/ml/ hvac-edge/tests/test_ml_runtime.py
git commit -m "feat(p3): add hvac-edge ONNX inference runtime"
```

---

## Phase 6: Bare-Metal Deployment (P3-A)

### Task 18: Bare-metal systemd deployment + edge_config.yaml

**Files:**
- Create: `hvac-edge/deploy/systemd/hvac-edge.service`
- Create: `hvac-edge/deploy/edge_config.yaml`
- Create: `hvac-edge/deploy/install.sh`

- [ ] **Step 1: Create systemd service unit**

```ini
# hvac-edge/deploy/systemd/hvac-edge.service
[Unit]
Description=HVAC Edge Controller
After=network.target
Wants=network.target

[Service]
Type=simple
User=hvac
WorkingDirectory=/opt/hvac-edge
ExecStart=/opt/hvac-edge/.venv/bin/python -m edge.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=EDGE_CONFIG_PATH=/etc/hvac-edge/edge_config.yaml

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Create default edge config**

```yaml
# hvac-edge/deploy/edge_config.yaml
edge_id: "edge-default"
plant_id: "plant-default"
mode: hybrid
cloud_api_url: "http://192.168.1.100:8006"
mqtt_broker_host: "192.168.1.100"
mqtt_broker_port: 1883
db_path: "/var/lib/hvac-edge/edge_data.duckdb"

acquisition:
  poll_interval_ms: 1000
  protocols:
    - type: modbus
      port: /dev/ttyUSB0
      baudrate: 19200
      points: []

control:
  safety_gate: true
  pid_enabled: true
  interlock_enabled: true

inspection:
  plans_dir: "/etc/hvac-edge/plans"
  default_interval_hours: 4

ml:
  onnx_model_path: "/etc/hvac-edge/models/anomaly_v1.onnx"
  feature_window_hours: 24
```

- [ ] **Step 3: Create install script**

```bash
#!/bin/bash
# hvac-edge/deploy/install.sh
set -e

INSTALL_DIR="/opt/hvac-edge"
CONFIG_DIR="/etc/hvac-edge"
DATA_DIR="/var/lib/hvac-edge"

echo "Installing hvac-edge..."

# Create user
id -u hvac &>/dev/null || useradd -r -s /bin/false hvac

# Create directories
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR/plans" "$CONFIG_DIR/models" "$DATA_DIR"

# Copy files
cp -r edge/ "$INSTALL_DIR/edge/"
cp pyproject.toml "$INSTALL_DIR/"

# Python venv
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"

# Config
cp deploy/edge_config.yaml "$CONFIG_DIR/edge_config.yaml"
chown -R hvac:hvac "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR"

# Systemd
cp deploy/systemd/hvac-edge.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hvac-edge

echo "Installation complete. Start with: systemctl start hvac-edge"
```

- [ ] **Step 4: Commit**

```bash
git add hvac-edge/deploy/
git commit -m "feat(p3): add bare-metal systemd deployment with install script"
```

---

## Phase 7: Dependencies & Final Integration

### Task 19: Add new dependencies to workspace

**Files:**
- Modify: `pyproject.toml` (root workspace)
- Modify: `services/agent/pyproject.toml`
- Create: `hvac-edge/deploy/requirements-bare.txt`

- [ ] **Step 1: Update Agent Service dependencies for predictive maintenance**

In `services/agent/pyproject.toml`, add:

```toml
dependencies = [
    ...
    "scikit-learn>=1.4",
    "skl2onnx>=1.16",
    "numpy>=1.26",
]
```

- [ ] **Step 2: Create bare-metal requirements**

```txt
# hvac-edge/deploy/requirements-bare.txt
duckdb>=1.1
pydantic>=2.0
pyyaml>=6.0
aiomqtt>=2.0
httpx>=0.28
pymodbus>=3.7
BAC0>=23.0
asyncua>=1.0
```

- [ ] **Step 3: Verify Edge Manager deps**

In `services/edgemanager/pyproject.toml`, confirm `aiomqtt>=2.0` is present (already added in Task 1).

- [ ] **Step 4: Install and verify**

```bash
uv sync
cd services/edgemanager && uv sync
cd services/agent && uv sync
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml services/agent/pyproject.toml services/edgemanager/pyproject.toml hvac-edge/deploy/requirements-bare.txt
git commit -m "feat(p3): add scikit-learn, skl2onnx, aiomqtt dependencies for P3 modules"
```

---

### Task 20: Final integration — run all tests

- [ ] **Step 1: Run Edge Manager tests**

```bash
cd services/edgemanager && python -m pytest tests/ -v
```
Expected: all pass

- [ ] **Step 2: Run hvac-edge tests**

```bash
cd hvac-edge && python -m pytest tests/ -v
```
Expected: all pass

- [ ] **Step 3: Run Agent Service predictive maintenance tests**

```bash
cd services/agent && python -m pytest tests/test_degradation_tracker.py tests/test_failure_predictor.py tests/test_maintenance_api.py tests/test_workorder.py tests/test_workorder_api.py -v
```
Expected: all pass

- [ ] **Step 4: Run existing test suites to verify no regressions**

```bash
cd services/agent && python -m pytest tests/ -v --ignore=tests/test_degradation_tracker.py --ignore=tests/test_failure_predictor.py --ignore=tests/test_maintenance_api.py --ignore=tests/test_workorder.py --ignore=tests/test_workorder_api.py -x
```

- [ ] **Step 5: Commit any fixes**

```bash
git add -A && git diff --cached --stat
# Only commit if regression fixes needed
```

---

## Summary of All Tasks

| # | Phase | Task | Files |
|---|-------|------|-------|
| 1 | P3-A | Edge Manager scaffold | 7 new |
| 2 | P3-A | Registry & heartbeat API | 4 new |
| 3 | P3-A | Config & OTA API | 4 new |
| 4 | P3-A | Data ingest & MQTT client | 3 new |
| 5 | P3-A | Docker Compose + Mosquitto | 2 modify, 1 new |
| 6 | P3-A | hvac-edge scaffold + config + DB | 8 new |
| 7 | P3-A | Collector engine | 3 new |
| 8 | P3-A | Controller engine | 2 new |
| 9 | P3-A | Sync agent | 3 new |
| 10 | P3-A | Main lifecycle integration | 1 modify |
| 11 | P3-B | Inspector engine | 2 new |
| 12 | P3-C | Degradation tracker | 3 new |
| 13 | P3-C | Failure predictor + ONNX export | 2 new |
| 14 | P3-C | Maintenance API + wiring | 3 new, 1 modify |
| 15 | P3-B | Work order models + state machine | 3 new |
| 16 | P3-B | Work order API | 3 new, 1 modify |
| 17 | P3-C | Edge ML runtime | 3 new |
| 18 | P3-A | Bare-metal deployment | 3 new |
| 19 | — | Dependencies | 3 modify, 1 new |
| 20 | — | Integration test run | — |

**Total: 55+ new files, ~7 modified files**
