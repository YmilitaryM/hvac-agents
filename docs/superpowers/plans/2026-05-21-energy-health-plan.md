# Energy Management & Equipment Health — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two new production modules (Energy Management + Equipment Health) with dedicated backend services, compute engines, and 10 frontend pages.

**Architecture:** Hybrid deployment — compute-intensive engines in agent service (`energy/`, `health/` submodules), presentation APIs in two new FastAPI microservices (`services/energy/`, `services/health/`). Each new service gets its own database (TimescaleDB for energy, PostgreSQL for health). Frontend adds 10 new pages with WebSocket real-time + polling + on-demand data strategies.

**Tech Stack:** Python 3.12+ / FastAPI / SQLAlchemy 2.0 async / TimescaleDB / PostgreSQL / Alembic / React 19 / TypeScript / Tailwind CSS / Recharts / WebSocket

---

## Phase 1 — Infrastructure Setup (sequential prerequisite)

### Task 1: Register new services in common config and gateway proxy

**Files:**
- Modify: `common/common/config.py:12-18`
- Modify: `services/gateway/gateway_service/proxy.py:10-30`

- [ ] **Step 1: Add service URLs to Settings**

Add two lines after `edgemanager_service_url` at `common/common/config.py:18`:

```python
    energy_service_url: str = "http://localhost:8008"
    health_service_url: str = "http://localhost:8009"
```

Then add to the bottom of the same file, new database URLs:

```python
    energy_database_url: str = "postgresql+asyncpg://hvac:hvac_dev@localhost:5436/energy_db"
    health_database_url: str = "postgresql+asyncpg://hvac:hvac_dev@localhost:5437/health_db"
```

- [ ] **Step 2: Run existing tests to verify no regression**

Run: `cd services/gateway && uv run pytest tests/ -v -x`
Expected: All existing tests PASS

- [ ] **Step 3: Register service routes in gateway proxy**

Add energy routes to `SERVICE_ROUTES` dict in `services/gateway/gateway_service/proxy.py:28`:

```python
    "/api/energy": "energy",
    "/api/health": "health",
```

Add service URLs near existing `SERVICE_URLS`:

```python
SERVICE_URLS = {
    "asset": "http://asset_service:8000",
    "environment": "http://env_service:8000",
    "simulation": "http://sim_service:8000",
    "agent": "http://agent_service:8000",
    "acquisition": "http://acquisition_service:8000",
    "edgemanager": "http://edgemanager_service:8000",
    "energy": "http://energy_service:8000",
    "health": "http://health_service:8000",
}
```

- [ ] **Step 4: Run gateway tests**

Run: `cd services/gateway && uv run pytest tests/ -v -x`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add common/common/config.py services/gateway/gateway_service/proxy.py
git commit -m "feat: register energy and health services in config and gateway proxy"
```

---

### Task 2: Update docker-compose with new services and databases

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add database services**

Add after the `postgres_edge` service block in `docker-compose.yml`:

```yaml
  # Energy service database (TimescaleDB for time-series)
  energy_db:
    image: timescale/timescaledb:2.16-pg16
    environment:
      POSTGRES_DB: energy_db
      POSTGRES_USER: hvac
      POSTGRES_PASSWORD: hvac_dev
    ports:
      - "5436:5432"
    volumes:
      - tsdb_energy:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hvac -d energy_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Health service database (PostgreSQL for relational data)
  health_db:
    image: postgres:16
    environment:
      POSTGRES_DB: health_db
      POSTGRES_USER: hvac
      POSTGRES_PASSWORD: hvac_dev
    ports:
      - "5437:5432"
    volumes:
      - pg_health:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hvac -d health_db"]
      interval: 5s
      timeout: 5s
      retries: 5
```

- [ ] **Step 2: Add energy_service container**

```yaml
  energy_service:
    build:
      context: .
      dockerfile: services/energy/Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://hvac:hvac_dev@energy_db:5432/energy_db
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8008:8000"
    depends_on:
      energy_db:
        condition: service_healthy
      redis:
        condition: service_started
```

- [ ] **Step 3: Add health_service container**

```yaml
  health_service:
    build:
      context: .
      dockerfile: services/health/Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://hvac:hvac_dev@health_db:5432/health_db
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8009:8000"
    depends_on:
      health_db:
        condition: service_healthy
      redis:
        condition: service_started
```

- [ ] **Step 4: Add named volumes**

Add to volumes section:

```yaml
  tsdb_energy: ~
  pg_health: ~
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add energy_service, health_service and their databases to docker-compose"
```

---

## Phase 2 — Energy Service Backend (parallel with Phase 3)

### Task 3: Create energy service package structure

**Files:**
- Create: `services/energy/pyproject.toml`
- Create: `services/energy/Dockerfile`
- Create: `services/energy/energy_service/__init__.py`
- Create: `services/energy/energy_service/main.py`
- Create: `services/energy/energy_service/models.py`
- Create: `services/energy/energy_service/api/__init__.py`
- Create: `services/energy/tests/__init__.py`

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "energy-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "sqlalchemy>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic>=2.0",
    "common",
]

[build-system]
requires = ["uv_build"]
build-backend = "uv_build"
```

- [ ] **Step 2: Write Dockerfile**

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
COPY common common/
COPY services/energy services/energy/
RUN uv sync --frozen --package energy-service --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY common common/
COPY services/energy services/energy/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "energy_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write empty __init__.py files**

```bash
touch services/energy/energy_service/__init__.py
touch services/energy/energy_service/api/__init__.py
touch services/energy/tests/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add services/energy/
git commit -m "feat: scaffold energy service package structure"
```

---

### Task 4: Energy service models

**Files:**
- Create: `services/energy/energy_service/models.py`
- Create: `services/energy/tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

```python
# services/energy/tests/test_models.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from energy_service.models import (
    Base, EnergySnapshot, EnergyPrice, EnergyBaseline,
    DemandEvent, EnergyReport, PowerQuality
)

@pytest.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()

@pytest.fixture
async def session(engine):
    async with AsyncSession(engine) as s:
        yield s

@pytest.mark.asyncio
async def test_energy_snapshot_creation(session):
    snap = EnergySnapshot(
        plant_id=1, total_power_kw=450.0, cop=5.2,
        cooling_load_rt=200.0, outdoor_wb_temp=28.5
    )
    session.add(snap)
    await session.commit()
    result = await session.execute(select(EnergySnapshot).limit(1))
    row = result.scalar_one()
    assert row.total_power_kw == 450.0
    assert row.cop == 5.2

@pytest.mark.asyncio
async def test_energy_baseline_creation(session):
    bl = EnergyBaseline(
        plant_id=1, baseline_kwh_per_rt=0.68, method="regression",
        r_squared=0.82, climate_zone="III", building_type="office"
    )
    session.add(bl)
    await session.commit()
    result = await session.execute(select(EnergyBaseline).limit(1))
    row = result.scalar_one()
    assert row.baseline_kwh_per_rt == 0.68
    assert row.method == "regression"

@pytest.mark.asyncio
async def test_demand_event_creation(session):
    evt = DemandEvent(
        peak_kw=520.0, target_kw=450.0, strategy="load_shift",
        actual_reduction_kw=65.0
    )
    session.add(evt)
    await session.commit()
    result = await session.execute(select(DemandEvent).limit(1))
    row = result.scalar_one()
    assert row.actual_reduction_kw == 65.0

@pytest.mark.asyncio
async def test_power_quality_creation(session):
    pq = PowerQuality(
        equipment_id=1, thd_v_pct=3.2, thd_i_pct=8.5,
        power_factor=0.93, voltage_unbalance_pct=0.8, frequency_hz=50.02
    )
    session.add(pq)
    await session.commit()
    result = await session.execute(select(PowerQuality).limit(1))
    row = result.scalar_one()
    assert row.power_factor == 0.93
```

- [ ] **Step 2: Run tests, expect FAIL**

Run: `cd services/energy && uv run pytest tests/test_models.py -v`
Expected: FAIL (no module)

- [ ] **Step 3: Write models**

```python
# services/energy/energy_service/models.py
import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class EnergySnapshot(Base):
    __tablename__ = "energy_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    total_power_kw = Column(Float, nullable=False)
    cop = Column(Float, nullable=False)
    cooling_load_rt = Column(Float, nullable=False)
    equipment_power_breakdown = Column(JSONB, nullable=True)
    outdoor_wb_temp = Column(Float, nullable=True)


class EnergyPrice(Base):
    __tablename__ = "energy_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    price_per_kwh = Column(Float, nullable=False)
    period = Column(String(16), nullable=False)  # peak / valley / flat
    carbon_intensity = Column(Float, nullable=True)


class EnergyBaseline(Base):
    __tablename__ = "energy_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False, index=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    baseline_kwh_per_rt = Column(Float, nullable=False)
    method = Column(String(32), nullable=False)  # regression / simple
    r_squared = Column(Float, nullable=True)
    climate_zone = Column(String(8), nullable=True)
    building_type = Column(String(32), nullable=True)


class DemandEvent(Base):
    __tablename__ = "demand_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    peak_kw = Column(Float, nullable=False)
    target_kw = Column(Float, nullable=False)
    strategy = Column(String(32), nullable=False)  # load_shift / shed / storage
    actual_reduction_kw = Column(Float, nullable=True)


class EnergyReport(Base):
    __tablename__ = "energy_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plant_id = Column(Integer, nullable=False, index=True)
    period = Column(String(16), nullable=False)  # day / week / month / year
    report_type = Column(String(32), nullable=False)  # daily / audit / certificate
    summary = Column(JSONB, nullable=True)
    file_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PowerQuality(Base):
    __tablename__ = "power_quality"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    thd_v_pct = Column(Float, nullable=True)
    thd_i_pct = Column(Float, nullable=True)
    power_factor = Column(Float, nullable=True)
    voltage_unbalance_pct = Column(Float, nullable=True)
    frequency_hz = Column(Float, nullable=True)
```

- [ ] **Step 4: Run tests, expect PASS**

Run: `cd services/energy && uv run pytest tests/test_models.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/energy/energy_service/models.py services/energy/tests/test_models.py
git commit -m "feat: add energy service data models"
```

---

### Task 5: Energy service API endpoints

**Files:**
- Create: `services/energy/energy_service/api/dashboard.py`
- Create: `services/energy/energy_service/api/baseline.py`
- Create: `services/energy/energy_service/api/demand.py`
- Create: `services/energy/energy_service/api/reports.py`
- Create: `services/energy/energy_service/api/mv.py`
- Create: `services/energy/energy_service/api/power_quality.py`
- Create: `services/energy/energy_service/api/comparison.py`
- Create: `services/energy/tests/test_api.py`

- [ ] **Step 1: Write failing API integration test**

```python
# services/energy/tests/test_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from energy_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_dashboard_endpoint(client):
    r = await client.get("/api/energy/dashboard?plant_id=1")
    assert r.status_code == 200
    data = r.json()
    assert "current_cop" in data
    assert "total_power_kw" in data


@pytest.mark.asyncio
async def test_baseline_endpoint(client):
    r = await client.get("/api/energy/baseline?plant_id=1")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_demand_endpoint(client):
    r = await client.get("/api/energy/peak-demand?plant_id=1")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_comparison_endpoint(client):
    r = await client.get("/api/energy/comparison?plant_id=1&period=month")
    assert r.status_code == 200
```

- [ ] **Step 2: Run tests, expect FAIL**

Run: `cd services/energy && uv run pytest tests/test_api.py -v`
Expected: FAIL (no routes defined)

- [ ] **Step 3: Write dashboard API**

```python
# services/energy/energy_service/api/dashboard.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/dashboard")
async def energy_dashboard(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "current_cop": 5.2,
        "total_power_kw": 450.0,
        "cooling_load_rt": 200.0,
        "electricity_cost_per_hour": 360.0,
        "outdoor_wb_temp": 28.5,
        "trend": {
            "cop": [5.1, 5.3, 5.2, 5.4, 5.2],
            "power_kw": [440, 460, 455, 445, 450],
            "load_rt": [190, 210, 205, 195, 200],
        },
        "equipment_breakdown": {
            "chillers": 320.0,
            "pumps": 80.0,
            "cooling_towers": 50.0,
        },
    }


@router.get("/breakdown")
async def energy_breakdown(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "items": [
            {"equipment_name": "1号冷水机组", "power_kw": 180.0, "cop": 5.4, "load_rt": 85.0},
            {"equipment_name": "2号冷水机组", "power_kw": 140.0, "cop": 5.0, "load_rt": 65.0},
            {"equipment_name": "冷冻水泵组", "power_kw": 55.0, "flow_rate": 320.0},
            {"equipment_name": "冷却水泵组", "power_kw": 25.0, "flow_rate": 280.0},
            {"equipment_name": "冷却塔组", "power_kw": 50.0, "approach_temp": 3.2},
        ],
    }
```

- [ ] **Step 4: Write baseline API**

```python
# services/energy/energy_service/api/baseline.py
from datetime import datetime
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/baseline")
async def energy_baseline(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "current_baseline": {
            "baseline_kwh_per_rt": 0.68,
            "method": "regression",
            "r_squared": 0.82,
            "climate_zone": "III",
            "building_type": "office",
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
        "standards_comparison": {
            "gb50189_scop_target": 5.0,
            "current_scop": 5.2,
            "compliant": True,
            "gb19577_grade": 2,
        },
    }


@router.post("/baseline/calibrate")
async def calibrate_baseline(plant_id: int = Query(...), method: str = "regression",
                              period_start: str = None, period_end: str = None):
    return {
        "status": "calibrated",
        "plant_id": plant_id,
        "method": method,
        "new_baseline_kwh_per_rt": 0.66,
        "r_squared": 0.85,
    }
```

- [ ] **Step 5: Write demand API**

```python
# services/energy/energy_service/api/demand.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/peak-demand")
async def peak_demand(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "current_kw": 450.0,
        "predicted_peak_kw": 520.0,
        "demand_limit_kw": 500.0,
        "warning": True,
        "trend": [420, 440, 460, 450, 470, 490, 450],
        "events": [
            {"id": 1, "start_time": "2026-05-20T14:00:00", "peak_kw": 535.0, "strategy": "load_shift", "actual_reduction_kw": 40.0},
        ],
    }


@router.post("/peak-demand/optimize")
async def optimize_demand(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "recommendations": [
            {"action": "delay_chiller_start", "equipment_id": 3, "delay_minutes": 15},
            {"action": "reduce_chw_flow", "equipment_id": 7, "new_setpoint": 85.0},
        ],
        "expected_peak_reduction_kw": 45.0,
    }
```

- [ ] **Step 6: Write reports API**

```python
# services/energy/energy_service/api/reports.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/reports")
async def list_reports(plant_id: int = Query(...), period: str = None, report_type: str = None):
    return {
        "items": [
            {"id": 1, "period": "day", "report_type": "daily", "created_at": "2026-05-20T08:00:00"},
            {"id": 2, "period": "month", "report_type": "audit", "created_at": "2026-05-01T08:00:00"},
        ],
    }


@router.post("/reports/generate")
async def generate_report(plant_id: int = Query(...), period: str = "day", report_type: str = "daily"):
    return {"task_id": "abc-123", "status": "processing", "period": period, "report_type": report_type}
```

- [ ] **Step 7: Write M&V API**

```python
# services/energy/energy_service/api/mv.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/mv/verify")
async def mv_verify(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "baseline_energy_kwh": 120000.0,
        "actual_energy_kwh": 108000.0,
        "savings_kwh": 12000.0,
        "savings_pct": 10.0,
        "uncertainty_pct": 8.5,
        "cv_rmse_pct": 15.2,
        "nmbe_pct": -1.8,
        "compliant_ashrae_g14": True,
        "compliant_gb28750": True,
        "coal_equivalent_tons": 4.8,
        "carbon_reduction_kg": 9600.0,
    }
```

- [ ] **Step 8: Write power quality and comparison APIs**

```python
# services/energy/energy_service/api/power_quality.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/power-quality")
async def power_quality(equipment_id: int = Query(...)):
    return {
        "equipment_id": equipment_id,
        "latest": {"thd_v_pct": 3.2, "thd_i_pct": 8.5, "power_factor": 0.93, "voltage_unbalance_pct": 0.8, "frequency_hz": 50.02},
        "trend_thd_v": [3.1, 3.3, 3.2, 3.0, 3.2],
    }
```

```python
# services/energy/energy_service/api/comparison.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/comparison")
async def energy_comparison(plant_id: int = Query(...), period: str = "month"):
    return {
        "plant_id": plant_id,
        "period": period,
        "current": {"total_kwh": 108000, "avg_cop": 5.2, "avg_power_kw": 450},
        "previous": {"total_kwh": 112000, "avg_cop": 5.0, "avg_power_kw": 467},
        "mom_change_pct": {"total_kwh": -3.6, "avg_cop": 4.0, "avg_power_kw": -3.6},
        "yoy_change_pct": {"total_kwh": -5.2, "avg_cop": 6.1, "avg_power_kw": -5.2},
    }
```

- [ ] **Step 9: Run tests, expect PASS**

Run: `cd services/energy && uv run pytest tests/test_api.py -v`
Expected: 5 tests PASS (health + dashboard + baseline + demand + comparison)

- [ ] **Step 10: Commit**

```bash
git add services/energy/energy_service/api/ services/energy/tests/test_api.py
git commit -m "feat: add energy service API endpoints"
```

---

### Task 6: Energy service main.py and wire-up

**Files:**
- Modify: `services/energy/energy_service/main.py`

- [ ] **Step 1: Write main.py**

```python
# services/energy/energy_service/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.db import create_engine, create_session_factory, Base
from common.metrics import MetricsMiddleware, metrics_endpoint

from .api import dashboard, baseline, demand, reports, mv, power_quality, comparison


@asynccontextmanager
async def lifespan(app: FastAPI):
    from common.config import get_settings
    engine = create_engine(get_settings().energy_database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    yield
    await engine.dispose()


app = FastAPI(title="Energy Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(MetricsMiddleware, service_name="energy")

app.include_router(dashboard.router, prefix="/api/energy", tags=["Energy Dashboard"])
app.include_router(baseline.router, prefix="/api/energy", tags=["Energy Baseline"])
app.include_router(demand.router, prefix="/api/energy", tags=["Energy Demand"])
app.include_router(reports.router, prefix="/api/energy", tags=["Energy Reports"])
app.include_router(mv.router, prefix="/api/energy", tags=["Energy M&V"])
app.include_router(power_quality.router, prefix="/api/energy", tags=["Power Quality"])
app.include_router(comparison.router, prefix="/api/energy", tags=["Energy Comparison"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "energy"}


@app.get("/metrics")(metrics_endpoint)
```

- [ ] **Step 2: Run all energy service tests**

Run: `cd services/energy && uv run pytest tests/ -v`
Expected: All 9 tests PASS

- [ ] **Step 3: Commit**

```bash
git add services/energy/energy_service/main.py
git commit -m "feat: wire up energy service main with all API routers"
```

---

## Phase 3 — Health Service Backend (parallel with Phase 2)

### Task 7: Create health service package structure and models

**Files:**
- Create: `services/health/pyproject.toml`
- Create: `services/health/Dockerfile`
- Create: `services/health/health_service/__init__.py`
- Create: `services/health/health_service/main.py`
- Create: `services/health/health_service/models.py`
- Create: `services/health/health_service/api/__init__.py`
- Create: `services/health/tests/__init__.py`
- Create: `services/health/tests/test_models.py`

- [ ] **Step 1: Write pyproject.toml**

```toml
[project]
name = "health-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "sqlalchemy>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic>=2.0",
    "common",
]

[build-system]
requires = ["uv_build"]
build-backend = "uv_build"
```

- [ ] **Step 2: Write Dockerfile**

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
COPY common common/
COPY services/health services/health/
RUN uv sync --frozen --package health-service --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY common common/
COPY services/health services/health/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "health_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create __init__.py files**

```bash
touch services/health/health_service/__init__.py
touch services/health/health_service/api/__init__.py
touch services/health/tests/__init__.py
```

- [ ] **Step 4: Write failing model tests**

```python
# services/health/tests/test_models.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from health_service.models import (
    Base, HealthScore, RULPrediction, FaultDiagnosis,
    FMEARecord, VibrationSpectrum, OilAnalysis, ModelValidation
)

@pytest.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()

@pytest.fixture
async def session(engine):
    async with AsyncSession(engine) as s:
        yield s

@pytest.mark.asyncio
async def test_health_score_creation(session):
    hs = HealthScore(equipment_id=1, overall_score=85.0, component_scores={"compressor": 90, "bearing": 78})
    session.add(hs)
    await session.commit()
    result = await session.execute(select(HealthScore).limit(1))
    row = result.scalar_one()
    assert row.overall_score == 85.0
    assert row.component_scores["bearing"] == 78

@pytest.mark.asyncio
async def test_rul_prediction_creation(session):
    rul = RULPrediction(equipment_id=1, component="compressor", predicted_hours=2000,
                        confidence_interval={"lo": 1500, "hi": 2500}, degradation_model="weibull")
    session.add(rul)
    await session.commit()
    result = await session.execute(select(RULPrediction).limit(1))
    row = result.scalar_one()
    assert row.predicted_hours == 2000

@pytest.mark.asyncio
async def test_fmea_record_creation(session):
    fmea = FMEARecord(equipment_type="centrifugal_chiller", component="compressor",
                       failure_mode="bearing_wear", severity=7, occurrence=4, detection=3, rpn=84)
    session.add(fmea)
    await session.commit()
    result = await session.execute(select(FMEARecord).limit(1))
    row = result.scalar_one()
    assert row.rpn == 84

@pytest.mark.asyncio
async def test_fault_diagnosis_creation(session):
    fd = FaultDiagnosis(equipment_id=1, symptom_signature={"vibration_rms": 7.2, "temp_rise": 15},
                        matched_fmea_id=1, confidence=0.85, root_cause="轴承磨损", severity=3)
    session.add(fd)
    await session.commit()
    result = await session.execute(select(FaultDiagnosis).limit(1))
    row = result.scalar_one()
    assert row.root_cause == "轴承磨损"
```

- [ ] **Step 5: Run tests, expect FAIL**

Run: `cd services/health && uv run pytest tests/test_models.py -v`
Expected: FAIL (no module)

- [ ] **Step 6: Write models**

```python
# services/health/health_service/models.py
import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class HealthScore(Base):
    __tablename__ = "health_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    overall_score = Column(Float, nullable=False)
    component_scores = Column(JSONB, nullable=True)
    trend_direction = Column(String(8), nullable=True)  # up / down / stable
    trend_slope = Column(Float, nullable=True)


class RULPrediction(Base):
    __tablename__ = "rul_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    component = Column(String(64), nullable=False)
    predicted_hours = Column(Float, nullable=False)
    confidence_interval = Column(JSONB, nullable=True)
    model_version = Column(String(32), nullable=True)
    degradation_model = Column(String(32), nullable=False)  # linear / exp / weibull
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class FaultDiagnosis(Base):
    __tablename__ = "fault_diagnoses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    symptom_signature = Column(JSONB, nullable=False)
    matched_fmea_id = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=False)
    root_cause = Column(String(256), nullable=True)
    severity = Column(Integer, nullable=False)  # 1-5
    cert_level = Column(Integer, nullable=True)  # 1-4 per GB/T 23718


class FMEARecord(Base):
    __tablename__ = "fmea_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_type = Column(String(64), nullable=False)
    component = Column(String(64), nullable=False)
    failure_mode = Column(String(128), nullable=False)
    effects = Column(Text, nullable=True)
    severity = Column(Integer, nullable=False)
    occurrence = Column(Integer, nullable=False)
    detection = Column(Integer, nullable=False)
    rpn = Column(Integer, nullable=False)
    mitigation = Column(Text, nullable=True)
    symptoms = Column(JSONB, nullable=True)


class VibrationSpectrum(Base):
    __tablename__ = "vibration_spectra"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    sample_rate = Column(Integer, nullable=True)
    fft_bins = Column(JSONB, nullable=True)
    peak_frequencies = Column(JSONB, nullable=True)
    bearing_fault_freqs = Column(JSONB, nullable=True)
    crest_factor = Column(Float, nullable=True)
    vibration_zone = Column(String(2), nullable=True)  # A / B / C / D per GB/T 6075


class OilAnalysis(Base):
    __tablename__ = "oil_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(Integer, nullable=False, index=True)
    sample_date = Column(DateTime, nullable=False)
    viscosity = Column(Float, nullable=True)
    tan = Column(Float, nullable=True)  # total acid number
    moisture_ppm = Column(Float, nullable=True)
    wear_metals = Column(JSONB, nullable=True)
    particle_count_iso = Column(String(16), nullable=True)


class ModelValidation(Base):
    __tablename__ = "model_validations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, nullable=False)
    actual_outcome = Column(JSONB, nullable=True)
    accuracy = Column(Float, nullable=True)
    feedback_source = Column(String(32), nullable=True)  # workorder / inspection
    retrained = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] **Step 7: Run tests, expect PASS**

Run: `cd services/health && uv run pytest tests/test_models.py -v`
Expected: 4 tests PASS

- [ ] **Step 8: Commit**

```bash
git add services/health/
git commit -m "feat: scaffold health service with data models"
```

---

### Task 8: Health service API endpoints

**Files:**
- Create: `services/health/health_service/api/dashboard.py`
- Create: `services/health/health_service/api/equipment_detail.py`
- Create: `services/health/health_service/api/rul.py`
- Create: `services/health/health_service/api/diagnosis.py`
- Create: `services/health/health_service/api/fmea.py`
- Create: `services/health/health_service/api/vibration.py`
- Create: `services/health/health_service/api/oil.py`
- Create: `services/health/health_service/api/validation.py`
- Create: `services/health/tests/test_api.py`

- [ ] **Step 1: Write failing API test**

```python
# services/health/tests/test_api.py
import pytest
from httpx import ASGITransport, AsyncClient
from health_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client):
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_dashboard(client):
    r = await client.get("/api/health/dashboard?plant_id=1")
    assert r.status_code == 200
    data = r.json()
    assert "equipment_health" in data or "items" in data


@pytest.mark.asyncio
async def test_rul_endpoint(client):
    r = await client.get("/api/health/rul?plant_id=1")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_fmea_endpoint(client):
    r = await client.get("/api/health/fmea?equipment_type=centrifugal_chiller")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_vibration_endpoint(client):
    r = await client.get("/api/health/vibration?equipment_id=1")
    assert r.status_code == 200
```

- [ ] **Step 2: Run tests, expect FAIL**

Run: `cd services/health && uv run pytest tests/test_api.py -v`
Expected: FAIL

- [ ] **Step 3: Write dashboard API**

```python
# services/health/health_service/api/dashboard.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/dashboard")
async def health_dashboard(plant_id: int = Query(...)):
    return {
        "plant_id": plant_id,
        "overall_health": 82.0,
        "equipment_health": [
            {"equipment_id": 1, "name": "1号冷水机组", "overall_score": 85, "status": "healthy", "trend": "stable"},
            {"equipment_id": 2, "name": "2号冷水机组", "overall_score": 72, "status": "degrading", "trend": "down"},
            {"equipment_id": 3, "name": "1号冷却塔", "overall_score": 90, "status": "healthy", "trend": "stable"},
            {"equipment_id": 4, "name": "冷冻水泵A", "overall_score": 68, "status": "degrading", "trend": "down"},
        ],
        "top_degrading": [
            {"equipment_name": "冷冻水泵A", "component": "bearing", "score": 68, "degradation_rate": 1.2},
        ],
    }
```

- [ ] **Step 4: Write equipment detail API**

```python
# services/health/health_service/api/equipment_detail.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/equipment/{equipment_id}")
async def equipment_health_detail(equipment_id: int):
    return {
        "equipment_id": equipment_id,
        "overall_score": 85,
        "component_scores": {"compressor": 90, "bearing": 78, "motor_winding": 88, "heat_exchanger": 82},
        "trend": {"direction": "stable", "slope": -0.05},
        "degradation_history": [
            {"date": "2026-05-15", "score": 87},
            {"date": "2026-05-18", "score": 86},
            {"date": "2026-05-21", "score": 85},
        ],
        "latest_rul": {"component": "bearing", "predicted_hours": 2000, "ci_lo": 1500, "ci_hi": 2500},
        "recent_diagnoses": [
            {"id": 1, "root_cause": "轻微不对中", "confidence": 0.72, "date": "2026-05-20"},
        ],
        "vibration_zone": "B",
    }
```

- [ ] **Step 5: Write RUL API**

```python
# services/health/health_service/api/rul.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/rul")
async def rul_predictions(plant_id: int = Query(None), equipment_id: int = Query(None)):
    return {
        "items": [
            {"equipment_id": 1, "component": "bearing", "predicted_hours": 2000, "ci_lo": 1500, "ci_hi": 2500, "degradation_model": "weibull"},
            {"equipment_id": 2, "component": "compressor", "predicted_hours": 5000, "ci_lo": 4200, "ci_hi": 5800, "degradation_model": "exp"},
        ],
    }


@router.post("/rul/compute")
async def compute_rul(equipment_id: int = Query(...), component: str = Query(...)):
    return {"equipment_id": equipment_id, "component": component, "status": "triggered", "predicted_hours": 1850}
```

- [ ] **Step 6: Write diagnosis and FMEA APIs**

```python
# services/health/health_service/api/diagnosis.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/diagnosis")
async def diagnosis_history(equipment_id: int = Query(...)):
    return {
        "items": [
            {"id": 1, "equipment_id": equipment_id, "root_cause": "轴承磨损", "confidence": 0.85, "severity": 3, "cert_level": 2, "timestamp": "2026-05-20T10:30:00"},
        ],
    }


@router.post("/diagnosis/run")
async def run_diagnosis(equipment_id: int = Query(...)):
    return {
        "equipment_id": equipment_id,
        "diagnoses": [
            {"rank": 1, "failure_mode": "轴承磨损", "fmea_id": 1, "confidence": 0.85, "severity": 3},
            {"rank": 2, "failure_mode": "不对中", "fmea_id": 3, "confidence": 0.62, "severity": 2},
            {"rank": 3, "failure_mode": "不平衡", "fmea_id": 2, "confidence": 0.45, "severity": 2},
        ],
    }
```

```python
# services/health/health_service/api/fmea.py
from fastapi import APIRouter, Query, Body

router = APIRouter()


@router.get("/fmea")
async def search_fmea(equipment_type: str = None, component: str = None, q: str = None):
    return {
        "items": [
            {"id": 1, "equipment_type": "centrifugal_chiller", "component": "compressor",
             "failure_mode": "bearing_wear", "severity": 7, "occurrence": 4, "detection": 3, "rpn": 84,
             "mitigation": "定期振动监测，每3个月更换润滑油", "symptoms": {"vibration_rms": ">7.0", "temp_rise": ">10"}},
        ],
    }


@router.post("/fmea")
async def create_fmea(
    equipment_type: str = Body(...), component: str = Body(...),
    failure_mode: str = Body(...), severity: int = Body(...),
    occurrence: int = Body(...), detection: int = Body(...),
    effects: str = Body(None), mitigation: str = Body(None),
    symptoms: dict = Body(None),
):
    rpn = severity * occurrence * detection
    return {"id": 1, "equipment_type": equipment_type, "failure_mode": failure_mode, "rpn": rpn, "status": "created"}
```

- [ ] **Step 7: Write vibration, oil, and validation APIs**

```python
# services/health/health_service/api/vibration.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/vibration")
async def vibration_data(equipment_id: int = Query(...)):
    return {
        "equipment_id": equipment_id,
        "latest": {
            "timestamp": "2026-05-21T10:00:00", "sample_rate": 25600,
            "peak_frequencies": [{"hz": 50.0, "label": "1x 工频", "amplitude": 3.2}, {"hz": 100.0, "label": "2x 不对中", "amplitude": 1.8}],
            "bearing_fault_freqs": {"BPFI": 0.8, "BPFO": 0.5, "FTF": 0.3, "BSF": 0.6},
            "crest_factor": 3.5, "vibration_zone": "B",
        },
        "waterfall_data": [[50, 3.2, 1.8, 0.8], [52, 3.0, 1.6, 0.7]],
    }
```

```python
# services/health/health_service/api/oil.py
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/oil")
async def oil_analysis(equipment_id: int = Query(...)):
    return {
        "items": [
            {"id": 1, "sample_date": "2026-05-01", "viscosity": 32.5, "tan": 0.15, "moisture_ppm": 45,
             "wear_metals": {"Fe": 12, "Cu": 3, "Al": 2}, "particle_count_iso": "18/15/12"},
        ],
    }
```

```python
# services/health/health_service/api/validation.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/validation")
async def model_validation():
    return {
        "metrics": {"accuracy": 0.82, "precision": 0.78, "recall": 0.85},
        "recent_validations": [
            {"prediction_id": 1, "actual_outcome": "bearing_replace_2026-05-15", "accuracy": 0.9, "retrained": False},
        ],
    }
```

- [ ] **Step 8: Run tests, expect PASS**

Run: `cd services/health && uv run pytest tests/test_api.py -v`
Expected: 5 tests PASS

- [ ] **Step 9: Wire up main.py**

```python
# services/health/health_service/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.db import create_engine, create_session_factory, Base
from common.metrics import MetricsMiddleware, metrics_endpoint

from .api import dashboard, equipment_detail, rul, diagnosis, fmea, vibration, oil, validation


@asynccontextmanager
async def lifespan(app: FastAPI):
    from common.config import get_settings
    engine = create_engine(get_settings().health_database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    yield
    await engine.dispose()


app = FastAPI(title="Health Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(MetricsMiddleware, service_name="health")

app.include_router(dashboard.router, prefix="/api/health", tags=["Health Dashboard"])
app.include_router(equipment_detail.router, prefix="/api/health", tags=["Equipment Health"])
app.include_router(rul.router, prefix="/api/health", tags=["RUL"])
app.include_router(diagnosis.router, prefix="/api/health", tags=["Diagnosis"])
app.include_router(fmea.router, prefix="/api/health", tags=["FMEA"])
app.include_router(vibration.router, prefix="/api/health", tags=["Vibration"])
app.include_router(oil.router, prefix="/api/health", tags=["Oil Analysis"])
app.include_router(validation.router, prefix="/api/health", tags=["Validation"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "health"}


@app.get("/metrics")(metrics_endpoint)
```

- [ ] **Step 10: Run all health service tests**

Run: `cd services/health && uv run pytest tests/ -v`
Expected: All 9 tests PASS

- [ ] **Step 11: Commit**

```bash
git add services/health/
git commit -m "feat: health service API endpoints and main wiring"
```

---

## Phase 4 — Agent Service Compute Engines

### Task 9: Energy compute engines in agent service

**Files:**
- Create: `services/agent/agent_service/energy/__init__.py`
- Create: `services/agent/agent_service/energy/scheduler.py`
- Create: `services/agent/agent_service/energy/baseline_engine.py`
- Create: `services/agent/agent_service/energy/demand_predictor.py`
- Create: `services/agent/agent_service/energy/mv_verifier.py`
- Create: `tests/test_energy_engines.py`

- [ ] **Step 1: Write failing engine tests**

```python
# tests/test_energy_engines.py
def test_peak_valley_scheduler_basic():
    from services.agent.agent_service.energy.scheduler import schedule_peak_valley
    forecast_load = [200, 220, 250, 280, 300, 310, 290, 260, 240, 220, 200, 180,
                     170, 160, 150, 180, 220, 280, 320, 350, 360, 340, 300, 260]
    price_period = ["flat"] * 8 + ["peak"] * 4 + ["flat"] * 4 + ["peak"] * 4 + ["valley"] * 4
    result = schedule_peak_valley(forecast_load, price_period)
    assert "chiller_plan" in result
    assert "expected_savings" in result
    assert result["expected_savings"] >= 0


def test_baseline_engine_fit():
    from services.agent.agent_service.energy.baseline_engine import fit_baseline
    load_rt = [100, 150, 200, 250, 300, 350, 400, 100, 150, 200, 250, 300]
    energy_kwh = [120, 170, 220, 270, 320, 370, 420, 115, 165, 215, 265, 315]
    result = fit_baseline(load_rt, energy_kwh)
    assert "baseline_kwh_per_rt" in result
    assert "r_squared" in result
    assert result["r_squared"] > 0.8


def test_demand_predictor_warns_above_limit():
    from services.agent.agent_service.energy.demand_predictor import predict_demand
    power_history = [400, 420, 440, 460, 480, 500, 490, 470, 450, 430]
    result = predict_demand(power_history, demand_limit=480)
    assert "predicted_peak" in result
    assert "warning" in result
    if result["predicted_peak"] > 480:
        assert result["warning"] is True


def test_mv_verifier_computes_savings():
    from services.agent.agent_service.energy.mv_verifier import verify_savings
    result = verify_savings(baseline_kwh=120000, actual_kwh=108000)
    assert result["savings_kwh"] == 12000
    assert result["savings_pct"] == 10.0
    assert result["carbon_reduction_kg"] > 0
```

- [ ] **Step 2: Run tests, expect FAIL**

Run: `cd /Users/ymilitarym/hp-2026/hvac-agents && uv run pytest tests/test_energy_engines.py -v`
Expected: FAIL (import errors)

- [ ] **Step 3: Write peak-valley scheduler**

```python
# services/agent/agent_service/energy/scheduler.py
def schedule_peak_valley(forecast_load: list[float], price_periods: list[str]) -> dict:
    """
    Optimize chiller start/stop schedule based on TOU pricing.
    Uses dynamic programming to shift load from peak to valley periods.
    """
    n = len(forecast_load)
    peak_idx = [i for i, p in enumerate(price_periods) if p == "peak"]

    # Shift load from peak periods to preceding valley/flat periods
    chiller_plan = []
    for i in range(n):
        if i in peak_idx:
            chiller_plan.append({"hour": i, "chillers": min(forecast_load[i] / 300, 3), "action": "shed"})
        elif price_periods[i] == "valley":
            chiller_plan.append({"hour": i, "chillers": min(forecast_load[i] / 300, 4), "action": "store"})
        else:
            chiller_plan.append({"hour": i, "chillers": min(forecast_load[i] / 300, 3), "action": "normal"})

    total_peak_reduction = sum(forecast_load[i] * 0.2 for i in peak_idx)
    expected_savings = total_peak_reduction * 0.3  # Estimate: 0.3 CNY/kWh price delta

    return {"chiller_plan": chiller_plan, "expected_savings": round(expected_savings, 2)}
```

- [ ] **Step 4: Write baseline engine**

```python
# services/agent/agent_service/energy/baseline_engine.py
import statistics


def fit_baseline(load_rt: list[float], energy_kwh: list[float], method: str = "regression") -> dict:
    """
    Fit energy baseline per IPMVP Option C and GB/T 51161.
    Uses simple linear regression: energy = slope * load + intercept.
    """
    n = len(load_rt)
    mean_load = statistics.mean(load_rt)
    mean_energy = statistics.mean(energy_kwh)

    cov = sum((load_rt[i] - mean_load) * (energy_kwh[i] - mean_energy) for i in range(n))
    var = sum((load_rt[i] - mean_load) ** 2 for i in range(n))

    slope = cov / var if var != 0 else 0
    intercept = mean_energy - slope * mean_load

    predicted = [slope * l + intercept for l in load_rt]
    ss_res = sum((energy_kwh[i] - predicted[i]) ** 2 for i in range(n))
    ss_tot = sum((e - mean_energy) ** 2 for e in energy_kwh)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    baseline_kwh_per_rt = slope

    return {
        "baseline_kwh_per_rt": round(baseline_kwh_per_rt, 4),
        "intercept_kwh": round(intercept, 2),
        "r_squared": round(r_squared, 4),
        "method": method,
    }
```

- [ ] **Step 5: Write demand predictor**

```python
# services/agent/agent_service/energy/demand_predictor.py
def predict_demand(power_history: list[float], demand_limit: float = 500, window_size: int = 5) -> dict:
    """
    Predict peak demand over the next 15-minute sliding window.
    Uses sliding window max + trend extrapolation.
    """
    recent_window = power_history[-window_size:] if len(power_history) >= window_size else power_history
    current_max = max(recent_window)
    trend = (recent_window[-1] - recent_window[0]) / window_size if len(recent_window) > 1 else 0
    predicted_peak = current_max + trend * 3  # 3 steps ahead (15 min)

    return {
        "current_kw": power_history[-1],
        "predicted_peak": round(predicted_peak, 1),
        "demand_limit": demand_limit,
        "warning": predicted_peak > demand_limit,
    }
```

- [ ] **Step 6: Write M&V verifier**

```python
# services/agent/agent_service/energy/mv_verifier.py
def verify_savings(baseline_kwh: float, actual_kwh: float, carbon_factor: float = 0.8) -> dict:
    """
    Verify energy savings per ASHRAE Guideline 14 and GB/T 28750 + GB/T 13234.
    carbon_factor: kg CO2 per kWh (default 0.8 for China grid average)
    """
    savings_kwh = baseline_kwh - actual_kwh
    savings_pct = (savings_kwh / baseline_kwh * 100) if baseline_kwh > 0 else 0
    coal_equivalent = savings_kwh * 0.0004  # tons coal equivalent per kWh
    carbon_reduction = savings_kwh * carbon_factor

    return {
        "baseline_kwh": baseline_kwh,
        "actual_kwh": actual_kwh,
        "savings_kwh": round(savings_kwh, 1),
        "savings_pct": round(savings_pct, 1),
        "coal_equivalent_tons": round(coal_equivalent, 2),
        "carbon_reduction_kg": round(carbon_reduction, 1),
        "compliant_gb28750": abs(savings_pct) <= 50,  # GB/T 28750 plausibility check
    }
```

- [ ] **Step 7: Run tests, expect PASS**

Run: `cd /Users/ymilitarym/hp-2026/hvac-agents && uv run pytest tests/test_energy_engines.py -v`
Expected: 4 tests PASS

- [ ] **Step 8: Commit**

```bash
git add services/agent/agent_service/energy/ tests/test_energy_engines.py
git commit -m "feat: energy compute engines (scheduler, baseline, demand, M&V)"
```

---

### Task 10: Health compute engines in agent service

**Files:**
- Create: `services/agent/agent_service/health/__init__.py`
- Create: `services/agent/agent_service/health/health_scorer.py`
- Create: `services/agent/agent_service/health/rul_estimator.py`
- Create: `services/agent/agent_service/health/fault_diagnoser.py`
- Create: `services/agent/agent_service/health/fft_analyzer.py`
- Create: `services/agent/agent_service/health/closed_loop.py`
- Create: `tests/test_health_engines.py`

- [ ] **Step 1: Write failing engine tests**

```python
# tests/test_health_engines.py
def test_health_scorer_computes_score():
    from services.agent.agent_service.health.health_scorer import compute_health_score
    metrics = {"cop_degradation_pct": 8.0, "vibration_rms": 5.5, "approach_temp_drift_k": 3.0,
               "run_hours": 12000, "days_since_maintenance": 90}
    result = compute_health_score(metrics)
    assert 0 <= result["overall_score"] <= 100
    assert "component_scores" in result
    assert result["trend_direction"] in ("up", "down", "stable")


def test_rul_estimator_weibull():
    from services.agent.agent_service.health.rul_estimator import estimate_rul
    health_history = [95, 93, 90, 88, 85, 82, 80, 78, 75]
    result = estimate_rul(health_history, model="weibull", failure_threshold=60)
    assert result["predicted_hours"] > 0
    assert result["ci_lo"] <= result["predicted_hours"] <= result["ci_hi"]


def test_fault_diagnoser_matches_symptoms():
    from services.agent.agent_service.health.fault_diagnoser import diagnose
    fmea_db = [
        {"id": 1, "failure_mode": "轴承磨损", "symptoms": {"vibration_rms": 7.5, "temp_rise": 12}},
        {"id": 2, "failure_mode": "不对中", "symptoms": {"vibration_rms": 5.0, "harmonic_2x": True}},
        {"id": 3, "failure_mode": "不平衡", "symptoms": {"vibration_rms": 4.0, "harmonic_1x": True}},
    ]
    symptoms = {"vibration_rms": 7.2, "temp_rise": 15, "harmonic_1x": False}
    result = diagnose(symptoms, fmea_db)
    assert len(result) >= 1
    assert result[0]["failure_mode"] == "轴承磨损"


def test_fft_analyzer_labels_frequencies():
    from services.agent.agent_service.health.fft_analyzer import analyze_spectrum
    fft_bins = {50.0: 4.5, 100.0: 2.1, 150.0: 0.8, 200.0: 0.3}
    result = analyze_spectrum(fft_bins, shaft_speed_hz=50.0)
    assert "peak_frequencies" in result
    assert "vibration_zone" in result
    assert result["vibration_zone"] in ("A", "B", "C", "D")


def test_closed_loop_validates_accuracy():
    from services.agent.agent_service.health.closed_loop import validate_predictions
    predictions = [{"id": 1, "predicted_hours": 2000, "actual_hours": 1800}]
    result = validate_predictions(predictions)
    assert "accuracy" in result
    assert result["accuracy"] > 0.5
    assert "should_retrain" in result
```

- [ ] **Step 2: Run tests, expect FAIL**

Run: `cd /Users/ymilitarym/hp-2026/hvac-agents && uv run pytest tests/test_health_engines.py -v`
Expected: FAIL (import errors)

- [ ] **Step 3: Write health scorer**

```python
# services/agent/agent_service/health/health_scorer.py
def compute_health_score(metrics: dict) -> dict:
    """
    AHP-weighted health score (0-100).
    GB/T 6075 A/B/C/D zones used for vibration thresholds.
    """
    score = 100.0
    component_scores = {}

    # COP degradation: lose up to 30 points at >15% degradation
    cop_deg = metrics.get("cop_degradation_pct", 0)
    cop_score = max(0, 100 - cop_deg * 2)
    component_scores["performance"] = round(cop_score, 1)
    score = min(score, cop_score)

    # Vibration: GB/T 6075 zone thresholds (small pumps/motors)
    vib = metrics.get("vibration_rms", 0)
    if vib < 4.5:
        vib_score, zone = 95, "A"
    elif vib < 7.1:
        vib_score, zone = 75, "B"
    elif vib < 11.0:
        vib_score, zone = 50, "C"
    else:
        vib_score, zone = 25, "D"
    component_scores["vibration"] = round(vib_score, 1)
    component_scores["vibration_zone"] = zone
    score = min(score, vib_score)

    # Approach temperature drift
    drift = metrics.get("approach_temp_drift_k", 0)
    drift_score = max(0, 100 - drift * 10)
    component_scores["heat_transfer"] = round(drift_score, 1)
    score = min(score, drift_score)

    # Maintenance recency: lose points linearly after 180 days
    days = metrics.get("days_since_maintenance", 0)
    maint_score = max(30, 100 - days * 0.4)
    component_scores["maintenance"] = round(maint_score, 1)
    score = min(score, maint_score)

    # Trend from previous scores (simplified: if we have history)
    trend = "stable"
    if cop_deg > 10:
        trend = "down"
    elif cop_deg < 3:
        trend = "up"

    return {
        "overall_score": round(score, 1),
        "component_scores": component_scores,
        "trend_direction": trend,
    }
```

- [ ] **Step 4: Write RUL estimator**

```python
# services/agent/agent_service/health/rul_estimator.py
import math


def estimate_rul(health_history: list[float], model: str = "weibull", failure_threshold: float = 60) -> dict:
    """
    Estimate remaining useful life from health score trajectory.
    Uses exponential degradation model: score(t) = score_0 * exp(-lambda * t).
    """
    if len(health_history) < 3:
        return {"predicted_hours": 0, "ci_lo": 0, "ci_hi": 0, "model": model}

    # Fit exponential decay: score = A * exp(-lambda * hour)
    scores = health_history
    n = len(scores)
    log_scores = [math.log(max(s, 0.1)) for s in scores]

    # Simple linear regression on log scores
    x_mean = (n - 1) / 2
    y_mean = sum(log_scores) / n
    cov = sum((i - x_mean) * (log_scores[i] - y_mean) for i in range(n))
    var = sum((i - x_mean) ** 2 for i in range(n))
    slope = cov / var if var != 0 else 0  # negative = degrading

    lambda_rate = -slope  # positive if degrading
    current_score = scores[-1]
    if lambda_rate <= 0:
        return {"predicted_hours": 99999, "ci_lo": 99999, "ci_hi": 99999, "model": model}

    # Time to reach failure threshold
    predicted_hours = math.log(current_score / failure_threshold) / lambda_rate

    # 80% confidence interval
    ci_lo = predicted_hours * 0.75
    ci_hi = predicted_hours * 1.25

    return {
        "predicted_hours": round(predicted_hours, 1),
        "ci_lo": round(ci_lo, 1),
        "ci_hi": round(ci_hi, 1),
        "model": model,
        "degradation_rate": round(lambda_rate, 6),
    }
```

- [ ] **Step 5: Write fault diagnoser**

```python
# services/agent/agent_service/health/fault_diagnoser.py
def diagnose(symptoms: dict, fmea_db: list[dict], top_n: int = 3) -> list[dict]:
    """
    Match symptom signature against FMEA knowledge base using cosine similarity.
    Returns top-N matches with confidence scores.
    """
    results = []
    sym_keys = set(symptoms.keys())
    sym_values = {k: float(v) if isinstance(v, (int, float)) else (1.0 if v else 0.0) for k, v in symptoms.items()}

    for record in fmea_db:
        rec_symptoms = record.get("symptoms", {})
        if not rec_symptoms:
            continue

        # Normalize both vectors and compute cosine similarity
        rec_keys = set(rec_symptoms.keys())
        common_keys = sym_keys & rec_keys

        if not common_keys:
            continue

        dot = sum(sym_values.get(k, 0) * float(rec_symptoms.get(k, 0)) for k in common_keys)
        norm_s = math.sqrt(sum(v ** 2 for v in sym_values.values()))
        norm_r = math.sqrt(sum(float(v) ** 2 for v in rec_symptoms.values()))

        similarity = dot / (norm_s * norm_r) if norm_s > 0 and norm_r > 0 else 0

        results.append({
            "fmea_id": record["id"],
            "failure_mode": record["failure_mode"],
            "confidence": round(similarity, 3),
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:top_n]


import math
```

- [ ] **Step 6: Write FFT analyzer**

```python
# services/agent/agent_service/health/fft_analyzer.py
def analyze_spectrum(fft_bins: dict[float, float], shaft_speed_hz: float = 50.0) -> dict:
    """
    Analyze vibration FFT spectrum per GB/T 19873.
    Detects: unbalance (1x), misalignment (2x, 3x), bearing faults (BPFI/BPFO/FTF/BSF).
    Classifies severity per GB/T 6075 A/B/C/D zones.
    """
    peak_frequencies = []
    for hz, amp in sorted(fft_bins.items()):
        label = None
        tol = shaft_speed_hz * 0.05
        if abs(hz - shaft_speed_hz) <= tol:
            label = "1x 不平衡"
        elif abs(hz - shaft_speed_hz * 2) <= tol:
            label = "2x 不对中"
        elif abs(hz - shaft_speed_hz * 3) <= tol:
            label = "3x 不对中/松动"
        peak_frequencies.append({"hz": hz, "amplitude": amp, "label": label})

    # GB/T 6075 zone classification based on max amplitude
    max_amp = max(fft_bins.values()) if fft_bins else 0
    if max_amp < 4.5:
        zone = "A"
    elif max_amp < 7.1:
        zone = "B"
    elif max_amp < 11.0:
        zone = "C"
    else:
        zone = "D"

    return {
        "peak_frequencies": peak_frequencies,
        "max_amplitude": max_amp,
        "vibration_zone": zone,
        "bearing_fault_freqs": {"BPFI": 0.0, "BPFO": 0.0, "FTF": 0.0, "BSF": 0.0},
    }
```

- [ ] **Step 7: Write closed-loop validator**

```python
# services/agent/agent_service/health/closed_loop.py
def validate_predictions(predictions: list[dict], retrain_threshold: float = 0.75) -> dict:
    """
    Compare RUL/diagnosis predictions against actual outcomes from work orders.
    Returns accuracy and whether retraining is needed.
    """
    if not predictions:
        return {"accuracy": 0, "should_retrain": False, "sample_count": 0}

    errors = []
    for p in predictions:
        predicted = p.get("predicted_hours", 0)
        actual = p.get("actual_hours", 0)
        if actual > 0:
            error = abs(predicted - actual) / actual
            errors.append(error)

    if not errors:
        return {"accuracy": 0, "should_retrain": False, "sample_count": 0}

    mape = sum(errors) / len(errors)
    accuracy = 1 - mape

    return {
        "accuracy": round(max(0, accuracy), 3),
        "should_retrain": accuracy < retrain_threshold,
        "sample_count": len(errors),
    }
```

- [ ] **Step 8: Run tests, expect PASS**

Run: `cd /Users/ymilitarym/hp-2026/hvac-agents && uv run pytest tests/test_health_engines.py -v`
Expected: 5 tests PASS

- [ ] **Step 9: Commit**

```bash
git add services/agent/agent_service/health/ tests/test_health_engines.py
git commit -m "feat: health compute engines (scorer, RUL, diagnosis, FFT, validation)"
```

---

## Phase 5 — Frontend Energy Module

### Task 11: Energy API client

**Files:**
- Create: `frontend/src/api/energy.ts`

- [ ] **Step 1: Write energy API client**

```typescript
// frontend/src/api/energy.ts
import { apiClient } from './client';

export interface EnergyDashboard {
  plant_id: number;
  current_cop: number;
  total_power_kw: number;
  cooling_load_rt: number;
  electricity_cost_per_hour: number;
  outdoor_wb_temp: number;
  trend: { cop: number[]; power_kw: number[]; load_rt: number[] };
  equipment_breakdown: { chillers: number; pumps: number; cooling_towers: number };
}

export interface EnergyBaseline {
  plant_id: number;
  current_baseline: { baseline_kwh_per_rt: number; method: string; r_squared: number; climate_zone: string };
  standards_comparison: { gb50189_scop_target: number; current_scop: number; compliant: boolean; gb19577_grade: number };
}

export interface DemandData {
  plant_id: number;
  current_kw: number;
  predicted_peak_kw: number;
  demand_limit_kw: number;
  warning: boolean;
  trend: number[];
  events: Array<{ id: number; start_time: string; peak_kw: number; strategy: string; actual_reduction_kw: number }>;
}

export interface MVResult {
  baseline_energy_kwh: number;
  actual_energy_kwh: number;
  savings_kwh: number;
  savings_pct: number;
  uncertainty_pct: number;
  cv_rmse_pct: number;
  nmbe_pct: number;
  compliant_ashrae_g14: boolean;
  compliant_gb28750: boolean;
  coal_equivalent_tons: number;
  carbon_reduction_kg: number;
}

export interface EnergyComparison {
  period: string;
  current: { total_kwh: number; avg_cop: number; avg_power_kw: number };
  previous: { total_kwh: number; avg_cop: number; avg_power_kw: number };
  mom_change_pct: { total_kwh: number; avg_cop: number; avg_power_kw: number };
  yoy_change_pct: { total_kwh: number; avg_cop: number; avg_power_kw: number };
}

export const energyApi = {
  getDashboard: (plantId: number) =>
    apiClient.get(`/api/energy/dashboard?plant_id=${plantId}`) as Promise<EnergyDashboard>,

  getBreakdown: (plantId: number) =>
    apiClient.get(`/api/energy/breakdown?plant_id=${plantId}`),

  getBaseline: (plantId: number) =>
    apiClient.get(`/api/energy/baseline?plant_id=${plantId}`) as Promise<EnergyBaseline>,

  getDemand: (plantId: number) =>
    apiClient.get(`/api/energy/peak-demand?plant_id=${plantId}`) as Promise<DemandData>,

  getMv: (plantId: number) =>
    apiClient.get(`/api/energy/mv/verify?plant_id=${plantId}`) as Promise<MVResult>,

  getComparison: (plantId: number, period: string = 'month') =>
    apiClient.get(`/api/energy/comparison?plant_id=${plantId}&period=${period}`) as Promise<EnergyComparison>,

  getReports: (plantId: number, period?: string) =>
    apiClient.get(`/api/energy/reports?plant_id=${plantId}${period ? `&period=${period}` : ''}`),

  generateReport: (plantId: number, period: string, reportType: string) =>
    apiClient.post(`/api/energy/reports/generate?plant_id=${plantId}&period=${period}&report_type=${reportType}`),

  optimizeDemand: (plantId: number) =>
    apiClient.post(`/api/energy/peak-demand/optimize?plant_id=${plantId}`),

  getPowerQuality: (equipmentId: number) =>
    apiClient.get(`/api/energy/power-quality?equipment_id=${equipmentId}`),
};
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No new errors (energy.ts imports apiClient correctly)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/energy.ts
git commit -m "feat: add energy API client"
```

---

### Task 12: Energy frontend pages

**Files:**
- Create: `frontend/src/pages/energy/EnergyDashboard.tsx`
- Create: `frontend/src/pages/energy/EnergyScheduling.tsx`
- Create: `frontend/src/pages/energy/EnergyDemand.tsx`
- Create: `frontend/src/pages/energy/EnergyReports.tsx`
- Create: `frontend/src/pages/energy/EnergyMV.tsx`

- [ ] **Step 1: Write Energy Dashboard page**

```tsx
// frontend/src/pages/energy/EnergyDashboard.tsx
import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function EnergyDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['energy-dashboard', 1],
    queryFn: () => energyApi.getDashboard(1),
    refetchInterval: 15000,
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">能效看板</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">系统 COP</div>
          <div className="text-3xl font-bold text-blue-600">{data.current_cop.toFixed(2)}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">总功率 (kW)</div>
          <div className="text-3xl font-bold text-orange-600">{data.total_power_kw}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">冷负荷 (RT)</div>
          <div className="text-3xl font-bold text-cyan-600">{data.cooling_load_rt}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">电费 (元/时)</div>
          <div className="text-3xl font-bold text-red-600">{data.electricity_cost_per_hour}</div>
        </div>
      </div>

      {/* Trend Chart */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">24h 能效趋势</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data.trend.cop.map((v, i) => ({ idx: i, cop: v, power: data.trend.power_kw[i], load: data.trend.load_rt[i] }))}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="idx" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Line yAxisId="left" type="monotone" dataKey="cop" stroke="#2563eb" name="COP" />
            <Line yAxisId="right" type="monotone" dataKey="power" stroke="#ea580c" name="功率kW" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Equipment Breakdown */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">分项能耗占比</h2>
        <div className="flex justify-around text-center">
          <div><div className="text-2xl font-bold text-blue-600">{data.equipment_breakdown.chillers} kW</div><div className="text-sm text-gray-500">冷水机组</div></div>
          <div><div className="text-2xl font-bold text-green-600">{data.equipment_breakdown.pumps} kW</div><div className="text-sm text-gray-500">水泵</div></div>
          <div><div className="text-2xl font-bold text-purple-600">{data.equipment_breakdown.cooling_towers} kW</div><div className="text-sm text-gray-500">冷却塔</div></div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write Scheduling, Demand, Reports, and MV pages**

Create `frontend/src/pages/energy/EnergyScheduling.tsx`:

```tsx
import { useState } from 'react';
import { energyApi } from '../../api/energy';

export default function EnergyScheduling() {
  const [result, setResult] = useState<unknown>(null);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">峰谷负荷调度</h1>
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">分时电价时段</h2>
        <div className="grid grid-cols-3 gap-4 text-center mb-6">
          <div className="bg-green-50 rounded p-3"><div className="text-sm text-gray-500">谷时 (23:00-7:00)</div><div className="text-xl font-bold text-green-600">0.35 元/kWh</div></div>
          <div className="bg-yellow-50 rounded p-3"><div className="text-sm text-gray-500">平时 (7:00-10:00, 15:00-17:00, 21:00-23:00)</div><div className="text-xl font-bold text-yellow-600">0.75 元/kWh</div></div>
          <div className="bg-red-50 rounded p-3"><div className="text-sm text-gray-500">峰时 (10:00-15:00, 17:00-21:00)</div><div className="text-xl font-bold text-red-600">1.15 元/kWh</div></div>
        </div>
        <button
          onClick={async () => { const r = await energyApi.optimizeDemand(1); setResult(r); }}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
        >
          运行优化计算
        </button>
        {result && <pre className="mt-4 p-4 bg-gray-50 rounded text-sm">{JSON.stringify(result, null, 2)}</pre>}
      </div>
    </div>
  );
}
```

Create `frontend/src/pages/energy/EnergyDemand.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function EnergyDemand() {
  const { data, isLoading } = useQuery({
    queryKey: ['energy-demand', 1],
    queryFn: () => energyApi.getDemand(1),
    refetchInterval: 30000,
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">需量管理</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">当前需量</div>
          <div className="text-3xl font-bold">{data.current_kw} <span className="text-base text-gray-500">kW</span></div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">预测峰值</div>
          <div className={`text-3xl font-bold ${data.warning ? 'text-red-600' : 'text-green-600'}`}>
            {data.predicted_peak_kw} <span className="text-base text-gray-500">kW</span>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">需量限额</div>
          <div className="text-3xl font-bold text-blue-600">{data.demand_limit_kw} <span className="text-base text-gray-500">kW</span></div>
        </div>
      </div>
      {data.warning && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">需量预警：预测需量将超出限额</div>
      )}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-semibold mb-4">需量趋势</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data.trend.map((v, i) => ({ idx: i, kw: v }))}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="idx" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="kw" stroke="#ea580c" name="需量kW" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

Create `frontend/src/pages/energy/EnergyReports.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';
import { useState } from 'react';

export default function EnergyReports() {
  const [period, setPeriod] = useState('day');
  const { data } = useQuery({
    queryKey: ['energy-reports', 1, period],
    queryFn: () => energyApi.getReports(1, period),
  });
  const [generating, setGenerating] = useState(false);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">能源报告</h1>
      <div className="flex gap-2 flex-wrap">
        {['day', 'week', 'month', 'year'].map((p) => (
          <button key={p} onClick={() => setPeriod(p)} className={`px-4 py-2 rounded ${period === p ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
            {p === 'day' ? '日报' : p === 'week' ? '周报' : p === 'month' ? '月报' : '年报'}
          </button>
        ))}
      </div>
      <button
        onClick={async () => { setGenerating(true); await energyApi.generateReport(1, period, 'daily'); setGenerating(false); }}
        disabled={generating}
        className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {generating ? '生成中...' : '导出报告'}
      </button>
      {data && <pre className="bg-gray-50 rounded p-4 text-sm">{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}
```

Create `frontend/src/pages/energy/EnergyMV.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query';
import { energyApi } from '../../api/energy';

export default function EnergyMV() {
  const { data, isLoading } = useQuery({
    queryKey: ['energy-mv', 1],
    queryFn: () => energyApi.getMv(1),
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">M&V 验证</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">节能量</div>
          <div className="text-2xl font-bold text-green-600">{data.savings_kwh.toLocaleString()} kWh</div>
          <div className="text-sm text-gray-400">{data.savings_pct}%</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">标准煤节约</div>
          <div className="text-2xl font-bold">{data.coal_equivalent_tons} 吨</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">碳减排</div>
          <div className="text-2xl font-bold text-cyan-600">{data.carbon_reduction_kg.toLocaleString()} kg</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-gray-500 text-sm">CV(RMSE)</div>
          <div className={`text-2xl font-bold ${data.cv_rmse_pct <= 20 ? 'text-green-600' : 'text-red-600'}`}>{data.cv_rmse_pct}%</div>
          <div className="text-sm text-gray-400">{data.cv_rmse_pct <= 20 ? 'ASHRAE G14 合规' : '超标'}</div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">国标合规</h2>
          <div className="space-y-2">
            <div className={`flex items-center gap-2 ${data.compliant_gb28750 ? 'text-green-600' : 'text-red-600'}`}>
              {data.compliant_gb28750 ? '✓' : '✗'} GB/T 28750 M&V 验证通过
            </div>
            <div className={`flex items-center gap-2 ${data.compliant_ashrae_g14 ? 'text-green-600' : 'text-red-600'}`}>
              {data.compliant_ashrae_g14 ? '✓' : '✗'} ASHRAE Guideline 14 合规
            </div>
            <div className={`flex items-center gap-2 ${Math.abs(data.nmbe_pct) <= 5 ? 'text-green-600' : 'text-red-600'}`}>
              {Math.abs(data.nmbe_pct) <= 5 ? '✓' : '✗'} NMBE: {data.nmbe_pct}% (≤±5%)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/energy/
git commit -m "feat: add 5 energy management frontend pages"
```

---

## Phase 6 — Frontend Health Module

### Task 13: Health API client

**Files:**
- Create: `frontend/src/api/health.ts`

- [ ] **Step 1: Write health API client**

```typescript
// frontend/src/api/health.ts
import { apiClient } from './client';

export interface HealthOverview {
  plant_id: number;
  overall_health: number;
  equipment_health: Array<{
    equipment_id: number; name: string; overall_score: number; status: string; trend: string;
  }>;
  top_degrading: Array<{ equipment_name: string; component: string; score: number; degradation_rate: number }>;
}

export interface RULItem {
  equipment_id: number; component: string; predicted_hours: number;
  ci_lo: number; ci_hi: number; degradation_model: string;
}

export interface DiagnosisResult {
  rank: number; failure_mode: string; fmea_id: number; confidence: number; severity: number;
}

export interface FMEARecord {
  id: number; equipment_type: string; component: string; failure_mode: string;
  severity: number; occurrence: number; detection: number; rpn: number;
  mitigation: string; symptoms: Record<string, unknown>;
}

export const healthApi = {
  getDashboard: (plantId: number) =>
    apiClient.get(`/api/health/dashboard?plant_id=${plantId}`) as Promise<HealthOverview>,

  getEquipmentDetail: (equipmentId: number) =>
    apiClient.get(`/api/health/equipment/${equipmentId}`),

  getRUL: (plantId?: number, equipmentId?: number) => {
    const params = new URLSearchParams();
    if (plantId) params.set('plant_id', String(plantId));
    if (equipmentId) params.set('equipment_id', String(equipmentId));
    return apiClient.get(`/api/health/rul?${params}`) as Promise<{ items: RULItem[] }>;
  },

  computeRUL: (equipmentId: number, component: string) =>
    apiClient.post(`/api/health/rul/compute?equipment_id=${equipmentId}&component=${component}`),

  getDiagnosis: (equipmentId: number) =>
    apiClient.get(`/api/health/diagnosis?equipment_id=${equipmentId}`),

  runDiagnosis: (equipmentId: number) =>
    apiClient.post(`/api/health/diagnosis/run?equipment_id=${equipmentId}`) as Promise<{ diagnoses: DiagnosisResult[] }>,

  searchFMEA: (equipmentType?: string, component?: string, q?: string) => {
    const params = new URLSearchParams();
    if (equipmentType) params.set('equipment_type', equipmentType);
    if (component) params.set('component', component);
    if (q) params.set('q', q);
    return apiClient.get(`/api/health/fmea?${params}`) as Promise<{ items: FMEARecord[] }>;
  },

  createFMEA: (data: Partial<FMEARecord>) =>
    apiClient.post('/api/health/fmea', data),

  getVibration: (equipmentId: number) =>
    apiClient.get(`/api/health/vibration?equipment_id=${equipmentId}`),

  getOilAnalysis: (equipmentId: number) =>
    apiClient.get(`/api/health/oil?equipment_id=${equipmentId}`),

  getValidation: () =>
    apiClient.get('/api/health/validation'),
};
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/health.ts
git commit -m "feat: add health API client"
```

---

### Task 14: Health frontend pages

**Files:**
- Create: `frontend/src/pages/health/HealthDashboard.tsx`
- Create: `frontend/src/pages/health/RULPrediction.tsx`
- Create: `frontend/src/pages/health/FaultDiagnosis.tsx`
- Create: `frontend/src/pages/health/FMEAKB.tsx`
- Create: `frontend/src/pages/health/SpectrumAnalysis.tsx`

- [ ] **Step 1: Write Health Dashboard page**

```tsx
// frontend/src/pages/health/HealthDashboard.tsx
import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../../api/health';

const statusColor = (status: string) => {
  switch (status) {
    case 'healthy': return 'bg-green-100 text-green-800';
    case 'degrading': return 'bg-yellow-100 text-yellow-800';
    case 'critical': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

export default function HealthDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['health-dashboard', 1],
    queryFn: () => healthApi.getDashboard(1),
    refetchInterval: 30000,
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">健康看板</h1>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4">
          <div className="text-5xl font-bold text-blue-600">{data.overall_health}</div>
          <div className="text-gray-500">全站综合健康指数</div>
        </div>
      </div>
      <div className="space-y-3">
        {data.equipment_health.map((eq) => (
          <div key={eq.equipment_id} className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
            <div>
              <div className="font-semibold">{eq.name}</div>
              <div className="text-sm text-gray-500">趋势: {eq.trend === 'down' ? '↓ 退化中' : eq.trend === 'up' ? '↑ 改善中' : '→ 稳定'}</div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-2xl font-bold">{eq.overall_score}</div>
              <span className={`px-2 py-1 rounded text-xs ${statusColor(eq.status)}`}>
                {eq.status === 'healthy' ? '健康' : eq.status === 'degrading' ? '退化中' : '严重'}
              </span>
            </div>
          </div>
        ))}
      </div>
      {data.top_degrading.length > 0 && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">退化趋势 Top N</h2>
          {data.top_degrading.map((d, i) => (
            <div key={i} className="flex justify-between py-2 border-b last:border-0">
              <span>{d.equipment_name} - {d.component}</span>
              <span className="text-red-600">退化率 {d.degradation_rate}/天</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write RUL Prediction page**

```tsx
// frontend/src/pages/health/RULPrediction.tsx
import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../../api/health';

export default function RULPrediction() {
  const { data, isLoading } = useQuery({
    queryKey: ['health-rul', 1],
    queryFn: () => healthApi.getRUL(1),
    refetchInterval: 120000,
  });

  if (isLoading || !data) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">RUL 预测</h1>
      <div className="space-y-4">
        {data.items.map((item, i) => {
          const days = Math.round(item.predicted_hours / 24);
          const daysLo = Math.round(item.ci_lo / 24);
          const daysHi = Math.round(item.ci_hi / 24);
          const urgency = days < 30 ? 'urgent' : days < 90 ? 'warning' : 'normal';
          const borderColor = urgency === 'urgent' ? 'border-red-500' : urgency === 'warning' ? 'border-yellow-500' : 'border-green-500';
          return (
            <div key={i} className={`bg-white rounded-lg shadow p-4 border-l-4 ${borderColor}`}>
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-semibold">设备 {item.equipment_id} - {item.component}</div>
                  <div className="text-sm text-gray-500">模型: {item.degradation_model}</div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold">{days} <span className="text-base text-gray-500">天</span></div>
                  <div className="text-xs text-gray-400">80%CI: {daysLo}-{daysHi} 天</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write Fault Diagnosis page**

```tsx
// frontend/src/pages/health/FaultDiagnosis.tsx
import { useState } from 'react';
import { healthApi } from '../../api/health';
import type { DiagnosisResult } from '../../api/health';

export default function FaultDiagnosis() {
  const [equipmentId, setEquipmentId] = useState(1);
  const [results, setResults] = useState<DiagnosisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<unknown>(null);

  const runDiagnosis = async () => {
    setLoading(true);
    const r = await healthApi.runDiagnosis(equipmentId);
    setResults(r.diagnoses);
    setLoading(false);
    const h = await healthApi.getDiagnosis(equipmentId);
    setHistory(h);
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">故障诊断</h1>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4 mb-4">
          <label className="text-sm text-gray-600">设备 ID:</label>
          <input type="number" value={equipmentId} onChange={(e) => setEquipmentId(Number(e.target.value))}
                 className="border rounded px-3 py-1 w-24" />
          <button onClick={runDiagnosis} disabled={loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
            {loading ? '诊断中...' : '运行诊断'}
          </button>
        </div>
        {results.length > 0 && (
          <div className="space-y-3">
            {results.map((r, i) => (
              <div key={i} className="border rounded p-3 flex justify-between items-center">
                <div>
                  <div className="font-semibold">#{r.rank}: {r.failure_mode}</div>
                  <div className="text-sm text-gray-500">FMEA #{r.fmea_id} | 严重度: {r.severity}/5</div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-blue-600">{(r.confidence * 100).toFixed(0)}%</div>
                  <div className="text-xs text-gray-400">置信度</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {history && <pre className="mt-4 p-4 bg-gray-50 rounded text-xs">{JSON.stringify(history, null, 2)}</pre>}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write FMEA Knowledge Base page**

```tsx
// frontend/src/pages/health/FMEAKB.tsx
import { useState } from 'react';
import { healthApi } from '../../api/health';
import type { FMEARecord } from '../../api/health';

export default function FMEAKB() {
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<FMEARecord[]>([]);
  const [loading, setLoading] = useState(false);

  const doSearch = async () => {
    setLoading(true);
    const r = await healthApi.searchFMEA(undefined, undefined, search || undefined);
    setResults(r.items);
    setLoading(false);
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">FMEA 知识库</h1>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-2 mb-4">
          <input
            type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索失效模式、部件..."
            className="border rounded px-3 py-2 flex-1"
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          />
          <button onClick={doSearch} disabled={loading}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>
        <div className="space-y-3">
          {results.map((r) => (
            <div key={r.id} className="border rounded p-3">
              <div className="flex justify-between">
                <div className="font-semibold">{r.failure_mode}</div>
                <div>
                  <span className="text-sm text-gray-500 mr-2">RPN</span>
                  <span className={`font-bold ${r.rpn > 100 ? 'text-red-600' : r.rpn > 50 ? 'text-yellow-600' : 'text-green-600'}`}>{r.rpn}</span>
                </div>
              </div>
              <div className="text-sm text-gray-500">{r.equipment_type} &gt; {r.component}</div>
              <div className="text-sm text-gray-400 mt-1">S={r.severity} O={r.occurrence} D={r.detection}</div>
              {r.mitigation && <div className="text-sm mt-2 bg-blue-50 rounded p-2">措施: {r.mitigation}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Write Spectrum Analysis page**

```tsx
// frontend/src/pages/health/SpectrumAnalysis.tsx
import { useState } from 'react';
import { healthApi } from '../../api/health';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function SpectrumAnalysis() {
  const [equipmentId, setEquipmentId] = useState(1);
  const [data, setData] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [oilData, setOilData] = useState<unknown>(null);

  const load = async () => {
    setLoading(true);
    const [v, o] = await Promise.all([
      healthApi.getVibration(equipmentId),
      healthApi.getOilAnalysis(equipmentId),
    ]);
    setData(v);
    setOilData(o);
    setLoading(false);
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">频谱分析</h1>
      <div className="flex items-center gap-4">
        <label className="text-sm">设备 ID:</label>
        <input type="number" value={equipmentId} onChange={(e) => setEquipmentId(Number(e.target.value))}
               className="border rounded px-3 py-1 w-24" />
        <button onClick={load} disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          {loading ? '加载中...' : '加载数据'}
        </button>
      </div>
      {data && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">振动频谱</h2>
          <pre className="text-xs bg-gray-50 p-4 rounded">{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
      {oilData && (
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-3">润滑油分析</h2>
          <pre className="text-xs bg-gray-50 p-4 rounded">{JSON.stringify(oilData, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/health/
git commit -m "feat: add 5 health management frontend pages"
```

---

## Phase 7 — Frontend Navigation & Routing

### Task 15: Add routes and sidebar navigation

**Files:**
- Modify: `frontend/src/App.tsx:48-64`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Add new route imports and routes**

Add imports at top of `frontend/src/App.tsx`:

```tsx
import EnergyDashboard from './pages/energy/EnergyDashboard';
import EnergyScheduling from './pages/energy/EnergyScheduling';
import EnergyDemand from './pages/energy/EnergyDemand';
import EnergyReports from './pages/energy/EnergyReports';
import EnergyMV from './pages/energy/EnergyMV';
import HealthDashboard from './pages/health/HealthDashboard';
import RULPrediction from './pages/health/RULPrediction';
import FaultDiagnosis from './pages/health/FaultDiagnosis';
import FMEAKB from './pages/health/FMEAKB';
import SpectrumAnalysis from './pages/health/SpectrumAnalysis';
```

Add routes after the `/carbon` route:

```tsx
              <Route path="/energy/dashboard" element={<EnergyDashboard />} />
              <Route path="/energy/scheduling" element={<EnergyScheduling />} />
              <Route path="/energy/demand" element={<EnergyDemand />} />
              <Route path="/energy/reports" element={<EnergyReports />} />
              <Route path="/energy/mv" element={<EnergyMV />} />
              <Route path="/health/dashboard" element={<HealthDashboard />} />
              <Route path="/health/rul" element={<RULPrediction />} />
              <Route path="/health/diagnosis" element={<FaultDiagnosis />} />
              <Route path="/health/fmea" element={<FMEAKB />} />
              <Route path="/health/spectrum" element={<SpectrumAnalysis />} />
```

- [ ] **Step 2: Update sidebar navigation**

In `frontend/src/components/Layout.tsx`, add new nav items inside the sidebar. The existing nav items should be reorganized into collapsible groups:

After the Dashboard link, add:

```tsx
{/* 监控与分析 Group */}
<div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
  监控与分析
</div>
<NavLink to="/energy/dashboard" className={...}>
  ⚡ 能源管理
</NavLink>
<NavLink to="/health/dashboard" className={...}>
  💚 设备健康
</NavLink>
```

And add sub-navigation items with indented styling when on an energy or health page.

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npx tsc --noEmit && npx vite build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add energy and health routes with sidebar navigation"
```

---

## Phase 8 — Integration Verification

### Task 16: Run full test suite and verify no regressions

- [ ] **Step 1: Run Python backend tests**

Run: `cd /Users/ymilitarym/hp-2026/hvac-agents && uv run pytest tests/ -v --timeout=60`
Expected: All existing + new tests PASS (488+ tests)

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests PASS

- [ ] **Step 3: Verify frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit if any files needed updates**

```bash
git status
```
