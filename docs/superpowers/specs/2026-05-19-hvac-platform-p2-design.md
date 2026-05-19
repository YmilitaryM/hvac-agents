# HVAC 制冷站平台 P2 设计规格

> 日期: 2026-05-19 | 状态: 设计完成 | 版本: 1.0

## 1. 概述

### 1.1 P0/P1 回顾

| 阶段 | 交付 |
|------|------|
| P0 | 微服务骨架 (5服务) + 设备CRUD + 制冷站拓扑 + 仿真引擎 + 智能体管线 + API Gateway + React SPA |
| P1 | 冷负荷预测 + DRL优化 + 故障注入 + 告警引擎 + What-if + 版本化 + 能效对标 + 审计日志 |

### 1.2 P2 目标

将系统从"仿真演示平台"升级为**可对接真实硬件、自校准、站间协同、可生产部署**的数字孪生平台。

### 1.3 四大模块

| # | 模块 | 优先级 | 核心交付 |
|---|------|--------|---------|
| A | 硬件采集 | 1 | Data Acquisition Service + 三协议适配器 + 时序存储 + Live/Shadow/Hybrid 模式 + 双向读写 + 边缘部署 |
| C | 模型校准 + 数据质量 | 2 | 设备性能曲线在线校准 + 5层数据质量监控 + 归因引擎 + ML异常检测 + 退化趋势追踪 |
| D | 协同优化 + 碳交易 | 3 | 站内 MILP+MAPPO 双层优化 + 站间协同调度 + 通用碳市场框架 + CEA 适配 |
| B | 生产化加固 | 4 | 测试全覆盖 + CI/CD + Alembic + 限流熔断 + Prometheus + PWA + 报告导出 + 告警送达 + HITL |

---

## 2. 模块 A: 硬件采集服务 (Data Acquisition Service)

### 2.1 服务定位

新建微服务 `services/acquisition/`，端口 8005，自带 TimescaleDB (`acq_db`)。

职责：从现场硬件读取点位数据写入时序库，转发最新值到 Asset Service，接收控制指令写回硬件。

### 2.2 架构

```
services/acquisition/
├── pyproject.toml
├── Dockerfile
├── acquisition_service/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── models.py                  # TimescaleDB supertable 模型
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                # ProtocolAdapter 抽象基类
│   │   ├── modbus_adapter.py      # pymodbus (RTU/TCP)
│   │   ├── bacnet_adapter.py      # BAC0
│   │   └── opcua_adapter.py       # opcua-asyncio
│   ├── poller.py                  # 可配置轮询引擎 (1s~3600s)
│   ├── cache.py                   # Redis 最新值缓存
│   ├── forwarder.py              # 数据转发到 Asset Service
│   ├── gap_filler.py             # 数据填补 (线性插值/回归/仿真回退)
│   ├── edge_sync.py              # 边缘-云端断点续传
│   └── api/
│       ├── __init__.py
│       ├── points.py              # 点位配置管理
│       ├── status.py              # 采集状态监控
│       └── commands.py            # 控制指令下发 (写操作)
└── tests/
```

### 2.3 协议适配器接口

```python
class ProtocolAdapter(ABC):
    protocol: str  # "bacnet" | "modbus" | "opc_ua"

    async def connect(self, binding: ProtocolBinding) -> None: ...
    async def read_point(self, point_id: str, binding: ProtocolBinding) -> float: ...
    async def write_point(self, point_id: str, binding: ProtocolBinding, value: float) -> None: ...
    async def disconnect(self) -> None: ...
```

**三协议实现：**

| 协议 | Python 库 | 通信方式 | 典型 binding |
|------|----------|---------|-------------|
| Modbus | pymodbus | RTU/TCP | slave_id + register + function_code |
| BACnet | BAC0 | UDP/IP | device_id + object_type + instance |
| OPC UA | opcua-asyncio | TCP | node_id + 订阅模式 |

### 2.4 EquipmentPoint.protocol_binding 扩展

```json
// Modbus
{ "protocol": "modbus", "slave_id": 3,
  "register": 40001, "function_code": 3,
  "scale": 0.1, "offset": 0, "data_type": "int16" }

// BACnet
{ "protocol": "bacnet", "device_id": 2401,
  "object_type": "analog_input", "instance": 12,
  "poll_interval_sec": 5 }

// OPC UA
{ "protocol": "opc_ua", "node_id": "ns=2;s=Temperature",
  "endpoint_url": "opc.tcp://192.168.1.100:4840",
  "poll_interval_sec": 1 }
```

### 2.5 轮询引擎

- 每点位独立 `poll_interval_sec`（1s ~ 3600s）
- 秒级点位走 WebSocket 推送，分钟级走批量轮询
- 采集失败自动重试 3 次，超时发布 `point.communication_lost` 事件
- OPC UA 优先使用订阅模式减少轮询开销

### 2.6 数据落地 (acq_db TimescaleDB)

```python
class EquipmentReading(TimescaleModel):
    __tablename__ = "equipment_readings"
    time: datetime = TimescaleTimestampColumn()
    equipment_id: str
    point_id: str
    point_code: str
    value: float
    quality: str  # "good" | "estimated" | "questionable" | "bad"
    source: str   # "live" | "simulated" | "shadow"
```

保留策略：原始数据 90 天，降采样后长期保留（1min → 1h → 1d → 1mon 四级）。

### 2.7 控制指令下发（写通路）

```
Agent (DRL/MILP) → Safety Gate → Parameter Agent → 
  POST /api/acquisition/commands/write  →  ProtocolAdapter.write_point()
```

写操作安全校验：
- 值范围检查（基于点位模板的合法范围）
- 写频率限制（同一设备最小间隔 1s）
- 紧急停机超控（绕过所有限制）
- 写审计日志 (who, when, what, old_value, new_value)

### 2.8 数据填补 (Gap Filler)

```python
class GapFiller:
    def fill(self, point, gap_start, gap_end) -> list[Reading]:
        # 短间隙 (<5min): 线性插值
        # 中间隙 (5min-1h): 同类设备回归填充
        # 长间隙 (>1h): 切换回仿真值 + 标记 quality="estimated"
```

### 2.9 渐进式投运模式

```
SIMULATED → SHADOW → HYBRID → LIVE
              │         │        │
           DRL推理    部分点位   全部点位
           不执行      真实值     真实值
           仅对比      其余仿真   全自动
           记录偏差
```

Shadow Mode: AI 照常推理但不执行，记录推理值 vs 实际/仿真值的偏差。偏差收敛到阈值内才允许推进。

### 2.10 边缘部署

```
边缘工控机:
  acquisition_service (轻量化)
  + acq_db (本地短存)
  + Redis (本地缓存)

云端:
  主 acq_db (长期)
  + 其余 5 服务

边缘 ↔ 云端: 断点续传 + 配置下发同步
```

---

## 3. 模块 C: 模型自动校准 + 数据质量监控

### 3.1 校准对象

| 设备 | 校准曲线 | 校准参数 |
|------|---------|---------|
| 冷水主机 | COP-KW 曲线 (PLR → kW) | 多项式系数 a0, a1, a2, a3 |
| 冷水主机 | 喘振线 (冷凝温度 → 极限 PLR) | 极限 PLR 阈值 |
| 冷却塔 | 逼近度曲线 (湿球+负载 → 出水温) | 传热系数 |
| 水泵 | Q-H 曲线 (频率 → 扬程/功率) | 曲线系数 |
| 阀门 | Cv 特性曲线 (开度 → Cv) | 拟合参数 |

管道不需要校准。

### 3.2 校准流程

```
运行数据积累 → 数据清洗 → 参数辨识 → 精度验证 → 发布/回滚
```

1. **数据积累**: 从 `acq_db` 拉取指定时间段（默认 7 天）运行数据
2. **数据清洗**: 剔除启停期、通讯故障点、传感器漂移异常点
3. **参数辨识**: 最小二乘法/非线性回归，对原物理模型参数做偏移修正
4. **精度验证**: 保留 20% 数据验证，计算 MAPE/RMSE
5. **发布**: 写入 `CalibrationRun` → 更新 Sim Service 物理模型参数 → 写 EntityVersion

### 3.3 实现位置

```
services/simulation/sim_service/
├── calibration/
│   ├── __init__.py
│   ├── base.py               # 抽象校准器
│   ├── chiller_cal.py        # 冷机 COP-KW 曲线校准
│   ├── tower_cal.py          # 冷却塔传热系数校准
│   ├── pump_cal.py           # 水泵 Q-H 曲线校准
│   ├── valve_cal.py          # 阀门 Cv 曲线校准
│   ├── cleaner.py            # 数据清洗
│   └── validator.py          # 精度验证 MAPE/RMSE
├── api/
│   └── calibration.py        # 校准触发/历史/对比 API
├── models.py                 # + CalibrationRun, CalibrationDataPoint
```

### 3.4 触发方式

- **手动**: API `POST /api/calibration/run`
- **定时**: 每 24h 检查新数据 >= 1000 条且精度 < 阈值则自动校准
- **事件**: 采集服务检测到持续偏差时发布 `calibration_needed` 事件

### 3.5 数据质量监控 —— 五层检测

```
第1层: 实时规则 (毫秒级)
  ├── 通讯超时 → point.communication_lost
  ├── 数据越界 (<物理最小值 or >物理最大值)
  └── 启停期标记 (过滤不告警)

第2层: 统计检测 (分钟级)
  ├── 传感器冻结 (滑动窗方差=0 持续 >5min)
  └── 传感器突变 (前后帧差超过 3σ)

第3层: 上下文窗口检测 (小时/天/周级)
  ├── baseline_comparator    # 同期基线偏离 (历史4周同时段对比)
  ├── drift_tracker          # CUSUM + EWMA 退化趋势
  ├── peer_comparator        # 同类型设备交叉对比
  └── operational_checker    # 工况合理性 (时间/季节/电价 vs 运行模式)

第4层: ML 无监督异常检测 (分钟级推理)
  ├── Autoencoder            # 重构误差 → 传感器关联异常
  └── Isolation Forest        # 离群检测 → 效率指标异常

第5层: 归因引擎
  ├── cross_validation       # 关联传感器交叉验证
  ├── spatial_cluster        # 同设备/同PLC模块异常聚集
  ├── temporal_correlate      # 异常时间与外部事件关联
  ├── physics_plausible       # 物理守恒检验
  └── history_match           # 历史故障模式库匹配
```

### 3.6 异常分类与时效

| 异常类型 | 检测方式 | 时效 | 严重度 |
|---------|---------|------|--------|
| 通讯中断 | 采集超时 | 实时 (<5s) | Critical |
| 传感器冻结 | 方差检测 | 近实时 (~5min) | High |
| 传感器漂移 | CUSUM 退化追踪 | 天级 | Warning |
| 数据越界 | 固定阈值 | 实时 | Critical |
| 设备退化 | EWMA 趋势 | 周/月级 | Warning |
| 工况错误 | 操作规则引擎 | 小时级 | Medium |
| 未知异常模式 | ML Autoencoder/IF | 分钟级 | High |

### 3.7 归因分类

| 根因 | 判断逻辑 | 建议动作 |
|------|---------|---------|
| SENSOR_FAULT | 单点异常、同设备其他正常、通讯OK | 更换传感器 |
| COMM_FAILURE | 同网关多点同时中断、ping超时 | 检查网络 |
| DRIFT | 长期缓慢偏移、残差单调递增 | 重新标定 |
| REAL_ANOMALY | 多传感器一致异常、物理守恒成立 | 设备检修 |
| PLC_FAULT | 同IO模块全部异常、数值固定(锁存) | 检查PLC |
| ENV_INTERFERENCE | 多点短时跳变、与天气/电网吻合 | 加屏蔽/滤波 |

### 3.8 ML 冷启动

- 无历史数据时用 Simulation Engine 生成正常工况数据预训练 Autoencoder
- 数据积累后每周用最新正常数据微调
- 切换 LIVE 模式时模型已预热，上线即有检测能力

---

## 4. 模块 D: 协同优化 + 碳交易

### 4.1 优化分层架构

```
┌──────────────────────────────────────────────┐
│         站间协同调度层 (新增)                    │
│   多站负荷分配 · 供冷互补 · 碳配额统筹           │
└──────┬───────────────┬───────────────┬────────┘
       │               │               │
┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│ 站A 站内优化 │ │ 站B 站内优化 │ │ 站C 站内优化 │
│ MILP+MAPPO  │ │ MILP+MAPPO  │ │ MILP+MAPPO  │
└─────────────┘ └─────────────┘ └─────────────┘
```

### 4.2 站内优化: MILP + MAPPO 双层

**Layer 1: MILP 离散调度 (每 15min)**

```python
minimize:
    Σ(electric_cost + carbon_cost + wear_cost + water_cost)
    over horizon H (24h × 15min = 96 步)
subject to:
    负荷平衡   ΣQi = load_t
    设备约束   0 ≤ Qi ≤ Qmax_i
    碳排放上限  Σ(emission_factor × Pi) ≤ cap_t
    最低负荷   ΣQi ≥ contract_min
    启停线性化  binary variables for chiller on/off
```

输出：开机组合 + 各机目标负荷 → 传递为 DRL action mask

**Layer 2: MAPPO 连续参数优化 (每 1-5min)**

每台设备一个 RL Agent，共享 Critic 评估全局效率：

```python
agents = {
    "chiller_1": PPOAgent(obs_space, act_space),  # 冷冻水温设定
    "chiller_2": PPOAgent(obs_space, act_space),
    "pump_1":    PPOAgent(obs_space, act_space),   # 频率/扬程
}
```

观测空间包含预测负荷、碳价、电价、同类设备状态。

奖励函数：
```python
reward = (
    0.35 * cop_reward
    - 0.20 * carbon_penalty
    - 0.15 * electric_penalty
    + 0.20 * load_match_reward     # 负荷匹配 (vs pred_load)
    + 0.05 * anticipatory_bonus    # 超前调节奖励
    - 0.05 * comfort_penalty
)
```

**两层联动：**
- MILP 输出 → DRL action mask (OFF 设备不出动作)
- DRL 发现新 COP 数据 → 反馈 MILP 下次优化用更新后的效率曲线

### 4.3 站间协同调度

```
agent_service/optimization/
├── station_dispatch.py    # 站间负荷分配
├── carbon_allocator.py    # 碳配额分配
└── network_flow.py        # 管网流模型 (输配距离/热损失)
```

```python
def inter_station_dispatch(
    stations: list[Plant], total_load: float,
    carbon_budget: float, prices: dict
) -> DispatchResult:
    # 1. 按边际成本排序 (电费+碳+损耗)
    # 2. 优先分配高效站、高碳配额站
    # 3. 考虑管网输配距离和热损失
    # 4. 输出: 各站目标负荷、碳配额、边际成本
```

协同场景：负荷平移 / 碳配额内部交换 / 蓄冷协同 / 故障转移

### 4.4 碳交易模块

```
agent_service/carbon/
├── __init__.py
├── emission_calculator.py   # 排放计算 (电网排放因子 × 用电量)
├── carbon_market.py         # 通用碳市场抽象模型
├── cea_adapter.py           # 中国全国碳市场 CEA 适配
├── allowance_tracker.py     # 配额跟踪 (履约周期)
└── carbon_optimizer.py      # 碳成本最优调度
```

### 4.5 DRL 训练增强

| 能力 | P1 | P2 |
|------|----|----|
| Agent 数量 | 单 PPO | 多设备 MAPPO |
| 训练数据 | 仿真 | 仿真预热 + LIVE 在线微调 |
| 探索策略 | ε-greedy | ε-greedy + Safety Layer 约束探索 |
| 模型更新 | 手动 | 定时自动训练 + 在线微调 |
| 基准对比 | 无 | vs MILP-only vs PID vs 人工 |

新增文件：
```
agent_service/rl/
├── multi_agent/
│   ├── __init__.py
│   ├── mappo.py            # MAPPO 实现
│   ├── action_mask.py      # MILP约束 → DRL action mask
│   └── reward_shaper.py    # 多目标奖励整形
├── training/
│   ├── auto_trainer.py     # 定时自动训练调度
│   └── online_finetune.py  # 在线微调
└── benchmark/
    ├── __init__.py
    └── comparator.py       # DRL vs MILP vs PID 对比
```

### 4.6 预测→DRL→执行闭环

```
Prediction Module (P1)        DRL Agent (P2)              Execution
─────────────────────       ──────────────────       ─────────────────
physics_model.predict() ──→  obs["pred_load_*"] ──→  action: 水温设定
ml_model.predict()      ──→  obs["electric_price"] ─→  action: 频率/开度
blender.blend()         ──→                          → Safety Gate → 执行
        ↑                                                    │
        └──── 实际负荷反馈 (从 acq_db 或 sim) ────────────────┘
```

---

## 5. 模块 B: 生产化加固

### 5.1 测试全覆盖

| 层 | 服务 | 内容 |
|----|------|------|
| 单元测试 | 全部 6 服务 | 每个模块独立测试，mock 外部依赖 |
| 集成测试 | Asset + 采集 | 采集写入 → acq_db → 点位更新 |
| 集成测试 | Sim + Agent | 仿真 → 质量监控 → 告警 |
| 集成测试 | Agent DRL | MILP → MAPPO → Safety Gate → 写指令 |
| E2E | 全局 | 采集 → 存储 → 质量 → 校准 → 优化 → 控制 |
| 性能测试 | 采集 + Sim | 1000+ 点位并发轮询、大拓扑仿真 |

### 5.2 CI/CD

```
.github/workflows/
├── ci.yml              # PR: lint + type check + unit test + coverage
├── integration.yml     # Merge master: docker compose up + 集成测试
├── deploy.yml          # Tag: 构建镜像 → push registry
└── nightly.yml         # 每夜: 全量测试 + 性能基准对比
```

### 5.3 基础设施

- **Alembic**: 6 服务各一套迁移目录，Docker Compose 启动自动 migrate
- **限流熔断**: Gateway per-user rate limit (100 req/s) + 连续失败 5 次熔断 30s
- **Prometheus**: 每服务 `/metrics`，请求量/延迟/错误率/点位计数/轮询延迟
- **WebSocket**: Gateway → 前端推送实时 KPI + 告警 + 点位变化

### 5.4 移动端 (PWA)

- vite-plugin-pwa 生成 Service Worker
- 离线缓存 Dashboard + 告警列表
- 响应式布局 (Tailwind breakpoint 扩展)
- Web Push 告警通知

### 5.5 报告导出

- PDF: WeasyPrint / ReportLab
- Excel: openpyxl 多 sheet（KPI 汇总 + 设备明细 + 趋势图）
- 定时自动生成（日/周/月报）→ 邮件/企微分发

### 5.6 告警送达通道

| 通道 | 场景 | 实现 |
|------|------|------|
| WebSocket | 前端实时弹窗 | 增强现有 WebSocket |
| 企业微信/钉钉/飞书 | 日常告警推送 | Webhook 集成 |
| 短信/电话 | 严重告警 + 未确认升级 | 第三方 API |
| 告警确认/静默/转派 | 运维闭环 | 前端 + Agent API |

### 5.7 人机协同 (HITL / Manual Override)

- 操作员手动超控：紧急停机、手动设定点、检修旁路
- 权限分级：OPERATOR 调设定点 / ENGINEER 改模式 / ADMIN 全局 AUTO↔MANUAL
- 超控审计：谁、何时、改了什么、原值、新值、原因
- 自动回退：手动超控有超时窗口，过期自动切回 AUTO

### 5.8 数字孪生同步

Simulation Engine 的数字孪生模型定期与实际运行数据同步：校准 + 更新初始状态 → 仿真基线 = 实际工况。

---

## 6. 服务全景

```
现有 5 服务 → P2 后 6 服务 + acq_db

┌──────────────────────────────────────────────────────┐
│            React SPA 前端 + PWA 移动端                 │
└────────────────────────┬─────────────────────────────┘
                         │ HTTP + WebSocket
┌────────────────────────▼─────────────────────────────┐
│   API Gateway :8000                                   │
│   [+限流 + 熔断 + Prometheus /metrics + WebSocket]     │
└──┬──────────┬──────────┬──────────┬──────────┬───────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────────┐
│Asset │ │Env   │ │Sim   │ │Agent │ │Data Acq      │
│:8001 │ │:8002 │ │:8003 │ │:8004 │ │:8005 (NEW)   │
│      │ │      │ │      │ │      │ │              │
│asset │ │env_db│ │sim_db│ │agent │ │acq_db        │
│_db   │ │(TS)  │ │      │ │_db   │ │(TS NEW)      │
└──────┘ └──────┘ └──────┘ └──────┘ └──────────────┘
   │          │          │          │          │
   └──────────┴──────────┴──────────┴──────────┘
                  Redis Pub/Sub
```

## 7. 数据库实例总览

| 数据库 | 类型 | 服务 | 数据 |
|--------|------|------|------|
| asset_db | PostgreSQL | Asset Service | 设备、拓扑、点位、版本 |
| env_db | TimescaleDB | Environment Service | 气象、电价、建筑 |
| sim_db | PostgreSQL | Simulation Engine | 仿真任务、故障、校准 |
| agent_db | PostgreSQL | Agent Pipeline | 告警、策略、RL模型、审计 |
| **acq_db** | **TimescaleDB** | **Data Acquisition** | **设备运行时序 (NEW)** |
| gateway_db | PostgreSQL | Gateway | 用户、角色、RefreshToken |

## 8. 自检清单

- [x] 微服务边界清晰，无循环依赖
- [x] 读通路 (采集→存储→监控) 完整
- [x] 写通路 (优化→Safety→执行) 完整
- [x] 数据质量五层检测 + 归因 + ML
- [x] 渐进式投运 (SIMULATED→SHADOW→HYBRID→LIVE)
- [x] 边缘部署方案
- [x] 站内双层优化 + 站间协同
- [x] 碳交易通用框架 + CEA 适配
- [x] 测试/CI/CD/限流/熔断/Prometheus
- [x] 移动端 PWA + 报告导出 + 告警送达
- [x] HITL 人机协同超控
- [x] 数据填补策略
- [x] 模型校准覆盖冷机/塔/泵/阀
