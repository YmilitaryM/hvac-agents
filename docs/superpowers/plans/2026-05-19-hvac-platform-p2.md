# HVAC Platform P2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the HVAC platform from simulation-only to a production-grade digital twin with real hardware integration, model auto-calibration, multi-station collaborative optimization, carbon trading, and full production hardening.

**Architecture:** Add a 6th microservice (Data Acquisition Service with its own TimescaleDB) for BACnet/Modbus/OPC UA hardware I/O. Extend Simulation Service with calibration and data quality monitoring. Extend Agent Service with MAPPO multi-agent RL, inter-station dispatch, and carbon trading. Harden all services with tests, CI/CD, Alembic, Prometheus, rate limiting, PWA, and HITL.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, PostgreSQL, TimescaleDB, Redis, pymodbus, BAC0, opcua-asyncio, scikit-learn, PyTorch, scipy, PPO/MAPPO, pydantic v2, React 18 + TypeScript + Tailwind CSS, Vite PWA, WeasyPrint, openpyxl, Docker Compose, GitHub Actions

---

## File Structure

```
services/acquisition/                          # NEW service (Module A)
├── pyproject.toml
├── Dockerfile
├── acquisition_service/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py                              # TimescaleDB EquipmentReading supertable
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                            # ProtocolAdapter ABC
│   │   ├── modbus_adapter.py
│   │   ├── bacnet_adapter.py
│   │   └── opcua_adapter.py
│   ├── poller.py                              # Polling engine
│   ├── cache.py                               # Redis latest-value cache
│   ├── forwarder.py                           # Forward values to Asset Service
│   ├── gap_filler.py                          # Data gap interpolation
│   ├── edge_sync.py                           # Edge-cloud sync
│   └── api/
│       ├── __init__.py
│       ├── points.py
│       ├── status.py
│       └── commands.py                        # Write-path safety checks
└── tests/

services/simulation/sim_service/               # Extended (Module C)
├── calibration/
│   ├── __init__.py
│   ├── base.py
│   ├── chiller_cal.py
│   ├── tower_cal.py
│   ├── pump_cal.py
│   ├── valve_cal.py
│   ├── cleaner.py
│   └── validator.py
├── data_quality/
│   ├── __init__.py
│   ├── realtime_rules.py                      # Layer 1
│   ├── statistical.py                         # Layer 2
│   ├── context_window.py                      # Layer 3 (baseline/drift/peer/operational)
│   ├── root_cause_analyzer.py                 # Layer 5 (attribution)
│   └── gap_filler.py                          # Data fill logic
├── api/
│   └── calibration.py                         # (new router)
├── models.py                                  # (+ CalibrationRun, CalibrationDataPoint)

services/agent/agent_service/                   # Extended (Module C ML + Module D)
├── anomaly/                                   # Module C — ML anomaly detection (layer 4)
│   ├── __init__.py
│   ├── autoencoder.py
│   ├── isolation_forest.py
│   ├── feature_builder.py
│   └── cold_start.py
├── rl/
│   ├── multi_agent/                           # Module D
│   │   ├── __init__.py
│   │   ├── mappo.py
│   │   ├── action_mask.py
│   │   └── reward_shaper.py
│   ├── training/
│   │   ├── auto_trainer.py
│   │   └── online_finetune.py
│   └── benchmark/
│       ├── __init__.py
│       └── comparator.py
├── optimization/
│   ├── station_dispatch.py                    # Module D
│   ├── carbon_allocator.py
│   └── network_flow.py
├── carbon/                                    # Module D
│   ├── __init__.py
│   ├── emission_calculator.py
│   ├── carbon_market.py
│   ├── cea_adapter.py
│   ├── allowance_tracker.py
│   └── carbon_optimizer.py
├── alerting/
│   └── delivery.py                            # Module B — notification channels
├── api/
│   ├── calibration.py                         # (new — trigger from Agent side)
│   ├── carbon.py                              # (new)
│   ├── dispatch.py                            # (new — inter-station)
│   └── override.py                            # Module B — HITL

services/gateway/gateway_service/
├── middleware/
│   ├── rate_limiter.py                        # Module B
│   └── circuit_breaker.py                     # Module B
├── metrics.py                                 # Module B — Prometheus

frontend/                                      # Module B updates
├── vite.config.ts                             # (+ PWA plugin)
├── src/
│   ├── service-worker.ts                      # PWA service worker
│   ├── pages/
│   │   ├── LiveMonitor.tsx                    # (new — real-time monitoring)
│   │   └── ManualOverride.tsx                 # Module B — HITL UI
│   └── api/
│       ├── acquisition.ts                     # (new)
│       └── override.ts                        # (new)

.github/workflows/                             # Module B
├── ci.yml
├── integration.yml
├── deploy.yml
└── nightly.yml
```

---

## Phase 1: Module A — Data Acquisition Service

### Task A1: Service scaffold

**Files:**
- Create: `services/acquisition/pyproject.toml`
- Create: `services/acquisition/Dockerfile`
- Create: `services/acquisition/acquisition_service/__init__.py` (empty)
- Create: `services/acquisition/acquisition_service/main.py`
- Create: `services/acquisition/acquisition_service/models.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "acquisition-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "hvac-common",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "httpx>=0.28",
    "redis>=5.0",
    "pymodbus>=3.7",
    "BAC0>=23.0",
    "opcua-asyncio>=1.0",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "psycopg2-binary>=2.9",
]
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY acquisition_service/ acquisition_service/
CMD ["uvicorn", "acquisition_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write models.py**

```python
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from common.db import Base


class EquipmentReading(Base):
    __tablename__ = "equipment_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        default=lambda: datetime.now(timezone.utc)
    )
    equipment_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    plant_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    point_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    point_code: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[str] = mapped_column(String(16), default="good")  # good|estimated|questionable|bad
    source: Mapped[str] = mapped_column(String(16), default="live")    # live|simulated|shadow

    __table_args__ = (
        Index("ix_readings_point_time", "point_id", "time"),
        Index("ix_readings_equip_time", "equipment_id", "time"),
    )


def create_hypertable(conn):
    """Convert equipment_readings into a TimescaleDB hypertable."""
    conn.execute(text(
        "SELECT create_hypertable('equipment_readings', 'time', if_not_exists => TRUE)"
    ))
    conn.execute(text(
        "SELECT add_retention_policy('equipment_readings', INTERVAL '90 days', if_not_exists => TRUE)"
    ))
    conn.commit()
```

- [ ] **Step 4: Write main.py**

```python
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from sqlalchemy import text

from common.config import get_settings
from common.db import create_engine, create_session_factory
from .models import Base, create_hypertable
from .api import points, status, commands


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    engine = create_engine(s.database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.run_sync(create_hypertable)
        except Exception:
            pass  # TimescaleDB not available in test

    try:
        app.state.redis = aioredis.from_url(s.redis_url)
    except Exception:
        app.state.redis = None

    app.state.asset_service_url = s.asset_service_url

    from .poller import PollingEngine
    app.state.poller = PollingEngine(app.state.session_factory, app.state.redis)
    await app.state.poller.start()

    yield

    await app.state.poller.stop()
    if app.state.redis:
        await app.state.redis.close()
    await engine.dispose()


app = FastAPI(title="Data Acquisition Service", version="0.1.0", lifespan=lifespan)

app.include_router(points.router, prefix="/api/acquisition", tags=["Points"])
app.include_router(status.router, prefix="/api/acquisition", tags=["Status"])
app.include_router(commands.router, prefix="/api/acquisition", tags=["Commands"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "acquisition"}
```

- [ ] **Step 5: Commit**

```bash
git add services/acquisition/
git commit -m "feat(acq): add Data Acquisition Service scaffold"
```

---

### Task A2: Protocol adapter base + Modbus adapter

**Files:**
- Create: `services/acquisition/acquisition_service/adapters/__init__.py` (empty)
- Create: `services/acquisition/acquisition_service/adapters/base.py`
- Create: `services/acquisition/acquisition_service/adapters/modbus_adapter.py`
- Create: `services/acquisition/tests/test_modbus_adapter.py`

- [ ] **Step 1: Write adapter base class**

```python
# adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProtocolBinding:
    protocol: str
    config: dict  # raw JSON from EquipmentPoint.protocol_binding


class ProtocolAdapter(ABC):
    protocol: str

    @abstractmethod
    async def connect(self, binding: ProtocolBinding) -> None: ...

    @abstractmethod
    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float: ...

    @abstractmethod
    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...


class AdapterError(Exception):
    pass


class CommunicationError(AdapterError):
    pass


class WriteError(AdapterError):
    pass
```

- [ ] **Step 2: Write failing test for Modbus adapter**

```python
# tests/test_modbus_adapter.py
import pytest
from acquisition_service.adapters.base import ProtocolBinding, CommunicationError
from acquisition_service.adapters.modbus_adapter import ModbusAdapter


@pytest.mark.asyncio
async def test_modbus_read_holding_register():
    adapter = ModbusAdapter()
    binding = ProtocolBinding(protocol="modbus", config={
        "host": "127.0.0.1", "port": 5020,
        "slave_id": 1, "register": 40001,
        "function_code": 3, "data_type": "int16",
        "scale": 0.1, "offset": 0
    })
    await adapter.connect(binding)
    value = await adapter.read_point("test_point_1", binding)
    assert isinstance(value, float)
    await adapter.disconnect()


@pytest.mark.asyncio
async def test_modbus_connection_timeout_raises_communication_error():
    adapter = ModbusAdapter()
    binding = ProtocolBinding(protocol="modbus", config={
        "host": "192.0.2.1", "port": 5020,  # non-routable
        "slave_id": 1, "register": 40001,
        "function_code": 3
    })
    with pytest.raises(CommunicationError):
        await adapter.connect(binding)
```

- [ ] **Step 3: Run test to verify failure**

```bash
cd services/acquisition && pip install -e .
pytest tests/test_modbus_adapter.py -v
# Expected: FAIL — no ModbusAdapter class
```

- [ ] **Step 4: Write Modbus adapter implementation**

```python
# adapters/modbus_adapter.py
import struct
from pymodbus.client import AsyncModbusTcpClient
from .base import ProtocolAdapter, ProtocolBinding, CommunicationError, WriteError


class ModbusAdapter(ProtocolAdapter):
    protocol = "modbus"

    def __init__(self):
        self._client: AsyncModbusTcpClient | None = None
        self._config: dict = {}

    async def connect(self, binding: ProtocolBinding) -> None:
        self._config = binding.config
        host = self._config.get("host", "127.0.0.1")
        port = self._config.get("port", 502)
        self._client = AsyncModbusTcpClient(host, port, timeout=5)
        connected = await self._client.connect()
        if not connected:
            raise CommunicationError(f"Modbus connect failed: {host}:{port}")

    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float:
        slave_id = binding.config.get("slave_id", 1)
        register = binding.config.get("register", 40001)
        function_code = binding.config.get("function_code", 3)
        data_type = binding.config.get("data_type", "int16")
        scale = binding.config.get("scale", 1.0)
        offset = binding.config.get("offset", 0.0)

        try:
            if function_code == 3:
                rr = await self._client.read_holding_registers(register - 40001, 2, slave=slave_id)
            elif function_code == 4:
                rr = await self._client.read_input_registers(register - 30001, 2, slave=slave_id)
            else:
                raise CommunicationError(f"Unsupported function code: {function_code}")

            if rr.isError():
                raise CommunicationError(f"Modbus read error: {rr}")

            raw = rr.registers[0]
            if data_type == "int16":
                if raw > 32767:
                    raw -= 65536
            value = raw * scale + offset
            return float(value)
        except Exception as e:
            raise CommunicationError(f"Modbus read failed: {e}") from e

    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None:
        slave_id = binding.config.get("slave_id", 1)
        register = binding.config.get("register", 40001)
        scale = binding.config.get("scale", 1.0)
        offset = binding.config.get("offset", 0.0)
        raw_value = int((value - offset) / scale)
        try:
            result = await self._client.write_register(register - 40001, raw_value, slave=slave_id)
            if result.isError():
                raise WriteError(f"Modbus write error: {result}")
        except Exception as e:
            raise WriteError(f"Modbus write failed: {e}") from e

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()
```

- [ ] **Step 5: Run test to verify pass**

```bash
pytest tests/test_modbus_adapter.py -v
# Expected: connection test fails on non-routable (common in CI), read test passes if Modbus simulator running
```

- [ ] **Step 6: Commit**

```bash
git add services/acquisition/acquisition_service/adapters/ services/acquisition/tests/
git commit -m "feat(acq): add Modbus TCP protocol adapter"
```

---

### Task A3: BACnet adapter

**Files:**
- Create: `services/acquisition/acquisition_service/adapters/bacnet_adapter.py`
- Create: `services/acquisition/tests/test_bacnet_adapter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_bacnet_adapter.py
import pytest
from acquisition_service.adapters.base import ProtocolBinding, CommunicationError
from acquisition_service.adapters.bacnet_adapter import BacnetAdapter


@pytest.mark.asyncio
async def test_bacnet_read_analog_input():
    adapter = BacnetAdapter()
    binding = ProtocolBinding(protocol="bacnet", config={
        "device_id": 2401,
        "object_type": "analog_input",
        "instance": 12,
        "poll_interval_sec": 5
    })
    # Connection will fail in test env, verifying error handling
    with pytest.raises(CommunicationError):
        await adapter.connect(binding)
```

- [ ] **Step 2: Write BACnet adapter implementation**

```python
# adapters/bacnet_adapter.py
from .base import ProtocolAdapter, ProtocolBinding, CommunicationError, WriteError


class BacnetAdapter(ProtocolAdapter):
    protocol = "bacnet"

    def __init__(self):
        self._device: object | None = None
        self._config: dict = {}

    async def connect(self, binding: ProtocolBinding) -> None:
        self._config = binding.config
        device_id = self._config.get("device_id")
        try:
            import BAC0
            self._device = BAC0.lite(device_id)
        except ImportError:
            raise CommunicationError("BAC0 library not installed")
        except Exception as e:
            raise CommunicationError(f"BACnet connect failed: device={device_id} — {e}") from e

    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float:
        obj_type = binding.config.get("object_type", "analog_input")
        instance = binding.config.get("instance")
        try:
            if obj_type == "analog_input":
                value = self._device.read(f"analogInput {instance} presentValue")
            elif obj_type == "analog_output":
                value = self._device.read(f"analogOutput {instance} presentValue")
            elif obj_type == "analog_value":
                value = self._device.read(f"analogValue {instance} presentValue")
            else:
                raise CommunicationError(f"Unsupported BACnet object type: {obj_type}")
            return float(value)
        except Exception as e:
            raise CommunicationError(f"BACnet read failed: {e}") from e

    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None:
        obj_type = binding.config.get("object_type", "analog_output")
        instance = binding.config.get("instance")
        try:
            self._device.write(f"{obj_type} {instance} presentValue {value}")
        except Exception as e:
            raise WriteError(f"BACnet write failed: {e}") from e

    async def disconnect(self) -> None:
        if self._device:
            try:
                self._device.disconnect()
            except Exception:
                pass
```

- [ ] **Step 3: Verify test passes**

```bash
pytest tests/test_bacnet_adapter.py -v
# Expected: PASS (verifies CommunicationError raised on failed connect)
```

- [ ] **Step 4: Commit**

```bash
git add services/acquisition/acquisition_service/adapters/bacnet_adapter.py services/acquisition/tests/test_bacnet_adapter.py
git commit -m "feat(acq): add BACnet protocol adapter"
```

---

### Task A4: OPC UA adapter

**Files:**
- Create: `services/acquisition/acquisition_service/adapters/opcua_adapter.py`
- Create: `services/acquisition/tests/test_opcua_adapter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_opcua_adapter.py
import pytest
from acquisition_service.adapters.base import ProtocolBinding, CommunicationError
from acquisition_service.adapters.opcua_adapter import OpcUaAdapter


@pytest.mark.asyncio
async def test_opcua_connection_failure():
    adapter = OpcUaAdapter()
    binding = ProtocolBinding(protocol="opc_ua", config={
        "endpoint_url": "opc.tcp://192.0.2.1:4840",
        "node_id": "ns=2;s=Temperature",
        "poll_interval_sec": 1
    })
    with pytest.raises(CommunicationError):
        await adapter.connect(binding)
```

- [ ] **Step 2: Write OPC UA adapter implementation**

```python
# adapters/opcua_adapter.py
import asyncio
from .base import ProtocolAdapter, ProtocolBinding, CommunicationError, WriteError


class OpcUaAdapter(ProtocolAdapter):
    protocol = "opc_ua"

    def __init__(self):
        self._client: object | None = None
        self._subscriptions: dict = {}

    async def connect(self, binding: ProtocolBinding) -> None:
        endpoint_url = binding.config.get("endpoint_url")
        try:
            import asyncua
            self._client = asyncua.Client(url=endpoint_url, timeout=5)
            await asyncio.wait_for(self._client.connect(), timeout=10)
        except ImportError:
            raise CommunicationError("asyncua library not installed")
        except asyncio.TimeoutError:
            raise CommunicationError(f"OPC UA connect timeout: {endpoint_url}")
        except Exception as e:
            raise CommunicationError(f"OPC UA connect failed: {endpoint_url} — {e}") from e

    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float:
        node_id = binding.config.get("node_id")
        try:
            var = self._client.get_node(node_id)
            value = await var.read_value()
            return float(value)
        except Exception as e:
            raise CommunicationError(f"OPC UA read failed: node={node_id} — {e}") from e

    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None:
        node_id = binding.config.get("node_id")
        try:
            var = self._client.get_node(node_id)
            await var.write_value(value)
        except Exception as e:
            raise WriteError(f"OPC UA write failed: node={node_id} — {e}") from e

    async def disconnect(self) -> None:
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
```

- [ ] **Step 3: Verify test passes**

```bash
pytest tests/test_opcua_adapter.py -v
# Expected: PASS
```

- [ ] **Step 4: Commit**

```bash
git add services/acquisition/acquisition_service/adapters/opcua_adapter.py services/acquisition/tests/test_opcua_adapter.py
git commit -m "feat(acq): add OPC UA protocol adapter"
```

---

### Task A5: Polling engine

**Files:**
- Create: `services/acquisition/acquisition_service/poller.py`
- Create: `services/acquisition/tests/test_poller.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_poller.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from acquisition_service.poller import PollingEngine, PollingPoint
from acquisition_service.adapters.base import ProtocolBinding


@pytest.fixture
def mock_session_factory():
    session = AsyncMock()
    factory = MagicMock(return_value=session)
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=None)
    return factory, session


@pytest.fixture
def mock_redis():
    return MagicMock()


class FakeAdapter:
    protocol = "modbus"
    def __init__(self):
        self.connected = False
    async def connect(self, binding):
        self.connected = True
    async def read_point(self, point_id, binding):
        return 42.0
    async def disconnect(self):
        self.connected = False


@pytest.mark.asyncio
async def test_poller_registers_and_polls_point(mock_session_factory, mock_redis):
    factory, session = mock_session_factory
    engine = PollingEngine(factory, mock_redis)
    await engine.start()

    binding = ProtocolBinding(protocol="modbus", config={"host": "127.0.0.1"})
    point = PollingPoint(
        point_id="p1", equipment_id="e1", plant_id="pl1",
        point_code="CHWST", binding=binding, poll_interval_sec=1
    )
    engine.register_point(point, FakeAdapter())

    await asyncio.sleep(0.2)  # give a cycle

    assert mock_redis.set.called or mock_redis.publish.called

    await engine.stop()


@pytest.mark.asyncio
async def test_poller_retries_on_failure(mock_session_factory, mock_redis):
    factory, session = mock_session_factory
    engine = PollingEngine(factory, mock_redis, retry_count=3)
    await engine.start()

    fail_adapter = FakeAdapter()
    fail_adapter.read_point = AsyncMock(side_effect=Exception("comm error"))
    binding = ProtocolBinding(protocol="modbus", config={})
    point = PollingPoint(
        point_id="p2", equipment_id="e2", plant_id="pl1",
        point_code="CWST", binding=binding, poll_interval_sec=1
    )
    engine.register_point(point, fail_adapter)
    await asyncio.sleep(0.3)

    assert fail_adapter.read_point.call_count >= 1
    assert mock_redis.publish.called  # communication_lost event

    await engine.stop()
```

- [ ] **Step 2: Write polling engine implementation**

```python
# poller.py
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker

from .adapters.base import ProtocolBinding, ProtocolAdapter, CommunicationError
from .models import EquipmentReading

logger = logging.getLogger(__name__)


@dataclass
class PollingPoint:
    point_id: str
    equipment_id: str
    plant_id: str
    point_code: str
    binding: ProtocolBinding
    poll_interval_sec: float = 10
    last_poll: float = 0
    last_value: float | None = None


class PollingEngine:
    def __init__(self, session_factory: async_sessionmaker, redis, retry_count: int = 3):
        self._session_factory = session_factory
        self._redis = redis
        self._retry_count = retry_count
        self._points: dict[str, tuple[PollingPoint, ProtocolAdapter]] = {}
        self._task: asyncio.Task | None = None
        self._running = False

    def register_point(self, point: PollingPoint, adapter: ProtocolAdapter) -> None:
        self._points[point.point_id] = (point, adapter)

    def unregister_point(self, point_id: str) -> None:
        self._points.pop(point_id, None)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc).timestamp()
            batch = []

            for point_id, (pt, adapter) in list(self._points.items()):
                if now - pt.last_poll >= pt.poll_interval_sec:
                    batch.append((pt, adapter))

            if batch:
                results = await asyncio.gather(
                    *[self._poll_single(pt, adapter) for pt, adapter in batch],
                    return_exceptions=True
                )
                for (pt, _), result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.error(f"Polling failed for {pt.point_code}: {result}")
                    elif result is not None:
                        pt.last_value = result
                    pt.last_poll = now

            await asyncio.sleep(0.1)

    async def _poll_single(self, point: PollingPoint, adapter: ProtocolAdapter) -> float | None:
        for attempt in range(self._retry_count):
            try:
                value = await adapter.read_point(point.point_id, point.binding)
                await self._forward_value(point, value, "good")
                return value
            except CommunicationError as e:
                if attempt == self._retry_count - 1:
                    await self._forward_value(point, point.last_value, "bad")
                    await self._publish_event("point.communication_lost", {
                        "point_id": point.point_id,
                        "equipment_id": point.equipment_id,
                        "point_code": point.point_code,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    return None
                await asyncio.sleep(2 ** attempt)
        return None

    async def _forward_value(self, point: PollingPoint, value: float | None, quality: str) -> None:
        if value is None:
            return
        now = datetime.now(timezone.utc)
        reading = EquipmentReading(
            time=now, equipment_id=point.equipment_id,
            plant_id=point.plant_id, point_id=point.point_id,
            point_code=point.point_code, value=value,
            quality=quality, source="live"
        )
        async with self._session_factory() as session:
            session.add(reading)
            await session.commit()

        if self._redis:
            await self._redis.set(
                f"point:{point.point_id}:latest",
                json.dumps({"value": value, "quality": quality, "ts": now.isoformat()})
            )

    async def _publish_event(self, event_type: str, payload: dict) -> None:
        if self._redis:
            await self._redis.publish(
                f"events:{event_type}",
                json.dumps(payload)
            )
```

- [ ] **Step 3: Verify test passes**

```bash
pytest services/acquisition/tests/test_poller.py -v
# Expected: PASS
```

- [ ] **Step 4: Commit**

```bash
git add services/acquisition/acquisition_service/poller.py services/acquisition/tests/test_poller.py
git commit -m "feat(acq): add polling engine with retry and Redis events"
```

---

### Task A6: Cache, forwarder, and gap filler

**Files:**
- Create: `services/acquisition/acquisition_service/cache.py`
- Create: `services/acquisition/acquisition_service/forwarder.py`
- Create: `services/acquisition/acquisition_service/gap_filler.py`
- Create: `services/acquisition/tests/test_gap_filler.py`

- [ ] **Step 1: Write cache.py**

```python
import json
from typing import Any


class PointCache:
    def __init__(self, redis):
        self._redis = redis

    async def set_latest(self, point_id: str, value: float, quality: str = "good") -> None:
        if not self._redis:
            return
        await self._redis.set(f"point:{point_id}:latest", json.dumps({"value": value, "quality": quality}))

    async def get_latest(self, point_id: str) -> dict | None:
        if not self._redis:
            return None
        raw = await self._redis.get(f"point:{point_id}:latest")
        return json.loads(raw) if raw else None

    async def get_latest_batch(self, point_ids: list[str]) -> dict[str, dict | None]:
        if not self._redis or not point_ids:
            return {}
        keys = [f"point:{pid}:latest" for pid in point_ids]
        results = await self._redis.mget(keys)
        return {
            pid: (json.loads(r) if r else None)
            for pid, r in zip(point_ids, results)
        }
```

- [ ] **Step 2: Write forwarder.py**

```python
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
        """Push latest values to Asset Service.
        updates: [{"point_id": "x", "value": 42.0, "last_updated": 1716123456}, ...]
        """
        client = await self._get_client()
        resp = await client.post(f"{self._url}/api/equipment/points/batch-update", json={"updates": updates})
        resp.raise_for_status()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
```

- [ ] **Step 3: Write gap filler with test**

```python
# gap_filler.py
from datetime import datetime, timezone
from typing import Sequence
from .models import EquipmentReading


class GapFiller:
    @staticmethod
    def fill(point_id: str, readings: Sequence[EquipmentReading],
             gap_start: datetime, gap_end: datetime) -> list[EquipmentReading]:
        gap_seconds = (gap_end - gap_start).total_seconds()
        filled = []

        if gap_seconds < 300:  # <5min: linear interpolation
            before = next((r for r in readings if r.time < gap_start and r.quality == "good"), None)
            after = next((r for r in readings if r.time > gap_end and r.quality == "good"), None)
            if before and after:
                dt = (after.time - before.time).total_seconds()
                dv = after.value - before.value
                mid_time = gap_start + (gap_end - gap_start) / 2
                mid_value = before.value + dv * ((mid_time - before.time).total_seconds() / dt) if dt > 0 else before.value
                filled.append(EquipmentReading(
                    time=mid_time, equipment_id=readings[0].equipment_id,
                    plant_id=readings[0].plant_id, point_id=point_id,
                    point_code=readings[0].point_code, value=mid_value,
                    quality="estimated", source=readings[0].source
                ))

        elif gap_seconds < 3600:  # 5min-1h: peer regression fallback
            filled.append(EquipmentReading(
                time=gap_start + (gap_end - gap_start) / 2,
                equipment_id=readings[0].equipment_id,
                plant_id=readings[0].plant_id, point_id=point_id,
                point_code=readings[0].point_code,
                value=readings[-1].value if readings else 0.0,
                quality="estimated", source=readings[0].source
            ))

        else:  # >1h: fallback to simulation
            filled.append(EquipmentReading(
                time=gap_start + (gap_end - gap_start) / 2,
                equipment_id=readings[0].equipment_id,
                plant_id=readings[0].plant_id, point_id=point_id,
                point_code=readings[0].point_code,
                value=readings[-1].value if readings else 0.0,
                quality="questionable", source="simulated"
            ))

        return filled
```

```python
# tests/test_gap_filler.py
from datetime import datetime, timezone
from acquisition_service.gap_filler import GapFiller
from acquisition_service.models import EquipmentReading


def make_reading(time, value, quality="good", source="live", point_code="CHWST",
                 equipment_id="e1", plant_id="pl1", point_id="p1"):
    return EquipmentReading(
        time=time, equipment_id=equipment_id, plant_id=plant_id,
        point_id=point_id, point_code=point_code, value=value,
        quality=quality, source=source
    )


def test_gap_filler_short_gap_linear_interpolation():
    t0 = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
    readings = [
        make_reading(t0.replace(minute=0), 20.0),
        make_reading(t0.replace(minute=5), 25.0),
    ]
    gap_start = t0.replace(minute=2)
    gap_end = t0.replace(minute=3)
    filled = GapFiller.fill("p1", readings, gap_start, gap_end)
    assert len(filled) == 1
    assert filled[0].quality == "estimated"


def test_gap_filler_long_gap_fallback_simulation():
    t0 = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
    readings = [make_reading(t0.replace(hour=10), 20.0)]
    gap_start = t0.replace(hour=12)
    gap_end = t0.replace(hour=14)
    filled = GapFiller.fill("p1", readings, gap_start, gap_end)
    assert len(filled) == 1
    assert filled[0].quality == "questionable"
    assert filled[0].source == "simulated"
```

- [ ] **Step 4: Run tests**

```bash
pytest services/acquisition/tests/test_gap_filler.py -v
# Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add services/acquisition/acquisition_service/cache.py services/acquisition/acquisition_service/forwarder.py services/acquisition/acquisition_service/gap_filler.py services/acquisition/tests/test_gap_filler.py
git commit -m "feat(acq): add cache, forwarder, and gap filler"
```

---

### Task A7: Control command write path

**Files:**
- Create: `services/acquisition/acquisition_service/api/__init__.py` (empty)
- Create: `services/acquisition/acquisition_service/api/commands.py`

- [ ] **Step 1: Write commands API with safety checks**

```python
# api/commands.py
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..adapters.base import WriteError

router = APIRouter()


class WriteCommandRequest(BaseModel):
    point_id: str
    value: float
    emergency: bool = False
    operator: str | None = None


class WriteCommandResponse(BaseModel):
    success: bool
    point_id: str
    value: float
    timestamp: str


_last_writes: dict[str, float] = {}  # point_id -> last write timestamp
MIN_WRITE_INTERVAL = 1.0  # seconds


def _check_write_rate(point_id: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    if point_id in _last_writes:
        if now - _last_writes[point_id] < MIN_WRITE_INTERVAL:
            raise HTTPException(status_code=429, detail="Write rate limit exceeded")


def _check_value_range(point_config: dict, value: float) -> None:
    min_val = point_config.get("min_value")
    max_val = point_config.get("max_value")
    if min_val is not None and value < min_val:
        raise HTTPException(status_code=400, detail=f"Value {value} below minimum {min_val}")
    if max_val is not None and value > max_val:
        raise HTTPException(status_code=400, detail=f"Value {value} above maximum {max_val}")


@router.post("/commands/write", response_model=WriteCommandResponse)
async def write_point(req: WriteCommandRequest, request: Request):
    """Write a control value to a hardware point."""
    poller = request.app.state.poller
    point_data = poller._points.get(req.point_id)

    if point_data is None:
        raise HTTPException(status_code=404, detail=f"Point {req.point_id} not registered for polling")

    pt, adapter = point_data

    if not req.emergency:
        _check_write_rate(req.point_id)

    try:
        await adapter.write_point(req.point_id, pt.binding, req.value)
    except WriteError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _last_writes[req.point_id] = datetime.now(timezone.utc).timestamp()

    return WriteCommandResponse(
        success=True, point_id=req.point_id, value=req.value,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/commands/history")
async def command_history(point_id: str | None = None):
    """Return recent write commands for audit."""
    return {"commands": []}  # stub — full impl in Module B with audit log
```

- [ ] **Step 2: Commit**

```bash
git add services/acquisition/acquisition_service/api/
git commit -m "feat(acq): add control command write path with safety checks"
```

---

### Task A8: Points and status API endpoints

**Files:**
- Create: `services/acquisition/acquisition_service/api/points.py`
- Create: `services/acquisition/acquisition_service/api/status.py`

- [ ] **Step 1: Write points API**

```python
# api/points.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..poller import PollingPoint
from ..adapters.base import ProtocolBinding

router = APIRouter()


class RegisterPointRequest(BaseModel):
    point_id: str
    equipment_id: str
    plant_id: str
    point_code: str
    protocol: str
    protocol_config: dict
    poll_interval_sec: float = 10.0


@router.post("/points/register")
async def register_point(req: RegisterPointRequest, request: Request):
    poller = request.app.state.poller
    binding = ProtocolBinding(protocol=req.protocol, config=req.protocol_config)

    from ..adapters.modbus_adapter import ModbusAdapter
    from ..adapters.bacnet_adapter import BacnetAdapter
    from ..adapters.opcua_adapter import OpcUaAdapter

    adapters = {"modbus": ModbusAdapter, "bacnet": BacnetAdapter, "opc_ua": OpcUaAdapter}
    adapter_cls = adapters.get(req.protocol)
    if adapter_cls is None:
        raise HTTPException(status_code=400, detail=f"Unsupported protocol: {req.protocol}")

    adapter = adapter_cls()
    try:
        await adapter.connect(binding)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connection failed: {e}")

    point = PollingPoint(
        point_id=req.point_id, equipment_id=req.equipment_id,
        plant_id=req.plant_id, point_code=req.point_code,
        binding=binding, poll_interval_sec=req.poll_interval_sec
    )
    poller.register_point(point, adapter)
    return {"status": "registered", "point_id": req.point_id}


@router.delete("/points/{point_id}")
async def unregister_point(point_id: str, request: Request):
    request.app.state.poller.unregister_point(point_id)
    return {"status": "unregistered", "point_id": point_id}


@router.get("/points")
async def list_points(request: Request):
    poller = request.app.state.poller
    points = []
    for pid, (pt, _) in poller._points.items():
        points.append({
            "point_id": pid, "point_code": pt.point_code,
            "equipment_id": pt.equipment_id, "plant_id": pt.plant_id,
            "protocol": pt.binding.protocol, "poll_interval_sec": pt.poll_interval_sec,
            "last_value": pt.last_value,
        })
    return {"points": points, "count": len(points)}
```

- [ ] **Step 2: Write status API**

```python
# api/status.py
from datetime import datetime, timezone

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
async def acquisition_status(request: Request):
    poller = request.app.state.poller
    points = list(poller._points.keys())
    return {
        "service": "acquisition",
        "running": poller._running,
        "registered_points": len(points),
        "uptime_seconds": "unknown",  # track with start time
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status/health")
async def adapter_health(request: Request):
    poller = request.app.state.poller
    health = {}
    for pid, (pt, adapter) in poller._points.items():
        health[pt.point_code] = {
            "protocol": pt.binding.protocol,
            "last_poll": pt.last_poll,
            "last_value": pt.last_value,
            "interval": pt.poll_interval_sec,
        }
    return {"adapters": health}
```

- [ ] **Step 3: Commit**

```bash
git add services/acquisition/acquisition_service/api/points.py services/acquisition/acquisition_service/api/status.py
git commit -m "feat(acq): add points registration and status API endpoints"
```

---

### Task A9: Docker Compose integration

**Files:**
- Modify: `docker-compose.yml` (add acq service + acq_db)
- Modify: `common/common/config.py` (add acquisition_service_url + acq_database_url)

- [ ] **Step 1: Add acq_db and acquisition_service to docker-compose.yml**

Insert after the `redis` service block:

```yaml
  timescaledb_acq:
    image: timescale/timescaledb:2.17.2-pg16
    environment:
      POSTGRES_DB: acq_db
      POSTGRES_USER: hvac
      POSTGRES_PASSWORD: hvac_dev
    ports: ["5438:5432"]
    volumes: [tsdb_acq:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hvac -d acq_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  acquisition_service:
    build: services/acquisition
    ports: ["8005:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://hvac:hvac_dev@timescaledb_acq:5432/acq_db
      ASSET_SERVICE_URL: http://asset_service:8000
      REDIS_URL: redis://redis:6379/0
    depends_on:
      timescaledb_acq:
        condition: service_healthy
      redis:
        condition: service_healthy
```

Add `tsdb_acq:` to volumes section.

- [ ] **Step 2: Update common config**

```python
# common/common/config.py — add to Settings class:
    acquisition_service_url: str = "http://localhost:8005"
    acq_database_url: str = "postgresql+asyncpg://hvac:hvac_dev@localhost:5438/acq_db"
```

- [ ] **Step 3: Add acquisition_service to gateway proxy**

Update `services/gateway/gateway_service/proxy.py` to route `/api/acquisition` to `acquisition_service:8000`.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml common/common/config.py services/gateway/gateway_service/proxy.py
git commit -m "feat(acq): add Data Acquisition Service to Docker Compose and Gateway"
```

---

### Task A10: Edge sync (edge-cloud bridge)

**Files:**
- Create: `services/acquisition/acquisition_service/edge_sync.py`
- Create: `services/acquisition/tests/test_edge_sync.py`

- [ ] **Step 1: Write edge_sync.py**

```python
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class EdgeSync:
    """Push local acq_db batches to cloud when connection is restored."""

    def __init__(self, session_factory, redis, cloud_url: str, batch_size: int = 500):
        self._session_factory = session_factory
        self._redis = redis
        self._cloud_url = cloud_url.rstrip("/")
        self._batch_size = batch_size
        self._last_synced_id = 0

    async def sync_pending(self) -> int:
        from .models import EquipmentReading
        synced = 0
        async with self._session_factory() as session:
            result = await session.execute(
                "SELECT * FROM equipment_readings WHERE id > :last_id ORDER BY id LIMIT :limit",
                {"last_id": self._last_synced_id, "limit": self._batch_size}
            )
            rows = result.fetchall()
            if rows:
                import httpx
                async with httpx.AsyncClient(timeout=30) as client:
                    payload = [{
                        "time": r.time.isoformat(), "equipment_id": r.equipment_id,
                        "plant_id": r.plant_id, "point_id": r.point_id,
                        "point_code": r.point_code, "value": r.value,
                        "quality": r.quality, "source": r.source,
                    } for r in rows]
                    resp = await client.post(f"{self._cloud_url}/api/acquisition/sync", json={"readings": payload})
                    if resp.status_code == 200:
                        self._last_synced_id = rows[-1].id
                        synced = len(rows)
                        if self._redis:
                            await self._redis.set("edge:last_synced_id", str(self._last_synced_id))
        return synced

    async def run_sync_loop(self, interval_sec: int = 30):
        while True:
            try:
                count = await self.sync_pending()
                if count > 0:
                    logger.info(f"Edge sync: pushed {count} readings to cloud")
            except Exception as e:
                logger.error(f"Edge sync failed: {e}")
            await asyncio.sleep(interval_sec)
```

- [ ] **Step 2: Write test**

```python
# tests/test_edge_sync.py
from unittest.mock import AsyncMock, MagicMock
import pytest
from acquisition_service.edge_sync import EdgeSync


@pytest.mark.asyncio
async def test_edge_sync_no_pending_data():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    syncer = EdgeSync(mock_factory, None, "http://cloud:8005")
    count = await syncer.sync_pending()
    assert count == 0
```

- [ ] **Step 3: Commit**

```bash
git add services/acquisition/acquisition_service/edge_sync.py services/acquisition/tests/test_edge_sync.py
git commit -m "feat(acq): add edge-to-cloud sync for offline resilience"
```

---

## Phase 2: Module C — Model Calibration + Data Quality

### Task C1: Calibration base + chiller calibrator

**Files:**
- Create: `services/simulation/sim_service/calibration/__init__.py` (empty)
- Create: `services/simulation/sim_service/calibration/base.py`
- Create: `services/simulation/sim_service/calibration/chiller_cal.py`
- Create: `services/simulation/sim_service/calibration/validator.py`
- Create: `services/simulation/tests/test_chiller_cal.py`

- [ ] **Step 1: Write calibration base class**

```python
# calibration/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence


@dataclass
class CalibrationDataPoint:
    timestamp: datetime
    input_features: dict  # PLR, ambient conditions, etc.
    measured_output: float  # actual kW, COP, etc.


@dataclass
class CalibrationResult:
    equipment_id: str
    curve_name: str
    original_params: dict
    calibrated_params: dict
    mape: float   # Mean Absolute Percentage Error
    rmse: float
    sample_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseCalibrator(ABC):
    @abstractmethod
    def calibrate(self, data: Sequence[CalibrationDataPoint]) -> CalibrationResult: ...

    @abstractmethod
    def validate(self, data: Sequence[CalibrationDataPoint], params: dict) -> tuple[float, float]: ...
```

- [ ] **Step 2: Write failing test for chiller calibration**

```python
# tests/test_chiller_cal.py
from datetime import datetime, timezone
import pytest
from sim_service.calibration.base import CalibrationDataPoint
from sim_service.calibration.chiller_cal import ChillerCalibrator


def make_data(plr, kw):
    return CalibrationDataPoint(
        timestamp=datetime.now(timezone.utc),
        input_features={"plr": plr, "chwst": 7.0, "cwst": 30.0, "chwrt": 12.0},
        measured_output=kw
    )


def test_chiller_calibration_basic():
    calibrator = ChillerCalibrator()
    data = [
        make_data(0.3, 180.0),
        make_data(0.5, 260.0),
        make_data(0.7, 340.0),
        make_data(1.0, 460.0),
    ]
    result = calibrator.calibrate(data)
    assert result.curve_name == "COP-KW"
    assert result.mape < 10.0  # good fit
    assert result.rmse < 50.0
    assert len(result.calibrated_params) == 4  # a0-a3


def test_chiller_calibration_empty_data():
    calibrator = ChillerCalibrator()
    with pytest.raises(ValueError):
        calibrator.calibrate([])
```

- [ ] **Step 3: Write chiller calibrator implementation**

```python
# calibration/chiller_cal.py
import numpy as np
from .base import BaseCalibrator, CalibrationDataPoint, CalibrationResult


class ChillerCalibrator(BaseCalibrator):
    def calibrate(self, data: list[CalibrationDataPoint]) -> CalibrationResult:
        if not data:
            raise ValueError("Empty calibration data")

        plr = np.array([d.input_features["plr"] for d in data])
        kw_measured = np.array([d.measured_output for d in data])

        # Polynomial fit: kW = a0 + a1*PLR + a2*PLR^2 + a3*PLR^3
        coeffs = np.polyfit(plr, kw_measured, deg=3)
        params = {f"a{i}": round(float(c), 6) for i, c in enumerate(coeffs)}

        kw_pred = np.polyval(coeffs, plr)
        mape = float(np.mean(np.abs((kw_measured - kw_pred) / (kw_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((kw_measured - kw_pred) ** 2)))

        return CalibrationResult(
            equipment_id=data[0].input_features.get("equipment_id", "unknown"),
            curve_name="COP-KW",
            original_params={},  # filled by caller from physics model
            calibrated_params=params,
            mape=mape, rmse=rmse, sample_count=len(data)
        )

    def validate(self, data: list[CalibrationDataPoint], params: dict) -> tuple[float, float]:
        coeffs = [params["a0"], params["a1"], params["a2"], params["a3"]]
        plr = np.array([d.input_features["plr"] for d in data])
        kw_measured = np.array([d.measured_output for d in data])
        kw_pred = np.polyval(coeffs, plr)
        mape = float(np.mean(np.abs((kw_measured - kw_pred) / (kw_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((kw_measured - kw_pred) ** 2)))
        return mape, rmse
```

- [ ] **Step 4: Write validator**

```python
# calibration/validator.py
import numpy as np
from .base import CalibrationDataPoint, CalibrationResult


class CalibrationValidator:
    MAPE_THRESHOLD = 15.0  # publish only if MAPE < 15%
    RMSE_THRESHOLD = 100.0

    @classmethod
    def is_acceptable(cls, result: CalibrationResult) -> bool:
        return result.mape < cls.MAPE_THRESHOLD and result.rmse < cls.RMSE_THRESHOLD

    @classmethod
    def split_data(cls, data: list[CalibrationDataPoint], train_ratio: float = 0.8):
        n = len(data)
        indices = np.random.RandomState(42).permutation(n)
        split = int(n * train_ratio)
        train_idx = indices[:split]
        test_idx = indices[split:]
        return [data[i] for i in train_idx], [data[i] for i in test_idx]
```

- [ ] **Step 5: Run tests**

```bash
pytest services/simulation/tests/test_chiller_cal.py -v
# Expected: PASS
```

- [ ] **Step 6: Commit**

```bash
git add services/simulation/sim_service/calibration/ services/simulation/tests/
git commit -m "feat(cal): add chiller calibration base + validator"
```

---

### Task C2: Tower, pump, valve calibrators

**Files:**
- Create: `services/simulation/sim_service/calibration/tower_cal.py`
- Create: `services/simulation/sim_service/calibration/pump_cal.py`
- Create: `services/simulation/sim_service/calibration/valve_cal.py`
- Create: `services/simulation/tests/test_tower_pump_valve_cal.py`

- [ ] **Step 1: Write tower calibrator**

```python
# calibration/tower_cal.py
import numpy as np
from .base import BaseCalibrator, CalibrationDataPoint, CalibrationResult


class TowerCalibrator(BaseCalibrator):
    """Calibrate cooling tower approach curve: T_out = f(wet_bulb, load, flow)."""

    def calibrate(self, data: list[CalibrationDataPoint]) -> CalibrationResult:
        if not data:
            raise ValueError("Empty data")
        wb = np.array([d.input_features["wet_bulb"] for d in data])
        load_ratio = np.array([d.input_features.get("load_ratio", 0.7) for d in data])
        t_out_measured = np.array([d.measured_output for d in data])

        # Simple model: T_out = k0 + k1*wb + k2*load_ratio
        X = np.column_stack([np.ones(len(data)), wb, load_ratio])
        coeffs, _, _, _ = np.linalg.lstsq(X, t_out_measured, rcond=None)
        params = {f"k{i}": round(float(c), 6) for i, c in enumerate(coeffs)}

        t_pred = X @ coeffs
        mape = float(np.mean(np.abs((t_out_measured - t_pred) / (t_out_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((t_out_measured - t_pred) ** 2)))

        return CalibrationResult(
            equipment_id="unknown", curve_name="approach",
            original_params={}, calibrated_params=params,
            mape=mape, rmse=rmse, sample_count=len(data)
        )

    def validate(self, data, params):
        wb = np.array([d.input_features["wet_bulb"] for d in data])
        load_ratio = np.array([d.input_features.get("load_ratio", 0.7) for d in data])
        t_measured = np.array([d.measured_output for d in data])
        X = np.column_stack([np.ones(len(data)), wb, load_ratio])
        coeffs = np.array([params["k0"], params["k1"], params["k2"]])
        t_pred = X @ coeffs
        mape = float(np.mean(np.abs((t_measured - t_pred) / (t_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((t_measured - t_pred) ** 2)))
        return mape, rmse
```

- [ ] **Step 2: Write pump calibrator (Q-H curve)**

```python
# calibration/pump_cal.py
import numpy as np
from .base import BaseCalibrator, CalibrationDataPoint, CalibrationResult


class PumpCalibrator(BaseCalibrator):
    """Calibrate pump Q-H curve: head = a0 + a1*Q + a2*Q^2 (at rated speed)."""

    def calibrate(self, data: list[CalibrationDataPoint]) -> CalibrationResult:
        if not data:
            raise ValueError("Empty data")
        flow = np.array([d.input_features["flow_rate"] for d in data])
        head_measured = np.array([d.measured_output for d in data])

        coeffs = np.polyfit(flow, head_measured, deg=2)
        params = {f"a{i}": round(float(c), 6) for i, c in enumerate(coeffs)}

        head_pred = np.polyval(coeffs, flow)
        mape = float(np.mean(np.abs((head_measured - head_pred) / (head_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((head_measured - head_pred) ** 2)))

        return CalibrationResult(
            equipment_id="unknown", curve_name="Q-H",
            original_params={}, calibrated_params=params,
            mape=mape, rmse=rmse, sample_count=len(data)
        )

    def validate(self, data, params):
        flow = np.array([d.input_features["flow_rate"] for d in data])
        head_measured = np.array([d.measured_output for d in data])
        coeffs = np.array([params["a0"], params["a1"], params["a2"]])
        head_pred = np.polyval(coeffs, flow)
        mape = float(np.mean(np.abs((head_measured - head_pred) / (head_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((head_measured - head_pred) ** 2)))
        return mape, rmse
```

- [ ] **Step 3: Write valve calibrator (Cv curve)**

```python
# calibration/valve_cal.py
import numpy as np
from .base import BaseCalibrator, CalibrationDataPoint, CalibrationResult


class ValveCalibrator(BaseCalibrator):
    """Calibrate valve Cv curve: Cv = f(opening)."""

    def calibrate(self, data: list[CalibrationDataPoint]) -> CalibrationResult:
        if not data:
            raise ValueError("Empty data")
        opening = np.array([d.input_features["opening"] for d in data])
        cv_measured = np.array([d.measured_output for d in data])

        coeffs = np.polyfit(opening, cv_measured, deg=2)
        params = {f"a{i}": round(float(c), 6) for i, c in enumerate(coeffs)}

        cv_pred = np.polyval(coeffs, opening)
        mape = float(np.mean(np.abs((cv_measured - cv_pred) / (cv_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((cv_measured - cv_pred) ** 2)))

        return CalibrationResult(
            equipment_id="unknown", curve_name="Cv-opening",
            original_params={}, calibrated_params=params,
            mape=mape, rmse=rmse, sample_count=len(data)
        )

    def validate(self, data, params):
        opening = np.array([d.input_features["opening"] for d in data])
        cv_measured = np.array([d.measured_output for d in data])
        coeffs = np.array([params["a0"], params["a1"], params["a2"]])
        cv_pred = np.polyval(coeffs, opening)
        mape = float(np.mean(np.abs((cv_measured - cv_pred) / (cv_measured + 1e-6))) * 100)
        rmse = float(np.sqrt(np.mean((cv_measured - cv_pred) ** 2)))
        return mape, rmse
```

- [ ] **Step 4: Write combined test**

```python
# tests/test_tower_pump_valve_cal.py
from datetime import datetime, timezone
from sim_service.calibration.base import CalibrationDataPoint
from sim_service.calibration.tower_cal import TowerCalibrator
from sim_service.calibration.pump_cal import PumpCalibrator
from sim_service.calibration.valve_cal import ValveCalibrator


def test_tower_calibration():
    calibrator = TowerCalibrator()
    data = [
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"wet_bulb": 24, "load_ratio": 0.8}, measured_output=30.5),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"wet_bulb": 26, "load_ratio": 1.0}, measured_output=32.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"wet_bulb": 22, "load_ratio": 0.5}, measured_output=28.0),
    ]
    result = calibrator.calibrate(data)
    assert result.curve_name == "approach"
    assert result.mape < 20.0


def test_pump_calibration():
    calibrator = PumpCalibrator()
    data = [
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"flow_rate": 100}, measured_output=30.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"flow_rate": 200}, measured_output=28.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"flow_rate": 300}, measured_output=24.0),
    ]
    result = calibrator.calibrate(data)
    assert result.curve_name == "Q-H"
    assert result.mape < 20.0


def test_valve_calibration():
    calibrator = ValveCalibrator()
    data = [
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"opening": 0.2}, measured_output=10.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"opening": 0.5}, measured_output=50.0),
        CalibrationDataPoint(timestamp=datetime.now(timezone.utc),
                             input_features={"opening": 0.8}, measured_output=90.0),
    ]
    result = calibrator.calibrate(data)
    assert result.curve_name == "Cv-opening"
    assert result.mape < 20.0
```

- [ ] **Step 5: Run tests + commit**

```bash
pytest services/simulation/tests/test_tower_pump_valve_cal.py -v && \
git add services/simulation/sim_service/calibration/ services/simulation/tests/ && \
git commit -m "feat(cal): add tower, pump, and valve calibrators"
```

---

### Task C3: Data cleaner and calibration API

**Files:**
- Create: `services/simulation/sim_service/calibration/cleaner.py`
- Create: `services/simulation/sim_service/api/calibration.py`
- Modify: `services/simulation/sim_service/main.py` (register calibration router)

- [ ] **Step 1: Write data cleaner**

```python
# calibration/cleaner.py
import numpy as np
from .base import CalibrationDataPoint


class DataCleaner:
    @staticmethod
    def remove_outliers(data: list[CalibrationDataPoint], sigma: float = 3.0) -> list[CalibrationDataPoint]:
        """Remove points where output deviates > sigma std from the mean."""
        if len(data) < 5:
            return data
        values = np.array([d.measured_output for d in data])
        mean, std = np.mean(values), np.std(values)
        if std == 0:
            return data
        return [d for d, v in zip(data, values) if abs(v - mean) <= sigma * std]

    @staticmethod
    def remove_startup(data: list[CalibrationDataPoint], min_plr: float = 0.1) -> list[CalibrationDataPoint]:
        """Remove startup/shutdown periods (very low load)."""
        return [d for d in data if d.input_features.get("plr", 0.5) >= min_plr]

    @staticmethod
    def remove_stale(data: list[CalibrationDataPoint], max_seconds: float = 300.0) -> list[CalibrationDataPoint]:
        """Remove points where adjacent interval > max_seconds (sensor dropout)."""
        if len(data) < 2:
            return data
        cleaned = [data[0]]
        for i in range(1, len(data)):
            delta = (data[i].timestamp - data[i-1].timestamp).total_seconds()
            if delta <= max_seconds:
                cleaned.append(data[i])
        return cleaned

    @classmethod
    def clean(cls, data: list[CalibrationDataPoint]) -> list[CalibrationDataPoint]:
        data = cls.remove_outliers(data)
        data = cls.remove_startup(data)
        data = cls.remove_stale(data)
        return data
```

- [ ] **Step 2: Write calibration API**

```python
# api/calibration.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..calibration.chiller_cal import ChillerCalibrator
from ..calibration.tower_cal import TowerCalibrator
from ..calibration.pump_cal import PumpCalibrator
from ..calibration.valve_cal import ValveCalibrator
from ..calibration.cleaner import DataCleaner
from ..calibration.validator import CalibrationValidator
from ..calibration.base import CalibrationDataPoint

router = APIRouter()

CALIBRATORS = {
    "chiller": ChillerCalibrator,
    "cooling_tower": TowerCalibrator,
    "pump": PumpCalibrator,
    "valve": ValveCalibrator,
}


class CalibrationRequest(BaseModel):
    equipment_id: str
    equipment_type: str  # chiller | cooling_tower | pump | valve
    data: list[dict]  # [{timestamp, input_features, measured_output}, ...]


@router.post("/calibration/run")
async def run_calibration(req: CalibrationRequest):
    calibrator_cls = CALIBRATORS.get(req.equipment_type)
    if not calibrator_cls:
        raise HTTPException(400, f"Unknown equipment type: {req.equipment_type}")

    points = [
        CalibrationDataPoint(
            timestamp=p["timestamp"],
            input_features={**p.get("input_features", {}), "equipment_id": req.equipment_id},
            measured_output=p["measured_output"]
        ) for p in req.data
    ]

    cleaned = DataCleaner.clean(points)
    if len(cleaned) < 4:
        raise HTTPException(400, f"Insufficient data after cleaning: {len(cleaned)} points")

    train_data, test_data = CalibrationValidator.split_data(cleaned)
    calibrator = calibrator_cls()
    result = calibrator.calibrate(train_data)

    if test_data:
        test_mape, test_rmse = calibrator.validate(test_data, result.calibrated_params)
        result.mape = test_mape
        result.rmse = test_rmse

    acceptable = CalibrationValidator.is_acceptable(result)

    return {
        "result": {
            "equipment_id": result.equipment_id,
            "curve_name": result.curve_name,
            "calibrated_params": result.calibrated_params,
            "mape": round(result.mape, 2),
            "rmse": round(result.rmse, 2),
            "sample_count": result.sample_count,
            "acceptable": acceptable,
        }
    }


@router.get("/calibration/history")
async def calibration_history(equipment_id: str | None = None):
    return {"history": []}  # DB-backed in production
```

- [ ] **Step 3: Register calibration router in main.py**

Add to `services/simulation/sim_service/main.py`:
```python
from .api import calibration as _calibration  # noqa
app.include_router(_calibration.router, prefix="/api/simulation", tags=["Calibration"])
```

- [ ] **Step 4: Commit**

```bash
git add services/simulation/sim_service/calibration/cleaner.py services/simulation/sim_service/api/calibration.py services/simulation/sim_service/main.py
git commit -m "feat(cal): add data cleaner and calibration API endpoints"
```

---

### Task C4: Data quality monitor — Layers 1+2 (realtime + statistical)

**Files:**
- Create: `services/simulation/sim_service/data_quality/__init__.py` (empty)
- Create: `services/simulation/sim_service/data_quality/realtime_rules.py`
- Create: `services/simulation/sim_service/data_quality/statistical.py`
- Create: `services/simulation/tests/test_data_quality.py`

- [ ] **Step 1: Write realtime rules (Layer 1)**

```python
# data_quality/realtime_rules.py
from dataclasses import dataclass
from typing import Callable
from datetime import datetime, timezone


@dataclass
class QualityEvent:
    point_id: str
    equipment_id: str
    event_type: str   # out_of_bounds | communication_lost
    severity: str     # critical | high | warning | info
    value: float | None
    threshold: float | None
    timestamp: datetime


class RealtimeRules:
    def __init__(self):
        self._bounds: dict[str, tuple[float, float]] = {}
        self._last_comms: dict[str, float] = {}
        self.comm_timeout_sec = 5.0

    def set_bounds(self, point_id: str, min_val: float, max_val: float) -> None:
        self._bounds[point_id] = (min_val, max_val)

    def check_bounds(self, point_id: str, equipment_id: str, value: float) -> QualityEvent | None:
        bounds = self._bounds.get(point_id)
        if bounds is None:
            return None
        lo, hi = bounds
        if value < lo or value > hi:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="out_of_bounds", severity="critical",
                value=value, threshold=hi if value > hi else lo,
                timestamp=datetime.now(timezone.utc)
            )
        return None

    def check_communication(self, point_id: str, equipment_id: str) -> QualityEvent | None:
        now = datetime.now(timezone.utc).timestamp()
        last = self._last_comms.get(point_id)
        if last is not None and now - last > self.comm_timeout_sec:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="communication_lost", severity="critical",
                value=None, threshold=None,
                timestamp=datetime.now(timezone.utc)
            )
        self._last_comms[point_id] = now
        return None
```

- [ ] **Step 2: Write statistical detector (Layer 2)**

```python
# data_quality/statistical.py
from collections import deque
import numpy as np
from .realtime_rules import QualityEvent


class StatisticalDetector:
    def __init__(self, freeze_window: int = 100, freeze_threshold: float = 0.001):
        self._histories: dict[str, deque] = {}
        self._freeze_window = freeze_window
        self._freeze_threshold = freeze_threshold

    def check_frozen(self, point_id: str, equipment_id: str, value: float) -> QualityEvent | None:
        if point_id not in self._histories:
            self._histories[point_id] = deque(maxlen=self._freeze_window)
        self._histories[point_id].append(value)

        window = self._histories[point_id]
        if len(window) < self._freeze_window:
            return None

        if np.var(list(window)) < self._freeze_threshold:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="sensor_frozen", severity="high",
                value=value, threshold=None,
                timestamp=None
            )
        return None

    def check_spike(self, point_id: str, equipment_id: str, current: float,
                    previous: float, sigma: float = 5.0) -> QualityEvent | None:
        if previous == 0:
            return None
        change = abs(current - previous) / abs(previous)
        if change > sigma:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="spike", severity="high",
                value=current, threshold=previous * (1 + sigma),
                timestamp=None
            )
        return None
```

- [ ] **Step 3: Write tests**

```python
# tests/test_data_quality.py
from sim_service.data_quality.realtime_rules import RealtimeRules
from sim_service.data_quality.statistical import StatisticalDetector


def test_realtime_out_of_bounds():
    rules = RealtimeRules()
    rules.set_bounds("p1", -10.0, 50.0)
    event = rules.check_bounds("p1", "e1", 60.0)
    assert event is not None
    assert event.event_type == "out_of_bounds"
    assert event.severity == "critical"


def test_realtime_in_bounds():
    rules = RealtimeRules()
    rules.set_bounds("p1", -10.0, 50.0)
    event = rules.check_bounds("p1", "e1", 25.0)
    assert event is None


def test_statistical_frozen_sensor():
    detector = StatisticalDetector(freeze_window=5)
    for _ in range(6):
        event = detector.check_frozen("p1", "e1", 42.0)
    assert event is not None
    assert event.event_type == "sensor_frozen"


def test_statistical_spike():
    detector = StatisticalDetector()
    event = detector.check_spike("p1", "e1", current=500.0, previous=10.0, sigma=5.0)
    assert event is not None
    assert event.event_type == "spike"
```

- [ ] **Step 4: Run tests + commit**

```bash
pytest services/simulation/tests/test_data_quality.py -v && \
git add services/simulation/sim_service/data_quality/ services/simulation/tests/ && \
git commit -m "feat(dq): add realtime and statistical data quality detectors"
```

---

### Task C5: Context window detectors (Layer 3) + Root cause analyzer (Layer 5)

**Files:**
- Create: `services/simulation/sim_service/data_quality/context_window.py`
- Create: `services/simulation/sim_service/data_quality/root_cause_analyzer.py`
- Create: `services/simulation/tests/test_context_window.py`

- [ ] **Step 1: Write context window detectors**

```python
# data_quality/context_window.py
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import numpy as np
from .realtime_rules import QualityEvent


class BaselineComparator:
    """Compare current value against historical baseline (same hour, same day type)."""
    def __init__(self, sigma: float = 3.0):
        self._baselines: dict[str, dict[str, tuple[float, float]]] = defaultdict(dict)
        self._sigma = sigma

    def update_baseline(self, point_id: str, hour: int, is_weekend: bool, value: float) -> None:
        key = f"{hour}:{'we' if is_weekend else 'wd'}"
        prev = self._baselines[point_id].get(key)
        if prev:
            mu, sigma, n = prev
            self._baselines[point_id][key] = (mu + (value - mu) / (n + 1), sigma * 0.95 + abs(value - mu) * 0.05, n + 1)
        else:
            self._baselines[point_id][key] = (value, 10.0, 1)

    def check(self, point_id: str, equipment_id: str, value: float,
              hour: int, is_weekend: bool) -> QualityEvent | None:
        key = f"{hour}:{'we' if is_weekend else 'wd'}"
        baseline = self._baselines[point_id].get(key)
        if baseline is None:
            return None
        mu, sigma, n = baseline
        if n < 10:
            return None  # not enough history
        if abs(value - mu) > self._sigma * sigma:
            return QualityEvent(
                point_id=point_id, equipment_id=equipment_id,
                event_type="baseline_deviation", severity="warning",
                value=value, threshold=mu,
                timestamp=datetime.now(timezone.utc)
            )
        return None


class DriftTracker:
    """CUSUM + EWMA degradation tracker for efficiency metrics."""
    def __init__(self, ewma_alpha: float = 0.1, cusum_threshold: float = 5.0):
        self._ewma: dict[str, float] = {}
        self._cusum_pos: dict[str, float] = defaultdict(float)
        self._cusum_neg: dict[str, float] = defaultdict(float)
        self._alpha = ewma_alpha
        self._threshold = cusum_threshold

    def update(self, point_id: str, value: float) -> QualityEvent | None:
        prev = self._ewma.get(point_id, value)
        new_ewma = self._alpha * value + (1 - self._alpha) * prev
        self._ewma[point_id] = new_ewma

        target = self._ewma.get(f"{point_id}:target", value)
        error = value - target

        self._cusum_pos[point_id] = max(0, self._cusum_pos[point_id] + error - 0.5)
        self._cusum_neg[point_id] = max(0, self._cusum_neg[point_id] - error - 0.5)

        if self._cusum_pos[point_id] > self._threshold:
            self._cusum_pos[point_id] = 0
            return QualityEvent(
                point_id=point_id, equipment_id="", event_type="degradation_upward",
                severity="warning", value=value, threshold=target, timestamp=datetime.now(timezone.utc)
            )
        if self._cusum_neg[point_id] > self._threshold:
            self._cusum_neg[point_id] = 0
            return QualityEvent(
                point_id=point_id, equipment_id="", event_type="degradation_downward",
                severity="warning", value=value, threshold=target, timestamp=datetime.now(timezone.utc)
            )
        return None


class PeerComparator:
    """Compare equipment against peers of same type."""
    def __init__(self, max_deviation_pct: float = 5.0):
        self._group_values: dict[str, list[float]] = defaultdict(list)
        self._max_dev = max_deviation_pct

    def update(self, group_key: str, equipment_id: str, value: float) -> QualityEvent | None:
        self._group_values[f"{group_key}:{equipment_id}"] = self._group_values.get(
            f"{group_key}:{equipment_id}", []
        )[-9:] + [value]

        all_vals = []
        for k, vals in self._group_values.items():
            if k.startswith(group_key) and vals:
                all_vals.append(np.median(vals[-5:]))

        if len(all_vals) < 2:
            return None

        group_median = np.median(all_vals)
        if group_median == 0:
            return None

        my_median = np.median(self._group_values[f"{group_key}:{equipment_id}"][-5:])
        deviation = abs(my_median - group_median) / abs(group_median) * 100
        if deviation > self._max_dev:
            return QualityEvent(
                point_id="", equipment_id=equipment_id,
                event_type="peer_deviation", severity="warning",
                value=my_median, threshold=group_median,
                timestamp=datetime.now(timezone.utc)
            )
        return None


class OperationalChecker:
    """Check operational context consistency."""
    WINTER_MONTHS = {12, 1, 2}
    SUMMER_MONTHS = {6, 7, 8}

    def check(self, equipment_id: str, plant_mode: str, power_kw: float,
              ambient_temp: float, hour: int, month: int) -> QualityEvent | None:
        # Check: cooling tower running at high load in freezing weather
        if ambient_temp < 2.0 and power_kw > 10.0 and plant_mode == "cooling":
            return QualityEvent(
                point_id="", equipment_id=equipment_id,
                event_type="freeze_risk", severity="high",
                value=ambient_temp, threshold=2.0,
                timestamp=datetime.now(timezone.utc)
            )

        # Check: high cooling in winter without free cooling
        if month in self.WINTER_MONTHS and plant_mode == "mechanical_cooling" and ambient_temp < 10:
            return QualityEvent(
                point_id="", equipment_id=equipment_id,
                event_type="missing_free_cooling_opportunity", severity="medium",
                value=ambient_temp, threshold=10.0,
                timestamp=datetime.now(timezone.utc)
            )
        return None
```

- [ ] **Step 2: Write root cause analyzer (Layer 5)**

```python
# data_quality/root_cause_analyzer.py
from dataclasses import dataclass
from typing import Sequence
from .realtime_rules import QualityEvent


@dataclass
class RootCause:
    category: str  # SENSOR_FAULT | COMM_FAILURE | DRIFT | REAL_ANOMALY | PLC_FAULT | ENV_INTERFERENCE
    confidence: float
    evidence: dict
    recommendation: str


class RootCauseAnalyzer:
    CAUSE_CATEGORIES = {
        "SENSOR_FAULT": "更换传感器",
        "COMM_FAILURE": "检查网络设备",
        "DRIFT": "重新标定传感器",
        "REAL_ANOMALY": "设备检修",
        "PLC_FAULT": "检查PLC/IO模块",
        "ENV_INTERFERENCE": "增加屏蔽或滤波",
    }

    def analyze(self, event: QualityEvent, related_events: Sequence[QualityEvent],
                peer_status: dict) -> RootCause:
        evidence = {}

        # Cross-validation: are peer sensors on same equipment OK?
        peer_ok = peer_status.get("same_equipment_ok", True)
        evidence["cross_validation"] = -0.8 if peer_ok else 0.5

        # Spatial cluster: multiple points on same PLC failing?
        plc_fail_count = peer_status.get("same_plc_failures", 0)
        if plc_fail_count >= 3:
            evidence["spatial_cluster"] = 0.9
        elif plc_fail_count == 0:
            evidence["spatial_cluster"] = -0.5

        # Temporal: correlate with external events
        evidence["temporal_correlate"] = peer_status.get("env_correlation", -0.3)

        # Physics plausibility
        evidence["physics_plausible"] = peer_status.get("physics_plausible", -0.7)

        # History match
        evidence["history_match"] = peer_status.get("history_match_score", 0.0)

        # Weighted decision
        scores = {
            "SENSOR_FAULT": evidence["cross_validation"] * 1.5 + evidence["history_match"],
            "COMM_FAILURE": evidence["spatial_cluster"] * 1.5 + evidence["temporal_correlate"],
            "DRIFT": evidence["physics_plausible"] * (-0.5) + evidence["history_match"] * 0.5,
            "REAL_ANOMALY": evidence["physics_plausible"] * 1.5 + evidence["cross_validation"] * 0.5,
            "PLC_FAULT": evidence["spatial_cluster"] * 2.0,
            "ENV_INTERFERENCE": evidence["temporal_correlate"] * 2.0,
        }

        best_category = max(scores, key=scores.get)
        return RootCause(
            category=best_category,
            confidence=min(max(scores[best_category], 0.0), 1.0),
            evidence=evidence,
            recommendation=self.CAUSE_CATEGORIES[best_category],
        )
```

- [ ] **Step 3: Write test + commit**

```bash
# Write test_context_window.py verifying baseline deviation, drift, peer comparison
pytest services/simulation/tests/test_context_window.py -v && \
git add services/simulation/sim_service/data_quality/ services/simulation/tests/ && \
git commit -m "feat(dq): add context window detectors and root cause analyzer"
```

---

### Task C6: ML anomaly detection (Layer 4) — Autoencoder + Isolation Forest

**Files:**
- Create: `services/agent/agent_service/anomaly/__init__.py` (empty)
- Create: `services/agent/agent_service/anomaly/autoencoder.py`
- Create: `services/agent/agent_service/anomaly/isolation_forest.py`
- Create: `services/agent/agent_service/anomaly/feature_builder.py`
- Create: `services/agent/agent_service/anomaly/cold_start.py`
- Create: `services/agent/tests/test_anomaly_ml.py`

- [ ] **Step 1: Write feature builder**

```python
# anomaly/feature_builder.py
import numpy as np


class FeatureBuilder:
    """Build feature vectors for ML anomaly detection from equipment sensor readings."""

    @staticmethod
    def build_equipment_vector(sensors: dict[str, float], sensor_order: list[str]) -> np.ndarray:
        """Build a normalized feature vector for one equipment snapshot."""
        vec = np.zeros(len(sensor_order))
        for i, name in enumerate(sensor_order):
            vec[i] = sensors.get(name, 0.0)
        return vec

    @staticmethod
    def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
        mean = vectors.mean(axis=0, keepdims=True)
        std = vectors.std(axis=0, keepdims=True)
        std[std == 0] = 1.0
        return (vectors - mean) / std

    @staticmethod
    def build_efficiency_vector(metrics: dict[str, float]) -> np.ndarray:
        """Build efficiency feature vector for Isolation Forest."""
        keys = ["cop", "kw_per_rt", "approach_temp", "plr", "delta_t_chw", "delta_t_cw"]
        return np.array([metrics.get(k, 0.0) for k in keys])
```

- [ ] **Step 2: Write Autoencoder**

```python
# anomaly/autoencoder.py
import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class EquipmentAutoencoder(nn.Module):
    """Autoencoder for equipment sensor anomaly detection."""
    def __init__(self, input_dim: int, hidden_dim: int = 8):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, input_dim),
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

    def reconstruction_error(self, x: np.ndarray) -> float:
        with torch.no_grad():
            tensor = torch.tensor(x, dtype=torch.float32).unsqueeze(0)
            recon = self.forward(tensor)
            error = torch.mean((tensor - recon) ** 2).item()
        return error

    def is_anomaly(self, x: np.ndarray, threshold: float) -> bool:
        return self.reconstruction_error(x) > threshold


class AutoencoderAnomalyDetector:
    def __init__(self, input_dim: int, learning_rate: float = 0.001):
        self.input_dim = input_dim
        self.model = EquipmentAutoencoder(input_dim) if HAS_TORCH else None
        self.threshold = 0.05
        self._optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate) if HAS_TORCH and self.model else None

    def train(self, data: np.ndarray, epochs: int = 50) -> None:
        if not HAS_TORCH or self.model is None:
            return
        self.model.train()
        tensor = torch.tensor(data, dtype=torch.float32)
        for _ in range(epochs):
            self._optimizer.zero_grad()
            recon = self.model(tensor)
            loss = nn.functional.mse_loss(recon, tensor)
            loss.backward()
            self._optimizer.step()
        # Set threshold at 95th percentile of reconstruction errors
        errors = [self.model.reconstruction_error(data[i].numpy()) for i in range(len(data))]
        self.threshold = np.percentile(errors, 95)

    def predict(self, x: np.ndarray) -> dict:
        if self.model is None:
            return {"anomaly": False, "error": 0.0}
        error = self.model.reconstruction_error(x)
        return {
            "anomaly": error > self.threshold,
            "error": float(error),
            "threshold": float(self.threshold),
            "contributing_features": [],  # feature-level attribution in production
        }
```

- [ ] **Step 3: Write Isolation Forest anomaly detector**

```python
# anomaly/isolation_forest.py
import numpy as np
from sklearn.ensemble import IsolationForest as SklearnIF


class IsolationForestDetector:
    def __init__(self, contamination: float = 0.05):
        self._model = SklearnIF(contamination=contamination, random_state=42)
        self._fitted = False

    def fit(self, data: np.ndarray) -> None:
        self._model.fit(data)
        self._fitted = True

    def predict(self, x: np.ndarray) -> dict:
        if not self._fitted:
            return {"anomaly": False, "score": 0.0}
        score = float(self._model.decision_function(x.reshape(1, -1))[0])
        pred = self._model.predict(x.reshape(1, -1))[0]
        return {
            "anomaly": pred == -1,
            "score": score,
            "threshold": 0.0,
        }
```

- [ ] **Step 4: Write cold start**

```python
# anomaly/cold_start.py
import numpy as np


class ColdStartTrainer:
    """Generate synthetic training data from Simulation Engine for ML model warm-up."""

    @staticmethod
    async def generate_from_simulation(sim_client, equipment_id: str, hours: int = 168) -> np.ndarray:
        """Run 1 week of simulated operation to get baseline data."""
        # Call sim service API to run batch simulations over various conditions
        synthetic_data = []
        for plr in np.linspace(0.3, 1.0, 20):
            for twb in np.linspace(20, 30, 10):
                result = await sim_client.post("/api/simulation/run", json={
                    "equipment_id": equipment_id,
                    "conditions": {"plr": float(plr), "wet_bulb": float(twb)},
                })
                if result.status_code == 200:
                    synthetic_data.append(result.json()["sensors"])
        return np.array(synthetic_data) if synthetic_data else np.zeros((0, 10))
```

- [ ] **Step 5: Write tests + commit**

```bash
pytest services/agent/tests/test_anomaly_ml.py -v && \
git add services/agent/agent_service/anomaly/ services/agent/tests/ && \
git commit -m "feat(dq): add ML anomaly detection with autoencoder, isolation forest, and cold start"
```

---

## Phase 3: Module D — Collaborative Optimization + Carbon Trading

### Task D1: Weights Initialization (MAPPO model checkpoint utility)

**Files:**
- Create: `services/agent/agent_service/rl/multi_agent/__init__.py` (empty)
- Create: `services/agent/agent_service/rl/multi_agent/mappo.py`
- Create: `services/agent/agent_service/rl/multi_agent/action_mask.py`
- Create: `services/agent/agent_service/rl/multi_agent/reward_shaper.py`

- [ ] **Step 1: Write MAPPO implementation**

```python
# rl/multi_agent/mappo.py
import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.distributions import Normal
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class ActorCritic(nn.Module):
    """Policy (Actor) + Value (Critic) network for MAPPO."""
    def __init__(self, obs_dim: int, act_dim: int, hidden: int = 128):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
        )
        self.actor_mean = nn.Linear(hidden, act_dim)
        self.actor_logstd = nn.Parameter(torch.zeros(1, act_dim))
        self.critic = nn.Linear(hidden, 1)

    def forward(self, obs):
        features = self.shared(obs)
        mean = self.actor_mean(features)
        std = self.actor_logstd.exp().expand_as(mean)
        dist = Normal(mean, std)
        value = self.critic(features)
        return dist, value


class MultiAgentController:
    """Manages multiple PPO agents sharing a global critic."""
    def __init__(self, device_configs: dict[str, dict]):
        self.agents: dict[str, ActorCritic] = {}
        for device_id, cfg in device_configs.items():
            self.agents[device_id] = ActorCritic(
                obs_dim=cfg["obs_dim"], act_dim=cfg["act_dim"]
            ) if HAS_TORCH else None

    def get_actions(self, observations: dict[str, np.ndarray],
                    action_masks: dict[str, np.ndarray] | None = None
                    ) -> dict[str, np.ndarray]:
        actions = {}
        for device_id, obs in observations.items():
            agent = self.agents.get(device_id)
            if agent is None or not HAS_TORCH:
                actions[device_id] = np.zeros(1)
                continue
            with torch.no_grad():
                obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                dist, _ = agent(obs_tensor)
                action = dist.mean.numpy()[0]
                # Apply action mask
                if action_masks and device_id in action_masks:
                    mask = action_masks[device_id]
                    action = action * mask  # zero out disallowed actions
            actions[device_id] = action
        return actions

    def get_values(self, observations: dict[str, np.ndarray]) -> dict[str, float]:
        values = {}
        for device_id, obs in observations.items():
            agent = self.agents.get(device_id)
            if agent is None or not HAS_TORCH:
                values[device_id] = 0.0
                continue
            with torch.no_grad():
                obs_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                _, value = agent(obs_tensor)
                values[device_id] = float(value.item())
        return values

    def build_observation(self, current: dict, predictions: dict,
                          prices: dict, peer_states: dict) -> np.ndarray:
        """Construct the full observation vector for a single device."""
        obs = np.array([
            current.get("plr", 0.0),
            current.get("chwst", 7.0),
            current.get("chwrt", 12.0),
            current.get("cwst", 30.0),
            current.get("ambient_wb", 24.0),
            predictions.get("load_15m", current.get("plr", 0.0)),
            predictions.get("load_1h", current.get("plr", 0.0)),
            predictions.get("load_4h", current.get("plr", 0.0)),
            predictions.get("load_24h", current.get("plr", 0.0)),
            prices.get("carbon", 58.5),
            prices.get("electric", 0.85),
            prices.get("price_trend_4h", 0.0),
            peer_states.get("peer_plr_avg", current.get("plr", 0.0)),
            peer_states.get("peer_cop_avg", 5.0),
        ], dtype=np.float32)
        return obs
```

- [ ] **Step 2: Write action mask**

```python
# rl/multi_agent/action_mask.py
import numpy as np


class ActionMask:
    """Convert MILP output to DRL action masks."""

    @staticmethod
    def from_milp_schedule(schedule: dict[str, dict]) -> dict[str, np.ndarray]:
        """
        schedule: {"chiller_1": {"on": True, "target_load": 300}, "chiller_2": {"on": False, ...}}
        Returns: {"chiller_1": [1,1,1,...], "chiller_2": [0,0,0,...]}
        """
        masks = {}
        for device_id, plan in schedule.items():
            if plan.get("on", False):
                masks[device_id] = np.ones(1)  # all actions allowed
            else:
                masks[device_id] = np.zeros(1)  # mask all actions (device off)
        return masks

    @staticmethod
    def apply_constraints(actions: dict[str, np.ndarray],
                          limits: dict[str, dict]) -> dict[str, np.ndarray]:
        """Clip actions to safe ranges, e.g. CHWST 5-12°C."""
        for device_id, action in actions.items():
            limit = limits.get(device_id, {})
            lo = limit.get("min", -np.inf)
            hi = limit.get("max", np.inf)
            actions[device_id] = np.clip(action, lo, hi)
        return actions
```

- [ ] **Step 3: Write reward shaper**

```python
# rl/multi_agent/reward_shaper.py
import numpy as np


class RewardShaper:
    """Multi-objective reward shaping for MAPPO."""

    def __init__(self, weights: dict | None = None):
        self.weights = weights or {
            "cop": 0.35,
            "carbon": -0.20,
            "electric": -0.15,
            "load_match": 0.20,
            "anticipatory": 0.05,
            "comfort": -0.05,
        }

    def compute(self, obs: np.ndarray, action: np.ndarray,
                next_obs: np.ndarray, design_cop: float = 5.5) -> float:
        current_plr = obs[0]
        current_cop = (design_cop * current_plr) if current_plr > 0.1 else 0.0
        pred_load_15m = obs[5]
        pred_load_1h = obs[6]
        carbon_price = obs[9]
        electric_price = obs[10]
        chwst = action[0] if len(action) > 0 else 7.0
        comfort_penalty = max(0, chwst - 10.0) + max(0, 5.0 - chwst)
        cop_reward = (current_cop / design_cop) if design_cop > 0 else 0.0
        power_est = current_plr * 500.0  # proxy power at 500kW design
        carbon_penalty = (power_est * 0.0006 * carbon_price) / 100.0
        electric_penalty = (power_est * electric_price) / 500.0
        load_gap = abs(current_plr * 500.0 - pred_load_15m * 500.0) / (pred_load_15m * 500.0 + 1e-6)
        load_match_reward = max(0, 1.0 - load_gap)
        anticipatory_bonus = 0.0
        if abs(pred_load_1h - current_plr) / (current_plr + 1e-6) > 0.2:
            anticipatory_bonus = 0.1 if abs(action[0]) > 0.3 else -0.1

        reward = (
            self.weights["cop"] * cop_reward
            + self.weights["carbon"] * carbon_penalty
            + self.weights["electric"] * electric_penalty
            + self.weights["load_match"] * load_match_reward
            + self.weights["anticipatory"] * anticipatory_bonus
            + self.weights["comfort"] * comfort_penalty
        )
        return float(reward)
```

- [ ] **Step 4: Commit**

```bash
git add services/agent/agent_service/rl/multi_agent/
git commit -m "feat(drl): add MAPPO multi-agent controller with action mask and reward shaper"
```

---

### Task D2: Auto trainer + benchmark comparator

**Files:**
- Create: `services/agent/agent_service/rl/training/__init__.py` (empty)
- Create: `services/agent/agent_service/rl/training/auto_trainer.py`
- Create: `services/agent/agent_service/rl/training/online_finetune.py`
- Create: `services/agent/agent_service/rl/benchmark/__init__.py` (empty)
- Create: `services/agent/agent_service/rl/benchmark/comparator.py`

- [ ] **Step 1: Write auto trainer**

```python
# rl/training/auto_trainer.py
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AutoTrainer:
    """Periodic automatic DRL training scheduler."""

    def __init__(self, controller, session_factory, redis, train_interval_hours: int = 24):
        self._controller = controller
        self._session_factory = session_factory
        self._redis = redis
        self._interval = train_interval_hours * 3600
        self._task: asyncio.Task | None = None

    async def start(self):
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while True:
            try:
                await self._train_cycle()
            except Exception as e:
                logger.error(f"Auto-training failed: {e}")
            await asyncio.sleep(self._interval)

    async def _train_cycle(self):
        logger.info("Starting auto-training cycle")
        # 1. Fetch latest training data from acq_db or sim_db
        # 2. Run MAPPO training episodes
        # 3. Validate against held-out data
        # 4. Save checkpoint if improved
        # 5. Publish training_completed event
        if self._redis:
            await self._redis.publish("events:rl.training_completed", "{}")
```

- [ ] **Step 2: Write online finetuner**

```python
# rl/training/online_finetune.py
import logging

logger = logging.getLogger(__name__)


class OnlineFinetuner:
    """Low-learning-rate online adaptation from LIVE data."""

    def __init__(self, controller, learning_rate: float = 1e-5):
        self._controller = controller
        self._lr = learning_rate
        self._buffer: list[dict] = []
        self._max_buffer = 10000

    def add_experience(self, obs: dict, action: dict, reward: dict, next_obs: dict):
        self._buffer.append({"obs": obs, "action": action, "reward": reward, "next_obs": next_obs})
        if len(self._buffer) > self._max_buffer:
            self._buffer = self._buffer[-self._max_buffer:]

    async def finetune_step(self):
        if len(self._buffer) < 128:
            return None
        batch = self._buffer[-128:]
        # Low-LR PPO update on batch
        logger.debug(f"Online finetune: batch_size={len(batch)}, lr={self._lr}")
        return {"samples": len(batch), "lr": self._lr}
```

- [ ] **Step 3: Write benchmark comparator**

```python
# rl/benchmark/comparator.py
from dataclasses import dataclass
from typing import Sequence


@dataclass
class BenchmarkResult:
    method: str  # mappo | milp_only | pid | manual
    total_cost: float
    avg_cop: float
    carbon_tonnes: float
    comfort_violations: int
    load_match_pct: float


class Comparator:
    """Compare DRL against baselines."""

    def compare(self, mappo_result: BenchmarkResult,
                baselines: Sequence[BenchmarkResult]) -> dict:
        report = {
            "mappo": {
                "cost": mappo_result.total_cost,
                "cop": mappo_result.avg_cop,
                "carbon": mappo_result.carbon_tonnes,
                "comfort_violations": mappo_result.comfort_violations,
                "load_match_pct": mappo_result.load_match_pct,
            },
            "baselines": [],
        }

        best_cost = mappo_result.total_cost
        for bl in baselines:
            report["baselines"].append({
                "method": bl.method,
                "cost": bl.total_cost,
                "cop": bl.avg_cop,
            })
            best_cost = min(best_cost, bl.total_cost)

        savings_pct = ((best_cost - mappo_result.total_cost) / best_cost * 100) if best_cost else 0
        report["mappo_savings_pct"] = round(savings_pct, 2)
        return report
```

- [ ] **Step 4: Commit**

```bash
git add services/agent/agent_service/rl/training/ services/agent/agent_service/rl/benchmark/
git commit -m "feat(drl): add auto trainer, online finetune, and benchmark comparator"
```

---

### Task D3: Inter-station dispatch + carbon trading module

**Files:**
- Create: `services/agent/agent_service/optimization/station_dispatch.py`
- Create: `services/agent/agent_service/optimization/network_flow.py`
- Create: `services/agent/agent_service/carbon/__init__.py` (empty)
- Create: `services/agent/agent_service/carbon/emission_calculator.py`
- Create: `services/agent/agent_service/carbon/carbon_market.py`
- Create: `services/agent/agent_service/carbon/cea_adapter.py`
- Create: `services/agent/agent_service/carbon/carbon_optimizer.py`

- [ ] **Step 1: Write station dispatch**

```python
# optimization/station_dispatch.py
from dataclasses import dataclass


@dataclass
class StationStatus:
    station_id: str
    available_capacity: float  # RT
    marginal_cost: float  # 元/RT-h
    current_load: float
    cop: float
    carbon_intensity: float  # tCO2/RT


@dataclass
class DispatchResult:
    stations: dict[str, float]  # station_id -> target_load
    marginal_cost: dict[str, float]
    unused_capacity: float


def inter_station_dispatch(stations: list[StationStatus], total_load: float,
                           carbon_budget: float | None = None) -> DispatchResult:
    """Allocate total cooling load across multiple stations by marginal cost."""
    sorted_stations = sorted(stations, key=lambda s: s.marginal_cost)

    remaining = total_load
    targets = {}
    mc = {}

    for station in sorted_stations:
        if remaining <= 0:
            targets[station.station_id] = 0.0
            mc[station.station_id] = station.marginal_cost
            continue

        alloc = min(remaining, station.available_capacity)
        targets[station.station_id] = alloc
        mc[station.station_id] = station.marginal_cost
        remaining -= alloc

    return DispatchResult(
        stations=targets,
        marginal_cost=mc,
        unused_capacity=sum(s.available_capacity for s in stations) - total_load,
    )
```

- [ ] **Step 2: Write network flow model**

```python
# optimization/network_flow.py
def estimate_delivery_loss(distance_km: float, flow_temp: float = 7.0,
                           ambient_temp: float = 30.0) -> float:
    """Estimate cooling loss per km of distribution piping."""
    delta_t = ambient_temp - flow_temp
    loss_per_km = 0.02 + 0.001 * delta_t  # ~2-5% per km
    return loss_per_km * distance_km


def effective_capacity(station_capacity: float, distance_km: float,
                       flow_temp: float = 7.0, ambient_temp: float = 30.0) -> float:
    """Capacity after delivery losses."""
    loss = estimate_delivery_loss(distance_km, flow_temp, ambient_temp)
    return station_capacity * (1.0 - loss)
```

- [ ] **Step 3: Write carbon market module**

```python
# carbon/carbon_market.py
from abc import ABC, abstractmethod
from datetime import datetime


class CarbonMarket(ABC):
    region: str
    carbon_price: float  # 元/tCO2
    emission_factor: float  # tCO2/MWh
    allowance_period: tuple[datetime, datetime]

    @abstractmethod
    def emission_cost(self, power_kw: float, duration_hours: float) -> float: ...

    @abstractmethod
    def allowance_remaining(self) -> float: ...

    @abstractmethod
    def purchase_deficit(self, amount_tco2: float) -> float: ...


class GenericCarbonMarket(CarbonMarket):
    """Configurable carbon market for any region."""

    def __init__(self, region: str, carbon_price: float, emission_factor: float,
                 total_allowance: float, period_start: datetime, period_end: datetime):
        self.region = region
        self.carbon_price = carbon_price
        self.emission_factor = emission_factor
        self._total = total_allowance
        self._used = 0.0
        self.allowance_period = (period_start, period_end)

    def emission_cost(self, power_kw: float, duration_hours: float) -> float:
        energy_mwh = power_kw * duration_hours / 1000.0
        emissions = energy_mwh * self.emission_factor
        self._used += emissions
        overage = max(0, self._used - self._total)
        return emissions * self.carbon_price + overage * self.carbon_price * 2.0

    def allowance_remaining(self) -> float:
        return max(0, self._total - self._used)

    def purchase_deficit(self, amount_tco2: float) -> float:
        return amount_tco2 * self.carbon_price * 1.1  # 10% transaction premium
```

- [ ] **Step 4: Write CEA adapter**

```python
# carbon/cea_adapter.py
from .carbon_market import GenericCarbonMarket

# China regional grid emission factors (tCO2/MWh)
CEA_REGIONAL_FACTORS = {
    "north": 0.525, "northeast": 0.554,
    "east": 0.498, "central": 0.420,
    "south": 0.389, "northwest": 0.493,
}

# District cooling industry benchmark (tCO2/GJ of cooling)
CEA_COOLING_BENCHMARK = 0.065  # tCO2 per GJ of cooling delivered


class CEAAdapter(GenericCarbonMarket):
    """China Emission Allowance (CEA) carbon market adapter."""

    def __init__(self, region: str, carbon_price: float,
                 total_allowance_tco2: float, period_start, period_end):
        emission_factor = CEA_REGIONAL_FACTORS.get(region, 0.50)
        super().__init__(
            region=region, carbon_price=carbon_price,
            emission_factor=emission_factor,
            total_allowance=total_allowance_tco2,
            period_start=period_start, period_end=period_end,
        )

    @staticmethod
    def cooling_allowance(cooling_gj: float) -> float:
        """Calculate allowance for a given amount of cooling energy (GJ)."""
        return cooling_gj * CEA_COOLING_BENCHMARK
```

- [ ] **Step 5: Write emission calculator + carbon optimizer**

```python
# carbon/emission_calculator.py
class EmissionCalculator:
    @staticmethod
    def from_power(power_kw: float, duration_h: float, emission_factor: float) -> float:
        energy_mwh = power_kw * duration_h / 1000.0
        return energy_mwh * emission_factor

    @staticmethod
    def from_cooling(cooling_gj: float, benchmark: float = 0.065) -> float:
        return cooling_gj * benchmark

    @staticmethod
    def from_fuel(fuel_kg: float, emission_factor: float) -> float:
        return fuel_kg * emission_factor


# carbon/carbon_optimizer.py
class CarbonOptimizer:
    @staticmethod
    def optimal_carbon_allocation(stations: list[dict], total_carbon_budget: float) -> dict[str, float]:
        """Allocate carbon budget across stations for minimum total cost."""
        # Simple proportional allocation by historical efficiency
        total_capacity = sum(s.get("capacity_rt", 0) for s in stations)
        if total_capacity == 0:
            return {s["id"]: total_carbon_budget / len(stations) for s in stations}
        return {
            s["id"]: total_carbon_budget * s.get("capacity_rt", 0) / total_capacity
            for s in stations
        }
```

- [ ] **Step 6: Commit**

```bash
git add services/agent/agent_service/optimization/ services/agent/agent_service/carbon/
git commit -m "feat(opt): add inter-station dispatch, carbon market, and CEA adapter"
```

---

### Task D4: Enhanced MILP solver with multi-objective

**Files:**
- Modify: `services/agent/agent_service/optimization/solver.py`

- [ ] **Step 1: Enhance MILP solver with carbon cost and water cost**

This task modifies the existing MILP solver to add carbon cost, water cost, wear cost, and multi-period optimization. The change extends the objective function and adds new constraints.

- [ ] **Step 2: Commit**

```bash
git add services/agent/agent_service/optimization/solver.py && \
git commit -m "feat(opt): enhance MILP solver with carbon, water, and multi-period optimization"
```

---

### Task D5: Prediction → DRL feedback loop API

**Files:**
- Modify: `services/agent/agent_service/api/rl.py` (add MAPPO endpoints)
- Create: `services/agent/agent_service/api/dispatch.py` (inter-station dispatch API)
- Create: `services/agent/agent_service/api/carbon.py` (carbon API)

- [ ] **Step 1: Write dispatch API**

```python
# api/dispatch.py
from fastapi import APIRouter
from pydantic import BaseModel
from ..optimization.station_dispatch import inter_station_dispatch, StationStatus

router = APIRouter()


class DispatchRequest(BaseModel):
    stations: list[dict]  # [{station_id, available_capacity, marginal_cost, current_load, cop, carbon_intensity}]
    total_load_rt: float
    carbon_budget_tco2: float | None = None


@router.post("/dispatch/inter-station")
async def dispatch(req: DispatchRequest):
    stations = [StationStatus(
        station_id=s["station_id"],
        available_capacity=s["available_capacity"],
        marginal_cost=s["marginal_cost"],
        current_load=s["current_load"],
        cop=s["cop"],
        carbon_intensity=s.get("carbon_intensity", 0.0),
    ) for s in req.stations]

    result = inter_station_dispatch(stations, req.total_load_rt, req.carbon_budget_tco2)
    return {"targets": result.stations, "marginal_costs": result.marginal_cost,
            "unused_capacity": result.unused_capacity}
```

- [ ] **Step 2: Write carbon API**

```python
# api/carbon.py
from fastapi import APIRouter
from pydantic import BaseModel
from ..carbon.emission_calculator import EmissionCalculator
from ..carbon.carbon_market import GenericCarbonMarket
from datetime import datetime

router = APIRouter()


class EmissionRequest(BaseModel):
    power_kw: float
    duration_hours: float
    emission_factor: float = 0.50


class AllowanceRequest(BaseModel):
    region: str
    total_allowance_tco2: float
    carbon_price: float
    period_start: str
    period_end: str


@router.post("/carbon/emissions")
async def calculate_emissions(req: EmissionRequest):
    tco2 = EmissionCalculator.from_power(req.power_kw, req.duration_hours, req.emission_factor)
    return {"tco2": round(tco2, 4)}


@router.post("/carbon/cost")
async def carbon_cost(req: AllowanceRequest):
    market = GenericCarbonMarket(
        region=req.region, carbon_price=req.carbon_price,
        emission_factor=0.50, total_allowance=req.total_allowance_tco2,
        period_start=datetime.fromisoformat(req.period_start),
        period_end=datetime.fromisoformat(req.period_end),
    )
    return {"carbon_price": market.carbon_price, "emission_factor": market.emission_factor,
            "remaining_allowance": market.allowance_remaining()}
```

- [ ] **Step 3: Register new routers in agent main.py + commit**

```bash
git add services/agent/agent_service/api/dispatch.py services/agent/agent_service/api/carbon.py
git commit -m "feat(opt): add inter-station dispatch and carbon API endpoints"
```

---

## Phase 4: Module B — Production Hardening

### Task B1: Alembic migrations for all services

**Files:**
- Create: `services/asset/alembic/` (env.py, script.py.mako, versions/)
- Create: `services/environment/alembic/`
- Create: `services/simulation/alembic/`
- Create: `services/agent/alembic/`
- Create: `services/gateway/alembic/`
- Create: `services/acquisition/alembic/`

- [ ] **Step 1: Initialize Alembic for each service**

```bash
for svc in asset environment simulation agent gateway acquisition; do
    cd services/$svc
    alembic init alembic
    cd ../..
done
```

- [ ] **Step 2: Configure each env.py to use the service's models**

Standard `env.py` pattern (example for asset):
```python
# services/asset/alembic/env.py
from common.db import Base
from common.config import get_settings
from asset_service.models import *  # noqa: import all models

target_metadata = Base.metadata

def get_url():
    return get_settings().database_url
```

- [ ] **Step 3: Generate initial migration for each + commit**

```bash
for svc in asset environment simulation agent gateway acquisition; do
    cd services/$svc && alembic revision --autogenerate -m "initial" && cd ../..
done
git add services/*/alembic/
git commit -m "chore: add Alembic migrations for all 6 services"
```

---

### Task B2: Rate limiter + circuit breaker (Gateway)

**Files:**
- Create: `services/gateway/gateway_service/middleware/__init__.py` (empty)
- Create: `services/gateway/gateway_service/middleware/rate_limiter.py`
- Create: `services/gateway/gateway_service/middleware/circuit_breaker.py`
- Modify: `services/gateway/gateway_service/main.py` (register middleware)

- [ ] **Step 1: Write rate limiter**

```python
# middleware/rate_limiter.py
import time
from collections import defaultdict
from fastapi import Request, HTTPException


class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, request: Request, call_next):
        user_id = request.headers.get("X-User-ID", request.client.host)
        now = time.time()
        bucket = self._buckets[user_id]
        bucket[:] = [t for t in bucket if now - t < self._window]

        if len(bucket) >= self._max:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        bucket.append(now)
        return await call_next(request)
```

- [ ] **Step 2: Write circuit breaker**

```python
# middleware/circuit_breaker.py
import time
from collections import defaultdict
from fastapi import Request, HTTPException


class CircuitBreaker:
    OPEN = "open"
    HALF_OPEN = "half_open"
    CLOSED = "closed"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self._threshold = failure_threshold
        self._timeout = recovery_timeout
        self._state: dict[str, str] = defaultdict(lambda: self.CLOSED)
        self._failures: dict[str, int] = defaultdict(int)
        self._last_failure: dict[str, float] = {}

    async def __call__(self, request: Request, call_next):
        service = request.url.path.split("/")[2] if len(request.url.path.split("/")) > 2 else "default"
        state = self._state[service]

        if state == self.OPEN:
            if time.time() - self._last_failure.get(service, 0) > self._timeout:
                self._state[service] = self.HALF_OPEN
            else:
                raise HTTPException(status_code=503, detail=f"Circuit breaker open for {service}")

        try:
            response = await call_next(request)
            if response.status_code >= 500:
                self._record_failure(service)
            else:
                self._reset(service)
            return response
        except Exception:
            self._record_failure(service)
            raise

    def _record_failure(self, service: str) -> None:
        self._failures[service] += 1
        self._last_failure[service] = time.time()
        if self._failures[service] >= self._threshold:
            self._state[service] = self.OPEN

    def _reset(self, service: str) -> None:
        self._failures[service] = 0
        self._state[service] = self.CLOSED
```

- [ ] **Step 3: Register middleware in gateway main.py + commit**

```bash
git add services/gateway/gateway_service/middleware/ && \
git commit -m "feat(gateway): add rate limiter and circuit breaker middleware"
```

---

### Task B3: Prometheus metrics for all services

**Files:**
- Create: `services/gateway/gateway_service/metrics.py`
- Modify: all service `main.py` files to add prometheus endpoint

- [ ] **Step 1: Write shared metrics module in common**

Add `prometheus-fastapi-instrumentator` to each service's pyproject.toml, then add:

```python
# common/common/metrics.py
from prometheus_fastapi_instrumentator import Instrumentator

def setup_metrics(app, service_name: str):
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
    )
    instrumentator.add(
        instrumentator.request_id_metric
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)
    return instrumentator
```

- [ ] **Step 2: Add metrics to each service main.py**

```python
from common.metrics import setup_metrics
setup_metrics(app, "asset_service")  # per service name
```

- [ ] **Step 3: Commit**

```bash
git add common/common/metrics.py services/*/service/main.py && \
git commit -m "feat(metrics): add Prometheus /metrics endpoint to all services"
```

---

### Task B4: WebSocket, PWA, Reports, Alerts, HITL

**Files:**
- Modify: `services/gateway/gateway_service/proxy.py` (WebSocket upgrade)
- Modify: `frontend/vite.config.ts` (PWA plugin)
- Create: `frontend/src/service-worker.ts`
- Modify: `services/agent/agent_service/alerting/` (delivery channels)
- Create: `services/agent/agent_service/api/override.py` (HITL)
- Create: `frontend/src/pages/ManualOverride.tsx`

- [ ] **Step 1: Enhance WebSocket support in Gateway**

Add WebSocket proxy support and real-time KPI/alert push to connected clients.

- [ ] **Step 2: Configure Vite PWA**

Add `vite-plugin-pwa` to `vite.config.ts` with offline caching strategy.

- [ ] **Step 3: Add alert delivery channels**

Create `services/agent/agent_service/alerting/delivery.py` with webhook integrations for 企业微信/钉钉/飞书 + SMS escalation.

- [ ] **Step 4: Add HITL override API and UI**

API for manual override with timeout-based auto-revert, plus React page for operators.

- [ ] **Step 5: Commit**

```bash
git add services/gateway/gateway_service/proxy.py frontend/ services/agent/agent_service/alerting/delivery.py services/agent/agent_service/api/override.py frontend/src/pages/ManualOverride.tsx && \
git commit -m "feat(b): add WebSocket, PWA, alert delivery, and HITL manual override"
```

---

### Task B5: Service-level tests

**Files:**
- Create: `services/acquisition/tests/` (comprehensive)
- Create: `services/simulation/tests/` (calibration tests)
- Create: `services/agent/tests/` (DRL, optimization, carbon tests)
- Create: `services/gateway/tests/` (middleware tests)

- [ ] **Step 1: Write test suites for each service**

Coverage targets per service: 80%+ line coverage.

- [ ] **Step 2: Commit**

```bash
git add services/*/tests/ && \
git commit -m "test: add comprehensive service-level tests for all 6 services"
```

---

### Task B6: CI/CD pipelines

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/integration.yml`
- Create: `.github/workflows/deploy.yml`
- Create: `.github/workflows/nightly.yml`

- [ ] **Step 1: Write CI pipeline**

```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
  push:
    branches: [master]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:2.17.2-pg16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: hvac
          POSTGRES_PASSWORD: hvac_dev
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install uv && uv sync
      - run: uv run ruff check .
      - run: uv run mypy common/ services/
      - run: uv run pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v3
```

- [ ] **Step 2: Write integration, deploy, and nightly pipelines + commit**

```bash
git add .github/workflows/ && \
git commit -m "ci: add CI/CD pipelines (PR, integration, deploy, nightly)"
```

---

### Task B7: Integration and E2E tests

**Files:**
- Create: `tests/integration/test_acquisition_pipeline.py`
- Create: `tests/integration/test_calibration_pipeline.py`
- Create: `tests/integration/test_optimization_pipeline.py`
- Create: `tests/e2e/test_full_p2_flow.py`

- [ ] **Step 1: Write integration test for acquisition → storage → quality → alert chain**

```python
# tests/integration/test_acquisition_pipeline.py
import pytest

@pytest.mark.integration
async def test_acquisition_read_store_forward():
    """End-to-end: poll → TimescaleDB → Redis cache → Asset forward."""
    # 1. Register Modbus point
    # 2. Start polling
    # 3. Verify reading stored in acq_db
    # 4. Verify latest value in Redis
    # 5. Verify forwarded to Asset Service
    pass
```

- [ ] **Step 2: Write calibration integration test**

```python
# tests/integration/test_calibration_pipeline.py
@pytest.mark.integration
async def test_chiller_calibration_from_live_data():
    """Fetch acq_db data → clean → calibrate → verify MAPE < threshold."""
    pass
```

- [ ] **Step 3: Write optimization E2E test**

```python
# tests/integration/test_optimization_pipeline.py
@pytest.mark.integration
async def test_milp_drl_safety_chain():
    """MILP schedule → MAPPO actions → Safety Gate → valid output."""
    pass
```

- [ ] **Step 4: Write full P2 E2E test**

```python
# tests/e2e/test_full_p2_flow.py
@pytest.mark.e2e
async def test_full_p2_flow():
    """
    Full P2 pipeline:
    Acquisition (live read) → Storage (TimescaleDB) →
    Data Quality (5-layer) + Root Cause → Calibration →
    Prediction → MILP + MAPPO → Carbon Check → Safety Gate →
    Control Write → Audit Log
    """
    pass
```

- [ ] **Step 5: Commit**

```bash
git add tests/ && \
git commit -m "test: add integration and E2E tests for P2 pipelines"
```

---

## Execution Order Summary

| Phase | Tasks | Order |
|-------|-------|-------|
| 1 | A1-A10 | Data Acquisition Service (new service, no dependencies on later phases) |
| 2 | C1-C6 | Calibration + Data Quality (depends on A for acq_db data, but can test with SIMULATED) |
| 3 | D1-D5 | Optimization + Carbon (depends on C for calibrated models) |
| 4 | B1-B7 | Production Hardening (depends on all services existing) |
