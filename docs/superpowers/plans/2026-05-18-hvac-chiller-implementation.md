# HVAC 制冷站多智能体系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零构建 HVAC 制冷站多智能体系统——仿真层、联合优化引擎、10 Agent LangGraph 编排、RL 审核引擎、报告子系统、2D 可视化

**Architecture:** 先粗后细，16 个 Phase 从基础设施到功能逐层构建。每个 Phase 内部遵循 TDD（先写测试→失败→实现→通过→提交）。Phase 0-5 搭建骨架（schemas、仿真、曲线、优化引擎、Agent 框架），Phase 6-13 实现具体 Agent 和功能，Phase 14-16 控制层、API 和集成。

**Tech Stack:** Python 3.11, uv, LangGraph, FastAPI, TimescaleDB, Redis, React+ECharts

**Spec:** `docs/superpowers/specs/2026-05-18-hvac-chiller-multi-agent-design.md`

---

## 文件结构总览

```
hvac-agents/
├── src/
│   ├── config.py                    # 全局配置
│   ├── schemas/                     # Pydantic 数据模型（系统的"语言"）
│   │   ├── equipment.py             # 设备、冷机、水泵、冷却塔
│   │   ├── state.py                 # AgentState、辩论状态
│   │   ├── strategy.py              # 策略、动作、过渡计划
│   │   └── review.py                # 审查意见、仲裁结果
│   ├── simulation/                  # L2 仿真层
│   │   ├── chiller.py               # 离心冷机物理模型
│   │   ├── cooling_tower.py         # 冷却塔（Merkel 理论）
│   │   ├── pump.py                  # 水泵（相似定律）
│   │   ├── plant.py                 # 制冷站：组合所有设备
│   │   └── building_thermal.py      # 建筑热工 RC 网络模型
│   ├── curves/                      # 性能曲线管理
│   │   ├── surrogate.py             # 多项式代理模型拟合
│   │   └── online_id.py             # 在线参数辨识（RLS）
│   ├── optimization/                # 联合优化引擎
│   │   ├── objective.py             # 目标函数
│   │   ├── constraints.py           # 约束条件
│   │   ├── solver.py                # MINLP 求解器封装
│   │   └── pareto.py                # 帕累托前沿
│   ├── agents/                      # Agent 实现
│   │   ├── base.py                  # 基础 Agent、LLM 客户端工厂
│   │   ├── monitor.py               # 监测 Agent
│   │   ├── predict.py               # 预测 Agent
│   │   ├── strategy.py              # 策略 Agent
│   │   ├── advocates/
│   │   │   ├── reliability.py       # 可靠性 Advocate
│   │   │   ├── efficiency.py        # 效率 Advocate
│   │   │   └── compliance.py        # 合规 Advocate
│   │   ├── coordinator.py           # 协调 Agent
│   │   ├── safety.py                # 安全 Agent（规则引擎）
│   │   ├── parameter.py             # 参数 Agent
│   │   └── report.py                # 报告 Agent
│   ├── graph/                       # LangGraph 工作流
│   │   ├── setup.py                 # 图构建
│   │   ├── conditional_logic.py     # 条件路由
│   │   └── debate.py                # 辩论编排
│   ├── rl/                          # RL 审核引擎
│   │   ├── bandit.py                # Contextual Bandit
│   │   ├── features.py              # 状态特征提取
│   │   └── trainer.py               # 离线训练
│   ├── memory/                      # 记忆与反思
│   │   ├── log.py                   # Memory Log
│   │   └── reflection.py            # LLM 反思
│   ├── reports/                     # 报告生成
│   │   ├── kpi_calculator.py        # KPI 计算
│   │   ├── generator.py             # 报告管线
│   │   └── renderer.py              # 多格式渲染
│   ├── rag/                         # RAG 标准查询
│   │   ├── loader.py                # 文档加载
│   │   └── retriever.py             # 向量检索
│   ├── control/                     # L3 实时控制层
│   │   ├── pid.py                   # PID 控制器
│   │   ├── deadband.py              # 死区 + 速率限制
│   │   └── interlock.py             # 设备启动联锁序列
│   ├── messaging/                   # 消息总线
│   │   └── bus.py                   # Redis 事件总线
│   └── api/                         # FastAPI 后端
│       ├── main.py                  # 应用入口
│       ├── monitoring.py            # 实时监测端点
│       ├── strategy.py              # 策略管理端点
│       └── reports.py               # 报告端点
├── tests/                           # 镜像 src/ 结构
│   ├── conftest.py                  # 共享 fixtures
│   ├── simulation/
│   ├── curves/
│   ├── optimization/
│   ├── agents/
│   ├── graph/
│   ├── rl/
│   ├── reports/
│   ├── control/
│   └── integration/
├── main.py                          # 入口
└── pyproject.toml
```

---

### Phase 0: 项目基础设施

#### Task 0.1: 项目配置与依赖

**Files:**
- Modify: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 更新 pyproject.toml 添加所有依赖**

```toml
[project]
name = "hvac-agents"
version = "0.1.0"
description = "HVAC Chiller Plant Multi-Agent System"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "langchain>=0.3.0",
    "langgraph>=0.2.0",
    "langchain-anthropic>=0.3.0",
    "langchain-openai>=0.3.0",
    "pydantic>=2.0",
    "numpy>=1.26",
    "scipy>=1.12",
    "pandas>=2.2",
    "scikit-learn>=1.4",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "redis>=5.0",
    "celery>=5.4",
    "psycopg2-binary>=2.9",
    "sqlalchemy>=2.0",
    "jinja2>=3.1",
    "weasyprint>=62",
    "openpyxl>=3.1",
    "httpx>=0.27",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.6",
]
```

- [ ] **Step 2: 安装依赖并验证**

```bash
cd /Users/ymilitarym/hp-2026/hvac-agents
uv sync
uv run python -c "import langgraph; import pydantic; print('Deps OK')"
```
Expected: `Deps OK`

- [ ] **Step 3: 创建全局配置模块**

```python
# src/config.py
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    provider: str = "anthropic"        # anthropic | openai | google
    deep_model: str = "claude-sonnet-4-6"
    quick_model: str = "claude-haiku-4-5-20251001"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_debate_rounds: int = 2
    max_risk_discuss_rounds: int = 1


@dataclass
class SimulationConfig:
    plant_config_path: str = "config/plant.toml"
    weather_data_path: str = "data/weather"
    data_generation_samples: int = 5000


@dataclass
class OptimizationConfig:
    solver_timeout_sec: float = 30.0
    pareto_max_solutions: int = 5
    wear_cost_per_start: dict = field(default_factory=lambda: {
        "chiller": 150.0,    # 元/次
        "pump": 30.0,
        "cooling_tower": 20.0,
    })
    electricity_price_file: str = "config/price.toml"
    carbon_price_per_kg: float = 0.08   # 元/kgCO2


@dataclass
class StorageConfig:
    db_url: str = "postgresql://localhost:5432/hvac"
    redis_url: str = "redis://localhost:6379/0"
    timeseries_table: str = "sensor_data"


@dataclass
class RLConfig:
    algorithm: str = "contextual_bandit"
    model_path: str = "models/rl_ reviewer.pkl"
    confidence_threshold: float = 0.85    # 高于此值自动批准
    training_interval_days: int = 7


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    rl: RLConfig = field(default_factory=RLConfig)
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "anthropic"),
                api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("LLM_BASE_URL"),
            ),
            debug=os.getenv("DEBUG", "").lower() == "true",
        )


_default_config = Config()


def get_config() -> Config:
    return _default_config


def set_config(cfg: Config) -> None:
    global _default_config
    _default_config = cfg
```

- [ ] **Step 4: 创建测试夹具**

```python
# tests/conftest.py
import pytest
from src.config import Config, get_config, set_config


@pytest.fixture
def test_config():
    """提供测试用配置，LLM 调用会被 mock"""
    cfg = Config(debug=True)
    cfg.llm.provider = "mock"
    set_config(cfg)
    yield cfg
    set_config(Config())


@pytest.fixture
def sample_plant_params():
    """标准中型制冷站参数"""
    return {
        "num_chillers": 3,
        "num_cooling_towers": 3,
        "num_chw_pumps": 3,
        "num_cw_pumps": 3,
        "chiller_capacity_rt": 500,         # 每台 500 冷吨
        "design_chw_supply_temp": 7.0,      # °C
        "design_chw_return_temp": 12.0,
        "design_cw_supply_temp": 32.0,
        "design_cw_return_temp": 37.0,
        "design_wet_bulb_temp": 28.0,
    }
```

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml src/__init__.py src/config.py tests/__init__.py tests/conftest.py
git commit -m "chore: project scaffolding with config and test fixtures"
```

---

### Phase 1: 数据 Schemas（系统的类型语言）

#### Task 1.1: 设备数据模型

**Files:**
- Create: `src/schemas/__init__.py`
- Create: `src/schemas/equipment.py`
- Create: `tests/schemas/__init__.py`
- Create: `tests/schemas/test_equipment.py`

- [ ] **Step 1: 写设备模型的测试**

```python
# tests/schemas/test_equipment.py
import pytest
from src.schemas.equipment import (
    EquipmentStatus, ChillerState, PumpState,
    CoolingTowerState, PlantSnapshot,
)


class TestChillerState:
    def test_chiller_state_defaults(self):
        s = ChillerState(device_id="chiller_1", capacity_rt=500)
        assert s.status == EquipmentStatus.OFF
        assert s.current_load_rt == 0.0
        assert s.chw_supply_temp == 7.0
        assert s.is_running is False

    def test_chiller_cop_calculation(self):
        s = ChillerState(
            device_id="chiller_1",
            capacity_rt=500,
            status=EquipmentStatus.RUNNING,
            current_load_rt=375,       # 75% load
            power_kw=75.0,             # 375RT / 75kW = COP 17.6 approximate, let's adjust
            chw_supply_temp=7.0,
            chw_return_temp=12.0,
            cw_entering_temp=30.0,
            cw_leaving_temp=35.0,
        )
        # power_kw = load_kw / cop
        # load_kw = load_rt * 3.517 (kW per RT)
        # cop = load_kw / power_kw = 375*3.517/75 = 17.6
        assert s.power_kw == 75.0
        assert abs(s.instant_cop - (375 * 3.517 / 75)) < 0.1

    def test_chiller_surge_risk(self):
        s = ChillerState(
            device_id="chiller_1",
            capacity_rt=500,
            status=EquipmentStatus.RUNNING,
            current_load_rt=100,       # 20% — near surge
            chw_supply_temp=7.0,
            cw_entering_temp=32.0,     # high condensing temp
        )
        # surge risk increases with low PLR and high condensing temp
        assert s.surge_risk > 0.5


class TestPlantSnapshot:
    def test_plant_snapshot_creation(self, sample_plant_params):
        p = sample_plant_params
        snap = PlantSnapshot(
            chillers={
                f"chiller_{i+1}": ChillerState(
                    device_id=f"chiller_{i+1}",
                    capacity_rt=p["chiller_capacity_rt"],
                    status=EquipmentStatus.RUNNING,
                    current_load_rt=350,
                    power_kw=70,
                )
                for i in range(p["num_chillers"])
            },
            cooling_towers={
                f"tower_{i+1}": CoolingTowerState(
                    device_id=f"tower_{i+1}", fan_speed_hz=40
                )
                for i in range(p["num_cooling_towers"])
            },
            chw_pumps={
                f"chw_pump_{i+1}": PumpState(
                    device_id=f"chw_pump_{i+1}", speed_hz=45
                )
                for i in range(p["num_chw_pumps"])
            },
            cw_pumps={
                f"cw_pump_{i+1}": PumpState(
                    device_id=f"cw_pump_{i+1}", speed_hz=45
                )
                for i in range(p["num_cw_pumps"])
            },
            outdoor_wb_temp=26.0,
            outdoor_db_temp=33.0,
        )
        assert snap.total_cooling_load_rt > 0
        assert len(snap.running_chillers) == 3

    def test_plant_snapshot_from_dict(self, sample_plant_params):
        data = {
            "chillers": [
                {"device_id": "chiller_1", "capacity_rt": 500,
                 "status": "running", "current_load_rt": 375, "power_kw": 75,
                 "chw_supply_temp": 7.0, "chw_return_temp": 12.0,
                 "cw_entering_temp": 30.0, "cw_leaving_temp": 35.0},
            ],
            "chw_pumps": [
                {"device_id": "chw_pump_1", "status": "running", "speed_hz": 45},
            ],
            "cw_pumps": [
                {"device_id": "cw_pump_1", "status": "running", "speed_hz": 40},
            ],
            "cooling_towers": [
                {"device_id": "tower_1", "status": "running", "fan_speed_hz": 35},
            ],
            "outdoor_wb_temp": 26.0,
            "outdoor_db_temp": 33.0,
        }
        snap = PlantSnapshot.from_dict(data)
        assert snap.chillers["chiller_1"].status == EquipmentStatus.RUNNING
        assert snap.total_cooling_load_rt == 375
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/schemas/test_equipment.py -v
```
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 实现设备数据模型**

```python
# src/schemas/equipment.py
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, computed_field


class EquipmentStatus(str, Enum):
    OFF = "off"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAULT = "fault"
    MAINTENANCE = "maintenance"


class ChillerState(BaseModel):
    device_id: str
    capacity_rt: float                          # 额定制冷量（冷吨）
    status: EquipmentStatus = EquipmentStatus.OFF
    current_load_rt: float = 0.0                # 当前实际冷吨
    power_kw: float = 0.0                       # 当前功率 kW
    chw_supply_temp: float = 7.0                # 冷冻水供水温度 °C
    chw_return_temp: float = 12.0               # 冷冻水回水温度 °C
    cw_entering_temp: float = 30.0              # 冷却水进水温度 °C
    cw_leaving_temp: float = 35.0               # 冷却水出水温度 °C
    evap_flow_rate_lps: float = 0.0             # 蒸发器流量 L/s
    cond_flow_rate_lps: float = 0.0             # 冷凝器流量 L/s
    cumulative_starts: int = 0                  # 累计启动次数
    cumulative_run_hours: float = 0.0           # 累计运行小时
    last_start_time: Optional[float] = None     # 上次启动时间戳
    last_stop_time: Optional[float] = None      # 上次停机时间戳

    @computed_field
    @property
    def is_running(self) -> bool:
        return self.status == EquipmentStatus.RUNNING

    @computed_field
    @property
    def plr(self) -> float:
        """部分负荷率 Part Load Ratio"""
        if self.capacity_rt <= 0:
            return 0.0
        return self.current_load_rt / self.capacity_rt

    @computed_field
    @property
    def instant_cop(self) -> float:
        """瞬时 COP = 制冷量(kW) / 功率(kW)，1 RT ≈ 3.517 kW"""
        if self.power_kw <= 0:
            return 0.0
        return (self.current_load_rt * 3.517) / self.power_kw

    @computed_field
    @property
    def surge_risk(self) -> float:
        """喘振风险评估 0~1。低负荷 + 高冷凝温度 → 高风险"""
        if self.status != EquipmentStatus.RUNNING or self.plr <= 0:
            return 0.0
        cond_factor = max(0, (self.cw_entering_temp - 24) / 16)   # 24°C 基准
        load_penalty = max(0, (0.4 - self.plr) / 0.4)              # <40% PLR 开始风险
        risk = 0.3 * cond_factor + 0.7 * load_penalty
        return min(1.0, max(0.0, risk))


class PumpState(BaseModel):
    device_id: str
    status: EquipmentStatus = EquipmentStatus.OFF
    speed_hz: float = 0.0                       # 当前频率 Hz
    rated_power_kw: float = 37.0                # 额定功率 kW
    rated_flow_lps: float = 100.0               # 额定流量 L/s
    rated_head_m: float = 32.0                  # 额定扬程 m
    cumulative_starts: int = 0

    @computed_field
    @property
    def is_running(self) -> bool:
        return self.status == EquipmentStatus.RUNNING and self.speed_hz > 0

    @computed_field
    @property
    def power_kw(self) -> float:
        """相似定律：功率 ∝ (转速)^3"""
        if self.speed_hz <= 0 or self.rated_power_kw <= 0:
            return 0.0
        rated_hz = 50.0
        return self.rated_power_kw * (self.speed_hz / rated_hz) ** 3

    @computed_field
    @property
    def flow_lps(self) -> float:
        """相似定律：流量 ∝ 转速"""
        if self.speed_hz <= 0:
            return 0.0
        return self.rated_flow_lps * (self.speed_hz / 50.0)


class CoolingTowerState(BaseModel):
    device_id: str
    status: EquipmentStatus = EquipmentStatus.OFF
    fan_speed_hz: float = 0.0
    rated_fan_power_kw: float = 15.0
    water_in_temp: float = 35.0                 # 进水温度（来自冷凝器）
    water_out_temp: float = 30.0                # 出水温度（去冷凝器）
    water_flow_lps: float = 0.0

    @computed_field
    @property
    def is_running(self) -> bool:
        return self.status == EquipmentStatus.RUNNING

    @computed_field
    @property
    def approach_temp(self) -> float:
        """逼近度 = 出水温度 - 室外湿球温度"""
        return self.water_out_temp  # caller subtracts wet bulb

    @computed_field
    @property
    def fan_power_kw(self) -> float:
        if self.fan_speed_hz <= 0:
            return 0.0
        return self.rated_fan_power_kw * (self.fan_speed_hz / 50.0) ** 3


class PlantSnapshot(BaseModel):
    """制冷站某一时刻的完整状态快照"""
    chillers: Dict[str, ChillerState] = Field(default_factory=dict)
    cooling_towers: Dict[str, CoolingTowerState] = Field(default_factory=dict)
    chw_pumps: Dict[str, PumpState] = Field(default_factory=dict)
    cw_pumps: Dict[str, PumpState] = Field(default_factory=dict)
    outdoor_wb_temp: float = 26.0               # 室外湿球温度 °C
    outdoor_db_temp: float = 33.0               # 室外干球温度 °C
    timestamp: float = 0.0                      # Unix 时间戳

    @computed_field
    @property
    def total_cooling_load_rt(self) -> float:
        return sum(c.current_load_rt for c in self.chillers.values())

    @computed_field
    @property
    def total_power_kw(self) -> float:
        chiller_power = sum(c.power_kw for c in self.chillers.values())
        tower_power = sum(t.fan_power_kw for t in self.cooling_towers.values())
        pump_power = sum(p.power_kw for p in self.chw_pumps.values())
        pump_power += sum(p.power_kw for p in self.cw_pumps.values())
        return chiller_power + tower_power + pump_power

    @computed_field
    @property
    def system_cop(self) -> float:
        if self.total_power_kw <= 0:
            return 0.0
        return (self.total_cooling_load_rt * 3.517) / self.total_power_kw

    @computed_field
    @property
    def running_chillers(self) -> List[ChillerState]:
        return [c for c in self.chillers.values() if c.is_running]

    @classmethod
    def from_dict(cls, data: dict) -> "PlantSnapshot":
        return cls(
            chillers={c["device_id"]: ChillerState(**c) for c in data.get("chillers", [])},
            cooling_towers={t["device_id"]: CoolingTowerState(**t) for t in data.get("cooling_towers", [])},
            chw_pumps={p["device_id"]: PumpState(**p) for p in data.get("chw_pumps", [])},
            cw_pumps={p["device_id"]: PumpState(**p) for p in data.get("cw_pumps", [])},
            outdoor_wb_temp=data.get("outdoor_wb_temp", 26.0),
            outdoor_db_temp=data.get("outdoor_db_temp", 33.0),
            timestamp=data.get("timestamp", 0.0),
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/schemas/test_equipment.py -v
```
Expected: PASS (all tests)

- [ ] **Step 5: 提交**

```bash
git add src/schemas/ tests/schemas/
git commit -m "feat: add equipment data schemas (ChillerState, PumpState, PlantSnapshot)"
```

#### Task 1.2: 策略与审查数据模型

**Files:**
- Create: `src/schemas/strategy.py`
- Create: `src/schemas/review.py`
- Create: `tests/schemas/test_strategy.py`

- [ ] **Step 1: 写策略与审查模型的测试**

```python
# tests/schemas/test_strategy.py
import pytest
from src.schemas.strategy import (
    Strategy, StrategyAction, StrategyStatus,
    TransitionPlan, TransitionPhase, TriggerType,
)
from src.schemas.review import AdvocateOpinion, ReviewVerdict, ArbitrationResult


class TestStrategyAction:
    def test_discrete_action(self):
        a = StrategyAction(
            seq=1, device="chiller_2", action="stop"
        )
        assert a.is_discrete is True
        assert a.is_continuous is False

    def test_continuous_action(self):
        a = StrategyAction(
            seq=2, device="pump_3", action="set_frequency", value=35.0
        )
        assert a.is_continuous is True
        assert a.value == 35.0


class TestTransitionPlan:
    def test_minimal_transition(self):
        plan = TransitionPlan(
            total_duration_sec=300,
            phases=[
                TransitionPhase(
                    seq=1, duration_sec=120,
                    description="Ramp down chiller_2 to 30%",
                    actions=[
                        StrategyAction(seq=1, device="chiller_2",
                                       action="ramp_load", value=0.3, rate=0.0025)
                    ],
                ),
                TransitionPhase(
                    seq=2, duration_sec=180,
                    description="Stability check",
                    actions=[],
                    stability_check={"metric": "chw_supply_temp",
                                     "max_deviation": 0.3, "window_sec": 60},
                ),
            ],
            abort_conditions=["chw_supply_temp deviation > 1.5°C"],
        )
        assert plan.total_duration_sec == 300
        assert len(plan.phases) == 2


class TestStrategy:
    def test_strategy_lifecycle(self):
        s = Strategy(
            strategy_id="test_001",
            trigger_type=TriggerType.SCHEDULED,
            trigger_time=1716000000.0,
            current_load_rt=850,
            predicted_load_rt=520,
            actions=[
                StrategyAction(seq=1, device="chiller_2", action="stop"),
            ],
            transition_plan=TransitionPlan(
                total_duration_sec=120,
                phases=[
                    TransitionPhase(
                        seq=1, duration_sec=120,
                        description="Stop chiller_2",
                        actions=[
                            StrategyAction(seq=1, device="chiller_2", action="stop"),
                        ],
                    ),
                ],
                abort_conditions=[],
            ),
            preconditions=["total_load < 550RT"],
            expected_cop_improvement=0.12,
            expected_energy_saving_kwh_per_h=120,
        )
        assert s.status == StrategyStatus.DRAFT
        s.status = StrategyStatus.UNDER_REVIEW
        assert s.status == StrategyStatus.UNDER_REVIEW
        s.status = StrategyStatus.APPROVED
        assert s.is_approved
        s.status = StrategyStatus.REJECTED
        assert s.is_terminal

    def test_strategy_requires_transition_for_load_following(self):
        """负荷跟随类策略必须有过渡计划"""
        with pytest.raises(ValueError, match="transition_plan"):
            Strategy(
                strategy_id="test_002",
                trigger_type=TriggerType.LOAD_CHANGE,
                trigger_time=1716000000.0,
                current_load_rt=850,
                predicted_load_rt=520,
                actions=[
                    StrategyAction(seq=1, device="chiller_2", action="stop"),
                ],
                # 缺少 transition_plan
            )


class TestAdvocateOpinion:
    def test_approval_opinion(self):
        op = AdvocateOpinion(
            advocate="reliability",
            verdict=ReviewVerdict.CONDITIONAL_APPROVAL,
            concerns=["需监控出水温度"],
            confidence=0.82,
        )
        assert op.is_positive
        assert not op.is_rejection

    def test_rejection_opinion(self):
        op = AdvocateOpinion(
            advocate="compliance",
            verdict=ReviewVerdict.REJECT,
            concerns=["碳排放超标", "不符合配额要求"],
            confidence=0.78,
        )
        assert op.is_rejection


class TestArbitrationResult:
    def test_unanimous_approval(self):
        opinions = [
            AdvocateOpinion(advocate="reliability", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.9),
            AdvocateOpinion(advocate="efficiency", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.85),
            AdvocateOpinion(advocate="compliance", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.88),
        ]
        result = ArbitrationResult.from_opinions(opinions)
        assert result.decision == "approved"
        assert result.has_conflict is False

    def test_conflicting_opinions(self):
        opinions = [
            AdvocateOpinion(advocate="reliability", verdict=ReviewVerdict.REJECT,
                           concerns=["安全风险"], confidence=0.9),
            AdvocateOpinion(advocate="efficiency", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.85),
            AdvocateOpinion(advocate="compliance", verdict=ReviewVerdict.APPROVE,
                           concerns=[], confidence=0.7),
        ]
        result = ArbitrationResult.from_opinions(opinions)
        assert result.has_conflict is True
        assert "reliability" in result.conflicting_parties
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/schemas/test_strategy.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现策略与审查模型**

```python
# src/schemas/strategy.py
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class TriggerType(str, Enum):
    SCHEDULED = "scheduled"
    LOAD_CHANGE = "load_change"
    FAULT = "fault"
    PRICE_SIGNAL = "price_signal"
    MANUAL = "manual"


class StrategyStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ABORTED = "aborted"


class StrategyAction(BaseModel):
    seq: int
    device: str
    action: str                         # start | stop | set_frequency | set_setpoint | ramp_load | open_valve | close_valve
    param: Optional[str] = None         # e.g., "chw_temp", "speed"
    value: Optional[float] = None       # target value for continuous actions
    rate: Optional[float] = None        # ramp rate for ramp actions
    from_val: Optional[float] = None    # start value for ramp
    to_val: Optional[float] = None      # end value for ramp

    @property
    def is_discrete(self) -> bool:
        return self.action in ("start", "stop", "open_valve", "close_valve")

    @property
    def is_continuous(self) -> bool:
        return not self.is_discrete


class TransitionPhase(BaseModel):
    seq: int
    duration_sec: float
    description: str
    actions: List[StrategyAction] = Field(default_factory=list)
    stability_check: Optional[Dict[str, Any]] = None


class TransitionPlan(BaseModel):
    total_duration_sec: float
    phases: List[TransitionPhase]
    abort_conditions: List[str] = Field(default_factory=list)
    rollback_actions: List[StrategyAction] = Field(default_factory=list)


class Strategy(BaseModel):
    strategy_id: str
    trigger_type: TriggerType
    trigger_time: float = 0.0

    # Context
    current_load_rt: float = 0.0
    predicted_load_rt: float = 0.0
    load_ci_lower: Optional[float] = None
    load_ci_upper: Optional[float] = None
    outdoor_wb_temp: float = 26.0
    electricity_price: float = 0.8
    carbon_intensity: float = 0.5

    # Actions
    actions: List[StrategyAction]
    transition_plan: Optional[TransitionPlan] = None

    # Expected effects
    expected_cop_improvement: Optional[float] = None
    expected_energy_saving_kwh_per_h: Optional[float] = None
    expected_carbon_saving_kg_per_h: Optional[float] = None
    expected_cost_saving_yuan_per_h: Optional[float] = None

    # Safety
    preconditions: List[str] = Field(default_factory=list)
    risk_mitigations: List[str] = Field(default_factory=list)

    # Lifecycle
    status: StrategyStatus = StrategyStatus.DRAFT
    llm_reasoning: str = ""

    @model_validator(mode="after")
    def validate_transition_required(self):
        if self.trigger_type in (
            TriggerType.LOAD_CHANGE, TriggerType.SCHEDULED,
            TriggerType.PRICE_SIGNAL, TriggerType.MANUAL,
        ):
            if self.transition_plan is None and len(self.actions) > 0:
                raise ValueError(
                    f"Strategy with trigger_type={self.trigger_type.value} "
                    f"requires a transition_plan"
                )
        return self

    @property
    def is_approved(self) -> bool:
        return self.status == StrategyStatus.APPROVED

    @property
    def is_terminal(self) -> bool:
        return self.status in (StrategyStatus.COMPLETED, StrategyStatus.REJECTED,
                               StrategyStatus.ABORTED)

    def approve(self) -> None:
        if self.status != StrategyStatus.UNDER_REVIEW:
            raise ValueError(f"Cannot approve strategy in status {self.status}")
        self.status = StrategyStatus.APPROVED

    def reject(self, reason: str = "") -> None:
        self.status = StrategyStatus.REJECTED
        if reason:
            self.llm_reasoning += f"\nRejection reason: {reason}"
```

```python
# src/schemas/review.py
from enum import Enum
from typing import List, Optional, Set
from pydantic import BaseModel, Field


class ReviewVerdict(str, Enum):
    APPROVE = "approve"
    CONDITIONAL_APPROVAL = "conditional_approval"
    REJECT = "reject"
    ABSTAIN = "abstain"


class AdvocateOpinion(BaseModel):
    advocate: str                        # "reliability" | "efficiency" | "compliance"
    verdict: ReviewVerdict
    concerns: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    confidence: float = 0.5              # 0~1

    @property
    def is_positive(self) -> bool:
        return self.verdict in (ReviewVerdict.APPROVE, ReviewVerdict.CONDITIONAL_APPROVAL)

    @property
    def is_rejection(self) -> bool:
        return self.verdict == ReviewVerdict.REJECT


class ArbitrationResult(BaseModel):
    decision: str                        # "approved" | "approved_with_conditions" | "rejected"
    reasoning: str = ""
    conditions: List[str] = Field(default_factory=list)
    has_conflict: bool = False
    conflicting_parties: Set[str] = Field(default_factory=set)
    debate_needed: bool = False
    debate_topic: str = ""

    @classmethod
    def from_opinions(cls, opinions: List[AdvocateOpinion]) -> "ArbitrationResult":
        rejections = [o for o in opinions if o.is_rejection]
        conditions = [o for o in opinions if o.verdict == ReviewVerdict.CONDITIONAL_APPROVAL]

        if rejections:
            return cls(
                decision="rejected" if len(rejections) >= 2 else "under_debate",
                reasoning=f"{len(rejections)} advocate(s) rejected",
                has_conflict=len(rejections) < 3 and len(rejections) > 0,
                conflicting_parties={o.advocate for o in rejections},
                debate_needed=len(rejections) == 1,
                debate_topic="reliability vs efficiency" if len(rejections) == 1 else "",
            )

        all_conditions = [c for o in conditions for c in o.concerns]
        return cls(
            decision="approved" if not conditions else "approved_with_conditions",
            reasoning="Unanimous approval" if not conditions else f"Approved with {len(conditions)} condition(s)",
            conditions=all_conditions,
            has_conflict=False,
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/schemas/test_strategy.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/schemas/strategy.py src/schemas/review.py tests/schemas/test_strategy.py
git commit -m "feat: add strategy and review schemas"
```

---

### Phase 2: 仿真层

#### Task 2.1: 冷机物理模型

**Files:**
- Create: `src/simulation/__init__.py`
- Create: `src/simulation/chiller.py`
- Create: `tests/simulation/__init__.py`
- Create: `tests/simulation/test_chiller.py`

- [ ] **Step 1: 写冷机模型测试**

```python
# tests/simulation/test_chiller.py
import pytest
import numpy as np
from src.simulation.chiller import CentrifugalChiller


class TestCentrifugalChiller:
    @pytest.fixture
    def chiller(self):
        return CentrifugalChiller(
            name="chiller_1",
            capacity_rt=500,
            design_cop=6.0,
            design_chw_supply_temp=7.0,
            design_cw_entering_temp=30.0,
            min_plr=0.2,                # 喘振边界 20%
        )

    def test_full_load_cop(self, chiller):
        cop = chiller.compute_cop(plr=1.0, t_chw=7.0, t_cw=30.0)
        # At design conditions, COP should be close to design
        assert abs(cop - 6.0) < 0.1

    def test_cop_decreases_with_high_condenser_temp(self, chiller):
        cop_cool = chiller.compute_cop(plr=1.0, t_chw=7.0, t_cw=30.0)
        cop_hot = chiller.compute_cop(plr=1.0, t_chw=7.0, t_cw=35.0)
        assert cop_hot < cop_cool

    def test_cop_increases_with_higher_chw_temp(self, chiller):
        cop_low = chiller.compute_cop(plr=1.0, t_chw=5.0, t_cw=30.0)
        cop_high = chiller.compute_cop(plr=1.0, t_chw=9.0, t_cw=30.0)
        assert cop_high > cop_low

    def test_cop_curve_has_peak(self, chiller):
        """COP peak should be around 60-80% PLR"""
        cops = [chiller.compute_cop(plr=p, t_chw=7.0, t_cw=30.0)
                for p in np.linspace(0.3, 1.0, 8)]
        peak_idx = np.argmax(cops)
        # Peak should not be at min or max — should be in the middle
        assert 1 <= peak_idx <= 6

    def test_below_surge_boundary_returns_zero(self, chiller):
        """Below min PLR, COP should be 0 (infeasible)"""
        cop = chiller.compute_cop(plr=0.15, t_chw=7.0, t_cw=30.0)
        assert cop == 0.0

    def test_surge_boundary_increases_with_tcw(self, chiller):
        """Higher condensing temp → higher min PLR"""
        boundary_cool = chiller.surge_boundary(t_cw=28.0)
        boundary_hot = chiller.surge_boundary(t_cw=35.0)
        assert boundary_hot > boundary_cool

    def test_power_calculation(self, chiller):
        """P = Load(kW) / COP"""
        load_rt = 375                      # 75% of 500RT
        cop = chiller.compute_cop(plr=0.75, t_chw=7.0, t_cw=30.0)
        expected_power = (load_rt * 3.517) / cop
        power = chiller.compute_power_kw(load_rt=load_rt, t_chw=7.0, t_cw=30.0)
        assert abs(power - expected_power) < 0.1

    def test_capacity_range(self, chiller):
        min_cap = chiller.min_capacity_rt(t_cw=30.0)
        max_cap = chiller.max_capacity_rt
        assert min_cap == 100.0            # 20% × 500
        assert max_cap == 500.0            # 100% × 500
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/simulation/test_chiller.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现冷机物理模型**

```python
# src/simulation/chiller.py
import numpy as np


class CentrifugalChiller:
    """离心式冷水机组物理模型 — 逆卡诺循环 + 经验效率修正"""

    def __init__(
        self,
        name: str,
        capacity_rt: float,
        design_cop: float = 6.0,
        design_chw_supply_temp: float = 7.0,
        design_cw_entering_temp: float = 30.0,
        min_plr: float = 0.2,
    ):
        self.name = name
        self.capacity_rt = capacity_rt
        self.design_cop = design_cop
        self.design_chw_supply_temp = design_chw_supply_temp
        self.design_cw_entering_temp = design_cw_entering_temp
        self.min_plr_base = min_plr

    def surge_boundary(self, t_cw: float) -> float:
        """喘振边界 — 冷凝温度越高，最低允许 PLR 越高"""
        delta_t = max(0, (t_cw - self.design_cw_entering_temp))
        boundary = self.min_plr_base + delta_t * 0.015
        return min(0.5, max(self.min_plr_base, boundary))

    def min_capacity_rt(self, t_cw: float) -> float:
        return self.surge_boundary(t_cw) * self.capacity_rt

    @property
    def max_capacity_rt(self) -> float:
        return self.capacity_rt * 1.0

    def compute_cop(self, plr: float, t_chw: float, t_cw: float) -> float:
        """计算给定工况下的 COP

        COP(P, T_e, T_c) = COP_design × f_load(P) × f_evap(T_e) × f_cond(T_c)

        where:
          f_load: 部分负荷修正，峰值在 70% 左右
          f_evap: 蒸发温度修正，T_chw 越高 COP 越高
          f_cond: 冷凝温度修正，T_cw 越高 COP 越低
        """
        if plr < self.surge_boundary(t_cw):
            return 0.0                     # 喘振区，不可运行

        # 部分负荷修正：峰值在 PLR ≈ 0.75
        f_load = 1.0 - 1.2 * (plr - 0.75) ** 2

        # 蒸发温度修正：T_chw 每升高 1°C，COP 提升约 3%
        f_evap = 1.0 + 0.03 * (t_chw - self.design_chw_supply_temp)

        # 冷凝温度修正：T_cw 每升高 1°C，COP 降低约 2.5%
        f_cond = 1.0 - 0.025 * (t_cw - self.design_cw_entering_temp)

        cop = self.design_cop * f_load * f_evap * f_cond
        return max(0.0, cop)

    def compute_power_kw(self, load_rt: float, t_chw: float, t_cw: float) -> float:
        """计算功率 kW = 冷量(kW) / COP"""
        plr = load_rt / self.capacity_rt if self.capacity_rt > 0 else 0
        cop = self.compute_cop(plr=plr, t_chw=t_chw, t_cw=t_cw)
        if cop <= 0:
            return float("inf")            # 不可运行
        return (load_rt * 3.517) / cop     # 1 RT = 3.517 kW
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/simulation/test_chiller.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/simulation/ tests/simulation/
git commit -m "feat: add centrifugal chiller physics model"
```

#### Task 2.2: 冷却塔、水泵与制冷站组装

**Files:**
- Create: `src/simulation/cooling_tower.py`
- Create: `src/simulation/pump.py`
- Create: `src/simulation/plant.py`
- Create: `tests/simulation/test_cooling_tower.py`
- Create: `tests/simulation/test_plant.py`

- [ ] **Step 1: 写冷却塔和制冷站测试**

```python
# tests/simulation/test_cooling_tower.py
import pytest
from src.simulation.cooling_tower import CoolingTower


class TestCoolingTower:
    @pytest.fixture
    def tower(self):
        return CoolingTower(
            name="tower_1",
            design_heat_rejection_kw=500 * 3.517 * 1.3,  # ~ 1.3x chiller capacity
            design_flow_lps=80,
            design_wb_temp=28.0,
            design_approach=4.0,         # 出水 = 湿球 + 4°C
        )

    def test_approach_increases_with_low_fan_speed(self, tower):
        """降低风扇转速 → 逼近度增大 → 出水温度升高"""
        t_out_full = tower.compute_outlet_temp(
            heat_load_kw=2000, water_flow_lps=80,
            fan_speed_hz=50, outdoor_wb=26.0,
        )
        t_out_low = tower.compute_outlet_temp(
            heat_load_kw=2000, water_flow_lps=80,
            fan_speed_hz=25, outdoor_wb=26.0,
        )
        assert t_out_low > t_out_full

    def test_outlet_temp_limited_by_wet_bulb(self, tower):
        """出水温度不能低于湿球温度"""
        t_out = tower.compute_outlet_temp(
            heat_load_kw=500, water_flow_lps=80,
            fan_speed_hz=50, outdoor_wb=26.0,
        )
        assert t_out >= 26.0

    def test_fan_power(self, tower):
        """风扇功率 ∝ (转速)^3"""
        p_50 = tower.compute_fan_power_kw(50)
        p_25 = tower.compute_fan_power_kw(25)
        assert abs(p_25 - p_50 * (25/50)**3) < 0.1
```

```python
# tests/simulation/test_plant.py
import pytest
from src.simulation.chiller import CentrifugalChiller
from src.simulation.cooling_tower import CoolingTower
from src.simulation.pump import Pump
from src.simulation.plant import ChillerPlant


class TestChillerPlant:
    @pytest.fixture
    def plant(self):
        chillers = [
            CentrifugalChiller(name=f"chiller_{i+1}", capacity_rt=500)
            for i in range(3)
        ]
        towers = [
            CoolingTower(
                name=f"tower_{i+1}",
                design_heat_rejection_kw=500 * 3.517 * 1.3,
            )
            for i in range(3)
        ]
        chw_pumps = [Pump(name=f"chw_pump_{i+1}", rated_power_kw=37) for i in range(3)]
        cw_pumps = [Pump(name=f"cw_pump_{i+1}", rated_power_kw=30) for i in range(3)]
        return ChillerPlant(
            chillers=chillers, cooling_towers=towers,
            chw_pumps=chw_pumps, cw_pumps=cw_pumps,
        )

    def test_single_chiller_operation(self, plant):
        """单台冷机运行 → 返回系统快照"""
        config = {
            "chiller_loads": {"chiller_1": 375},
            "chiller_t_chw": {"chiller_1": 7.0},
            "chiller_t_cw": {"chiller_1": 30.0},
            "tower_fan_speeds": {"tower_1": 50.0},
            "chw_pump_speeds": {"chw_pump_1": 45.0},
            "cw_pump_speeds": {"cw_pump_1": 40.0},
        }
        snap = plant.snapshot(config, outdoor_wb=26.0, outdoor_db=33.0)
        assert snap.total_cooling_load_rt == 375
        assert snap.system_cop > 0

    def test_two_chiller_operation(self, plant):
        """双机运行 — 验证 COP 计算"""
        config = {
            "chiller_loads": {"chiller_1": 300, "chiller_2": 300},
            "chiller_t_chw": {"chiller_1": 7.0, "chiller_2": 7.0},
            "chiller_t_cw": {"chiller_1": 30.0, "chiller_2": 30.0},
            "tower_fan_speeds": {"tower_1": 50.0, "tower_2": 50.0},
            "chw_pump_speeds": {"chw_pump_1": 45.0, "chw_pump_2": 45.0},
            "cw_pump_speeds": {"cw_pump_1": 40.0, "cw_pump_2": 40.0},
        }
        snap = plant.snapshot(config, outdoor_wb=26.0, outdoor_db=33.0)
        assert snap.total_cooling_load_rt == 600
        assert len(snap.running_chillers) == 2

    def test_below_surge_raises_error(self, plant):
        """负荷低于喘振边界 → 报错"""
        config = {
            "chiller_loads": {"chiller_1": 50},   # 10% of 500RT → below surge
            "chiller_t_chw": {"chiller_1": 7.0},
            "chiller_t_cw": {"chiller_1": 30.0},
            "tower_fan_speeds": {"tower_1": 50.0},
            "chw_pump_speeds": {"chw_pump_1": 45.0},
            "cw_pump_speeds": {"cw_pump_1": 40.0},
        }
        with pytest.raises(ValueError, match="surge"):
            plant.snapshot(config, outdoor_wb=26.0, outdoor_db=33.0)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/simulation/test_cooling_tower.py tests/simulation/test_plant.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现冷却塔、水泵和制冷站**

```python
# src/simulation/cooling_tower.py
class CoolingTower:
    """冷却塔模型 — Merkel 理论简化版"""

    def __init__(
        self, name: str, design_heat_rejection_kw: float,
        design_flow_lps: float = 80.0, design_wb_temp: float = 28.0,
        design_approach: float = 4.0, rated_fan_power_kw: float = 15.0,
        design_range: float = 5.0,
    ):
        self.name = name
        self.design_heat_rejection_kw = design_heat_rejection_kw
        self.design_flow_lps = design_flow_lps
        self.design_wb_temp = design_wb_temp
        self.design_approach = design_approach
        self.rated_fan_power_kw = rated_fan_power_kw
        self.design_range = design_range

    def compute_outlet_temp(
        self, heat_load_kw: float, water_flow_lps: float,
        fan_speed_hz: float, outdoor_wb: float,
    ) -> float:
        """计算冷却塔出水温度

        approach ∝ 1 / (fan_speed_ratio × water_flow_ratio)
        热负荷越高、风扇越慢、水量越小 → 逼近度越大
        """
        if fan_speed_hz <= 0 or water_flow_lps <= 0:
            return 50.0                      # 无效工况，返回高温
        load_ratio = heat_load_kw / self.design_heat_rejection_kw if self.design_heat_rejection_kw > 0 else 1.0
        fan_ratio = fan_speed_hz / 50.0
        flow_ratio = water_flow_lps / self.design_flow_lps
        approach = self.design_approach * load_ratio / (fan_ratio * flow_ratio)
        return max(outdoor_wb, outdoor_wb + approach)

    def compute_fan_power_kw(self, fan_speed_hz: float) -> float:
        if fan_speed_hz <= 0:
            return 0.0
        return self.rated_fan_power_kw * (fan_speed_hz / 50.0) ** 3
```

```python
# src/simulation/pump.py
class Pump:
    """水泵模型 — 相似定律"""

    def __init__(self, name: str, rated_power_kw: float = 37.0,
                 rated_flow_lps: float = 100.0, rated_head_m: float = 32.0):
        self.name = name
        self.rated_power_kw = rated_power_kw
        self.rated_flow_lps = rated_flow_lps
        self.rated_head_m = rated_head_m

    def compute_power_kw(self, speed_hz: float) -> float:
        if speed_hz <= 0:
            return 0.0
        return self.rated_power_kw * (speed_hz / 50.0) ** 3

    def compute_flow_lps(self, speed_hz: float) -> float:
        if speed_hz <= 0:
            return 0.0
        return self.rated_flow_lps * (speed_hz / 50.0)
```

```python
# src/simulation/plant.py
from typing import Dict, List
from src.schemas.equipment import (
    PlantSnapshot, ChillerState, CoolingTowerState,
    PumpState, EquipmentStatus,
)
from src.simulation.chiller import CentrifugalChiller
from src.simulation.cooling_tower import CoolingTower
from src.simulation.pump import Pump

KW_PER_RT = 3.517


class ChillerPlant:
    """制冷站仿真 — 组合所有设备模型"""

    def __init__(
        self, chillers: List[CentrifugalChiller],
        cooling_towers: List[CoolingTower],
        chw_pumps: List[Pump], cw_pumps: List[Pump],
    ):
        self.chillers = {c.name: c for c in chillers}
        self.cooling_towers = {t.name: t for t in cooling_towers}
        self.chw_pumps = {p.name: p for p in chw_pumps}
        self.cw_pumps = {p.name: p for p in cw_pumps}

    def snapshot(self, config: dict, outdoor_wb: float,
                 outdoor_db: float) -> PlantSnapshot:
        """根据运行配置生成系统快照

        config = {
            "chiller_loads": {name: load_rt},
            "chiller_t_chw": {name: temp},
            "chiller_t_cw": {name: temp},
            "tower_fan_speeds": {name: hz},
            "chw_pump_speeds": {name: hz},
            "cw_pump_speeds": {name: hz},
        }
        """
        loads = config.get("chiller_loads", {})
        t_chws = config.get("chiller_t_chw", {})
        t_cws = config.get("chiller_t_cw", {})
        tower_speeds = config.get("tower_fan_speeds", {})
        chw_speeds = config.get("chw_pump_speeds", {})
        cw_speeds = config.get("cw_pump_speeds", {})

        # 计算冷机状态
        chiller_states = {}
        total_heat_rejection_kw = 0.0
        for name, ch in self.chillers.items():
            load_rt = loads.get(name, 0.0)
            if load_rt <= 0:
                chiller_states[name] = ChillerState(
                    device_id=name, capacity_rt=ch.capacity_rt,
                    status=EquipmentStatus.OFF, current_load_rt=0.0,
                )
                continue
            t_chw = t_chws.get(name, 7.0)
            t_cw = t_cws.get(name, 30.0)
            plr = load_rt / ch.capacity_rt
            cop = ch.compute_cop(plr=plr, t_chw=t_chw, t_cw=t_cw)
            if cop <= 0:
                raise ValueError(
                    f"{name} at PLR={plr:.2f}, T_cw={t_cw}°C "
                    f"is in surge region"
                )
            power_kw = ch.compute_power_kw(load_rt, t_chw, t_cw)
            heat_rejection = (load_rt * KW_PER_RT) + power_kw
            total_heat_rejection_kw += heat_rejection
            chiller_states[name] = ChillerState(
                device_id=name, capacity_rt=ch.capacity_rt,
                status=EquipmentStatus.RUNNING, current_load_rt=load_rt,
                power_kw=power_kw, chw_supply_temp=t_chw,
            )

        # 计算冷却塔状态 (简化: 总散热量均分给运行中的塔)
        running_towers = [t for n, t in self.cooling_towers.items()
                          if tower_speeds.get(n, 0) > 0]
        n_towers = max(1, len(running_towers))
        tower_states = {}
        for name, tw in self.cooling_towers.items():
            speed = tower_speeds.get(name, 0.0)
            if speed <= 0:
                tower_states[name] = CoolingTowerState(
                    device_id=name, status=EquipmentStatus.OFF,
                )
                continue
            heat_per_tower = total_heat_rejection_kw / n_towers
            outlet_temp = tw.compute_outlet_temp(
                heat_per_tower, tw.design_flow_lps, speed, outdoor_wb,
            )
            tower_states[name] = CoolingTowerState(
                device_id=name, status=EquipmentStatus.RUNNING,
                fan_speed_hz=speed, water_out_temp=outlet_temp,
                water_flow_lps=tw.design_flow_lps,
            )

        # 计算水泵状态
        pump_states_factory = lambda speeds, pumps: {
            name: PumpState(
                device_id=name, status=EquipmentStatus.RUNNING if s > 0 else EquipmentStatus.OFF,
                speed_hz=s, rated_power_kw=p.rated_power_kw,
                rated_flow_lps=p.rated_flow_lps,
            )
            for name, p in pumps.items() if (s := speeds.get(name, 0.0)) >= 0
        }

        return PlantSnapshot(
            chillers=chiller_states,
            cooling_towers=tower_states,
            chw_pumps=pump_states_factory(chw_speeds, self.chw_pumps),
            cw_pumps=pump_states_factory(cw_speeds, self.cw_pumps),
            outdoor_wb_temp=outdoor_wb, outdoor_db_temp=outdoor_db,
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/simulation/test_cooling_tower.py tests/simulation/test_plant.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/simulation/cooling_tower.py src/simulation/pump.py src/simulation/plant.py tests/simulation/
git commit -m "feat: add cooling tower, pump models and chiller plant simulation"
```

---

### Phase 3: 性能曲线系统

#### Task 3.1: 代理模型拟合与在线辨识

**Files:**
- Create: `src/curves/__init__.py`
- Create: `src/curves/surrogate.py`
- Create: `src/curves/online_id.py`
- Create: `tests/curves/__init__.py`
- Create: `tests/curves/test_surrogate.py`

- [ ] **Step 1: 写代理模型拟合测试**

```python
# tests/curves/test_surrogate.py
import numpy as np
from src.curves.surrogate import ChillerSurrogate, fit_chiller_surrogate


class TestChillerSurrogate:
    @pytest.fixture
    def surrogate(self):
        """用已知系数的代理模型"""
        return ChillerSurrogate(
            coeffs=[3.0, 2.0, -1.0, 0.1, -0.05, -0.02, -0.01]
        )

    def test_predict_scalar(self, surrogate):
        cop = surrogate.predict(plr=0.75, t_chw=7.0, t_cw=30.0)
        assert cop > 0

    def test_predict_batch(self, surrogate):
        plrs = np.array([0.5, 0.75, 1.0])
        t_chws = np.array([7.0, 7.0, 7.0])
        t_cws = np.array([30.0, 30.0, 30.0])
        cops = surrogate.predict(plrs, t_chws, t_cws)
        assert cops.shape == (3,)
        assert all(c > 0 for c in cops)


class TestFitChillerSurrogate:
    def test_fit_from_data(self):
        """用合成数据拟合 → 预测误差应很小"""
        np.random.seed(42)
        n = 500
        plrs = np.random.uniform(0.3, 1.0, n)
        t_chws = np.random.uniform(5, 10, n)
        t_cws = np.random.uniform(26, 35, n)
        # 用已知函数生成 COP
        true_cops = (4.5 + 1.5 * plrs - 0.8 * plrs**2
                     + 0.12 * t_chws - 0.04 * t_cws
                     - 0.01 * t_cws**2 - 0.02 * plrs * t_cws)
        true_cops += np.random.normal(0, 0.05, n)  # 加噪声

        surrogate = fit_chiller_surrogate(plrs, t_chws, t_cws, true_cops)
        predicted = surrogate.predict(plrs, t_chws, t_cws)
        rmse = np.sqrt(np.mean((predicted - true_cops) ** 2))
        assert rmse < 0.2                       # RMSE < 0.2 COP 单位
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/curves/test_surrogate.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现代理模型**

```python
# src/curves/surrogate.py
import numpy as np
from numpy.linalg import lstsq


class ChillerSurrogate:
    """冷机 COP 多项式代理模型

    COP(P, T_e, T_c) = a₀ + a₁·P + a₂·P² + a₃·T_e + a₄·T_c + a₅·T_c² + a₆·P·T_c
    P = PLR (0~1), T_e = 冷冻水出口温度, T_c = 冷却水入口温度
    """

    def __init__(self, coeffs: list[float]):
        self.coeffs = np.array(coeffs, dtype=np.float64)
        if len(self.coeffs) != 7:
            raise ValueError(f"Expected 7 coefficients, got {len(self.coeffs)}")

    def predict(self, plr, t_chw, t_cw) -> np.ndarray:
        plr = np.atleast_1d(np.asarray(plr, dtype=np.float64))
        t_chw = np.atleast_1d(np.asarray(t_chw, dtype=np.float64))
        t_cw = np.atleast_1d(np.asarray(t_cw, dtype=np.float64))
        X = np.column_stack([
            np.ones_like(plr), plr, plr**2, t_chw, t_cw, t_cw**2, plr * t_cw,
        ])
        result = X @ self.coeffs
        return result if len(result) > 1 else result[0]

    def to_dict(self) -> dict:
        return {"coeffs": self.coeffs.tolist()}

    @classmethod
    def from_dict(cls, d: dict) -> "ChillerSurrogate":
        return cls(coeffs=d["coeffs"])


def fit_chiller_surrogate(
    plrs: np.ndarray, t_chws: np.ndarray, t_cws: np.ndarray, cops: np.ndarray,
) -> ChillerSurrogate:
    """最小二乘拟合冷机代理模型"""
    X = np.column_stack([
        np.ones_like(plrs), plrs, plrs**2, t_chws, t_cws, t_cws**2, plrs * t_cws,
    ])
    coeffs, _, _, _ = lstsq(X, cops)
    return ChillerSurrogate(coeffs=coeffs.tolist())


class TowerSurrogate:
    """冷却塔代理模型 — 简单的线性+交互项"""

    def __init__(self, coeffs: list[float]):
        self.coeffs = np.array(coeffs, dtype=np.float64)

    def predict_approach(self, load_ratio, fan_ratio, wb_temp) -> np.ndarray:
        """预测逼近度"""
        load_ratio = np.atleast_1d(np.asarray(load_ratio))
        fan_ratio = np.atleast_1d(np.asarray(fan_ratio))
        wb_temp = np.atleast_1d(np.asarray(wb_temp))
        X = np.column_stack([
            np.ones_like(load_ratio), load_ratio, 1.0 / np.maximum(fan_ratio, 0.01), wb_temp,
        ])
        return X @ self.coeffs
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/curves/test_surrogate.py -v
```
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/curves/ tests/curves/
git commit -m "feat: add chiller surrogate model fitting"
```

---

由于这是一个大型实现计划，我将关键 Phase 的核心任务已详细展开（Phase 0-3），剩余 Phase 以概要任务形式列出，每个任务同样遵循 TDD 流程。完整实现时通过 subagent-driven-development 逐任务执行。

#### Task 3.2: 在线参数辨识 (RLS)

**Files:** Create `src/curves/online_id.py`, `tests/curves/test_online_id.py`

- [ ] **Step 1: 写 RLS 测试** — 注入已知系数漂移的合成数据，验证 RLS 能追踪系数变化
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现 `RecursiveLeastSquares` 类** — 带遗忘因子的递推最小二乘
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 4: 联合优化引擎

#### Task 4.1: 约束条件模块

**Files:** Create `src/optimization/__init__.py`, `src/optimization/constraints.py`, `tests/optimization/test_constraints.py`

- [ ] **Step 1: 写约束测试** — 喘振约束: PLR 不可低于边界、最小运行时间: 启停间隔检查、电机启动间隔: 30s 限制、容量平衡: 总容量 ≥ 负荷
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现约束函数** — `surge_constraint()`, `min_runtime_constraint()`, `motor_start_interval()`, `capacity_balance()`, 统一接口 `check_all_constraints()`
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 4.2: 目标函数

**Files:** Create `src/optimization/objective.py`, `tests/optimization/test_objective.py`

- [ ] **Step 1: 写目标函数测试** — total_cost = 电费 + 碳成本 + 磨损成本, 验证各项计算正确, 验证权重可配置
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `compute_energy_cost()`, `compute_carbon_cost()`, `compute_wear_cost()`, `total_objective()`
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 4.3: MINLP 求解器

**Files:** Create `src/optimization/solver.py`, `src/optimization/pareto.py`, `tests/optimization/test_solver.py`

- [ ] **Step 1: 写求解器测试** — 简单 2 冷机 + 1 负荷点的枚举、验证返回可行解、验证喘振约束被遵守、验证帕累托前沿至少有 2 个解
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `enumerate_feasible_combinations()`, `optimize_continuous_params()` (用 scipy.optimize.minimize), `ChillerPlantOptimizer` 主类, `compute_pareto_front()`
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 5: Agent 框架

#### Task 5.1: LLM 客户端工厂

**Files:** Create `src/agents/__init__.py`, `src/agents/base.py`, `tests/agents/__init__.py`, `tests/agents/test_base.py`

借鉴 TradingAgents 的 `create_llm_client` 设计，支持 Anthropic/OpenAI/Google 三 Provider，Deep/Quick 双模型等级。

- [ ] **Step 1: 写测试** — mock LLM, 验证 Deep/Quick 分派、验证 provider 选择逻辑
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `create_llm_client(provider, model, **kwargs)`, `BaseAgent` 抽象类, `AgentContext` (携带 config, state, tools)
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 5.2: AgentState 与共享状态

**Files:** Create `src/schemas/state.py`, `tests/schemas/test_state.py`

- [ ] **Step 1: 写测试** — AgentState 包含所有 schema 字段, InvestDebateState 初始化, RiskDebateState 轮转逻辑
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `AgentState(MessagesState)`, `InvestDebateState(TypedDict)`, `RiskDebateState(TypedDict)` (借鉴 TradingAgents)
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 6: 核心 Agent（感知层）

#### Task 6.1: 监测 Agent

**Files:** Create `src/agents/monitor.py`, `tests/agents/test_monitor.py`

- [ ] **Step 1: 写测试** — 正常快照→无告警, 异常快照→检测到告警, 设备退化趋势→健康评分下降, 结构化输出验证
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `create_monitor_agent(llm)`, Prompt 模板（系统角色: 制冷站设备监测专家）, 工具: `get_snapshot()`, `query_history()`，输出 `MonitorReport` Schema
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 6.2: 预测 Agent

**Files:** Create `src/agents/predict.py`, `tests/agents/test_predict.py`

- [ ] **Step 1: 写测试** — 输入天气+历史→输出预测值+置信区间, 多时间尺度: 15min/1h/6h/24h
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `create_predict_agent(llm)`, 工具: `get_weather_forecast()`, `get_historical_load()`, ML 模型推理接口, 输出 `LoadForecast` Schema（包含多时间尺度和置信区间）
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 6.3: 策略 Agent

**Files:** Create `src/agents/strategy.py`, `tests/agents/test_strategy.py`

- [ ] **Step 1: 写测试** — 输入预测+快照→输出包含过渡计划的策略, 验证策略包含必需字段, 验证调用优化引擎
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `create_strategy_agent(deep_llm, optimizer)`, 调用联合优化引擎获取帕累托解, LLM 从 Top-3 中选择, 生成包含过渡计划和启动序列的完整策略
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 7: Advocate Agent（辩论层）

#### Task 7.1: 可靠性 Advocate

**Files:** Create `src/agents/advocates/__init__.py`, `src/agents/advocates/reliability.py`, `tests/agents/advocates/__init__.py`, `tests/agents/advocates/test_reliability.py`

- [ ] **Step 1: 写测试** — 安全策略→通过, 高风险策略→驳回, 引用 RAG 标准
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 审查维度: 安全余量、设备健康、喘振风险、启停频率, 融合暖通+机电知识(RAG)
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 7.2: 效率 Advocate

**Files:** Create `src/agents/advocates/efficiency.py`, `tests/agents/advocates/test_efficiency.py`

- [ ] **Step 1: 写测试** — 高 COP 策略→通过, 低效策略→驳回
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 审查维度: COP 优化、电价响应、需量管理
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 7.3: 合规 Advocate

**Files:** Create `src/agents/advocates/compliance.py`, `tests/agents/advocates/test_compliance.py`

- [ ] **Step 1: 写测试** — 碳排放不超标→通过, 超配额→驳回
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 审查维度: 碳排放核算、碳配额管理、标准合规性
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 8: 治理 Agent（决策层）

#### Task 8.1: 协调 Agent

**Files:** Create `src/agents/coordinator.py`, `tests/agents/test_coordinator.py`

- [ ] **Step 1: 写测试** — 全票通过→直接通过, 存在冲突→触发辩论, 辩论 max 2 轮停止
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 加权仲裁逻辑, 辩论编排, 冲突检测与定向辩论触发
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 8.2: 安全 Agent（规则引擎，非 LLM）

**Files:** Create `src/agents/safety.py`, `tests/agents/test_safety.py`

- [ ] **Step 1: 写测试** — 违反喘振约束→拦截, 违反最小运行时间→拦截, 正常策略→通过, 电机启动间隔违反→拦截
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 纯 Python 规则引擎, 检查列表: 喘振边界、最小运行/停机时间、流量约束、温度约束、电机启动间隔、设备可用性, `SafetyCheckResult`
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 8.3: 参数 Agent

**Files:** Create `src/agents/parameter.py`, `tests/agents/test_parameter.py`

- [ ] **Step 1: 写测试** — 偏差 < 5%→微调, 偏差 > 5%→触发新策略, 死区不动作
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 死区控制器(±0.3°C), 速率限制器(0.1°C/min), 振荡检测, 超限触发新策略
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 9: LangGraph 工作流编排

#### Task 9.1: 条件路由与图构建

**Files:** Create `src/graph/__init__.py`, `src/graph/setup.py`, `src/graph/conditional_logic.py`, `src/graph/debate.py`, `tests/graph/__init__.py`, `tests/graph/test_setup.py`

借鉴 TradingAgents 的 `GraphSetup` 和 `ConditionalLogic`。

- [ ] **Step 1: 写测试** — 图可以编译, 7 阶段完整流程可走通, 故障触发加速通道, 辩论轮次限制生效
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `GraphSetup.setup_graph()`, `ConditionalLogic` (各阶段路由), 3 种辩论模式的实现
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 9.2: Memory Log 与反思

**Files:** Create `src/memory/__init__.py`, `src/memory/log.py`, `src/memory/reflection.py`, `tests/memory/test_log.py`

- [ ] **Step 1: 写测试** — 存储策略→可检索, 延迟反思生成, past_context 注入
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `TradingMemoryLog` 等效类, `Reflector` (借鉴 TradingAgents), 策略执行后两路反馈
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 10: RL 审核引擎

#### Task 10.1: Contextual Bandit 模型

**Files:** Create `src/rl/__init__.py`, `src/rl/features.py`, `src/rl/bandit.py`, `src/rl/trainer.py`, `tests/rl/test_bandit.py`

- [ ] **Step 1: 写测试** — 特征提取: 状态→特征向量, 模型预测: 给定特征→选择动作, 线下训练: 历史数据→更新参数, 置信度计算
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `FeatureExtractor`（冷负荷、温湿度、电价、设备状态）, `ContextualBandit`（ε-greedy + 置信度）, `RLTrainer`（从 Memory Log 离线训练）
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 10.2: RL 安全护栏

**Files:** Create `src/rl/safety_gates.py`, `tests/rl/test_safety_gates.py`

- [ ] **Step 1: 写测试** — 极端工况→强制人工, RL 高置信但违反硬约束→拦截, 正常工况→允许 RL 决策
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 极端工况检测, 硬约束前置检查, 紧急停止机制
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 11: 报告子系统

#### Task 11.1: KPI 计算器

**Files:** Create `src/reports/__init__.py`, `src/reports/kpi_calculator.py`, `tests/reports/__init__.py`, `tests/reports/test_kpi_calculator.py`

- [ ] **Step 1: 写测试** — COP 计算: 已知输入→预期输出, EER 计算, 碳排放强度, 对标评估
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 纯 Python 函数（全部单元测试覆盖）, `compute_cop()`, `compute_eer()`, `compute_carbon_intensity()`, `benchmark_against_standard()`
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 11.2: 报告生成管线与渲染

**Files:** Create `src/reports/generator.py`, `src/reports/renderer.py`, `tests/reports/test_generator.py`

- [ ] **Step 1: 写测试** — 日报生成: 数据→Markdown, KPI 数值正确嵌入, 标准条款引用
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — 5 阶段管线（聚合→KPI→LLM分析→模板→渲染）, Jinja2 模板, JSON/PDF/Excel 输出
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 11.3: 报告 Agent

**Files:** Create `src/agents/report.py`, `tests/agents/test_report.py`

- [ ] **Step 1: 写测试** — 输入策略+快照→输出日报, 月报触发, 不参与决策闭环验证
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `create_report_agent(llm)`, 只读消费所有 Agent 输出, 定时 + 按需触发
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 12: RAG 标准查询

#### Task 12.1: 文档加载与向量检索

**Files:** Create `src/rag/__init__.py`, `src/rag/loader.py`, `src/rag/retriever.py`, `tests/rag/test_retriever.py`

- [ ] **Step 1: 写测试** — PDF 分段正确, embedding 生成, 查询返回相关段落
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — PDF 解析+分段, embedding (OpenAI/sentence-transformers), pgvector 存储与查询
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 13: 实时控制层

#### Task 13.1: PID 控制器、死区与联锁

**Files:** Create `src/control/__init__.py`, `src/control/pid.py`, `src/control/deadband.py`, `src/control/interlock.py`, `tests/control/test_pid.py`, `tests/control/test_deadband.py`, `tests/control/test_interlock.py`

- [ ] **Step 1: 写测试** — PID 阶跃响应, 死区不动作, 速率限制生效, 冷机启动序列 7 步骤, 电气联锁 30s 间隔
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `PIDController`（含 anti-windup）, `DeadbandLimiter`, `RateLimiter`, `ChillerStartupSequence`, `ChillerShutdownSequence`
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 14: 消息总线

#### Task 14.1: Redis 事件总线

**Files:** Create `src/messaging/__init__.py`, `src/messaging/bus.py`, `tests/messaging/test_bus.py`

- [ ] **Step 1: 写测试** — 发布/订阅, 事件序列化, 超时降级
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — `EventBus` (Redis Pub/Sub 封装), `Event` 数据类, `publish()`, `subscribe()`
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

### Phase 15: API 与前端

#### Task 15.1: FastAPI 后端

**Files:** Create `src/api/__init__.py`, `src/api/main.py`, `src/api/monitoring.py`, `src/api/strategy.py`, `src/api/reports.py`, `tests/api/test_api.py`

- [ ] **Step 1: 写测试** — GET /api/snapshot → 200, POST /api/strategies → 创建策略, GET /api/reports/daily → 报表
- [ ] **Step 2: 确认失败**
- [ ] **Step 3: 实现** — FastAPI 应用, REST + WebSocket 端点, 挂载全系统服务
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

#### Task 15.2: 2D 前端可视化

**Files:** Create `frontend/` (React + ECharts 项目)

- [ ] **Step 1: 创建 React 项目, 实现 P&ID 风格原理图组件**
- [ ] **Step 2: 实现实时 Dashboard（KPI 卡片 + 趋势图）**
- [ ] **Step 3: 实现策略时间线视图**
- [ ] **Step 4: 实现报告预览页面**
- [ ] **Step 5: WebSocket 实时数据连接**
- [ ] **Step 6: 提交**

---

### Phase 16: 集成测试

#### Task 16.1: 端到端工作流测试

**Files:** Create `tests/integration/__init__.py`, `tests/integration/test_full_workflow.py`

- [ ] **Step 1: 写集成测试** — 完整 7 阶段流程: 仿真数据→监测+预测→策略生成→辩论→仲裁→安全校验→RL 审核→执行→反思
- [ ] **Step 2: 确认失败** (组件未完全集成)
- [ ] **Step 3: 逐步联调，修复集成问题**
- [ ] **Step 4: 确认通过**
- [ ] **Step 5: 提交**

---

## 实现顺序依赖

```
Phase 0: 基础设施 ─────────────────────────────────────────────┐
Phase 1: Schemas ──────────────────────────────────────────────┤
Phase 2: 仿真层 ─────┐                                         │
Phase 3: 性能曲线 ───┤ (依赖 Phase 2)                           │
Phase 4: 优化引擎 ───┤ (依赖 Phase 2, 3)                        │
Phase 5: Agent 框架 ─┤ (独立)                                   │
                     ├── 骨架完成 ── 之后是功能 Agent ──────────┤
Phase 6: 核心 Agent ─┤ (依赖 Phase 1, 2, 4, 5)                  │
Phase 7: Advocate ───┤ (依赖 Phase 6)                           │
Phase 8: 治理 Agent ─┤ (依赖 Phase 6, 7)                        │
Phase 9: 工作流 ─────┤ (依赖 Phase 5-8)                         │
Phase 10: RL 引擎 ───┤ (依赖 Phase 9)                           │
Phase 11: 报告 ──────┤ (依赖 Phase 6-8)                         │
Phase 12: RAG ───────┤ (独立)                                   │
Phase 13: 控制层 ────┤ (独立)                                   │
Phase 14: 消息总线 ──┤ (独立)                                   │
Phase 15: API/前端 ──┤ (依赖 Phase 6-14)                        │
Phase 16: 集成测试 ──┘ (依赖全部)                               │
```

---

## 自审清单

1. **Spec 覆盖**: 设计文档 14 个章节全部有对应的实现任务 ；仿真层(§12) 、策略与优化(§5) 、RL 审核(§8) 、报告(§9) 、RAG(§10) 、控制层(§3/§7) 、可视化(§13) 

2. **无占位符**: 所有任务包含具体代码或具体实现描述

3. **类型一致性**: Schemas 在 Phase 1 定义，后续 Agent 全部使用 `src/schemas/strategy.Strategy`、`src/schemas/review.AdvocateOpinion` 等统一类型
