# HVAC 制冷站全栈平台设计规格

> 日期: 2026-05-19 | 状态: 设计完成 | 版本: 1.0

## 1. 概述与目标

### 1.1 问题

当前系统（Phase 1-16）实现了制冷站物理仿真 + 多智能体管线，但存在根本性局限：

- 设备硬编码在 `__main__.py`（ch1/ch2 两台 500RT 主机）
- 无设备管理能力（无 CRUD、无类型模板）
- 前端仅单页 Dashboard，只读监控
- 不支持用户自定义制冷站拓扑
- 缺少阀门、管道、传感器的物理模型
- 环境参数仅几个固定值
- 强化学习仅做策略审批（approve/reject），未涉及运行参数优化

### 1.2 目标

将系统从"固定设备仿真演示"升级为**可配置、可扩展、可学习的制冷站数字孪生平台**。

### 1.3 核心原则

- **模板优先**：90% 场景通过模板覆盖，降低使用门槛
- **编辑与展示分离**：列表/表格编辑，画布只读展示
- **物理模型 + ML 互补**：物理模型提供 baseline，ML 积累数据后接管
- **Safety Gate 不可绕过**：所有 RL/自动控制输出必经安全检查
- **追加不覆盖**：配置变更 = 新版本，支持 diff 和回滚

---

## 2. 系统架构

### 2.1 微服务拆分

```
┌─────────────────────────────────────────────────────────┐
│                    React SPA 前端                        │
│                 Vite + React + TypeScript                │
│                    Port 5173 (dev)                       │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP + WebSocket
┌─────────────────────▼───────────────────────────────────┐
│               API Gateway · Port 8000                    │
│  路由 · JWT 认证 · 限流 · WebSocket 代理 · 审计日志       │
└──┬──────────────┬──────────────┬──────────────┬─────────┘
   │              │              │              │
   ▼              ▼              ▼              ▼
┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
│Asset │  │Env   │  │Sim   │  │Agent │
│Service│ │Service│ │Engine│  │Pipeline│
│:8001 │  │:8002 │  │:8003 │  │:8004 │
│      │  │      │  │      │  │      │
│asset │  │env_db│  │sim_db│  │agent │
│_db   │  │(Time-│  │      │  │_db   │
│      │  │scale) │  │      │  │      │
└──────┘  └──────┘  └──────┘  └──────┘
   │         │          │          │
   └─────────┴──────────┴──────────┘
             Redis Pub/Sub (事件总线)
```

### 2.2 服务职责

| 服务 | 端口 | 数据库 | 职责 |
|------|------|--------|------|
| API Gateway | 8000 | — | 路由、认证、限流、WebSocket |
| Asset Service | 8001 | asset_db (PG) | 设备CRUD、类型模板、采集点、Plant拓扑、版本管理 |
| Environment Service | 8002 | env_db (TimescaleDB) | 气象时序、电价、碳强、时序降采样 |
| Simulation Engine | 8003 | sim_db (PG) | 物理模型、仿真执行、故障注入、模型校准、What-if |
| Agent Pipeline | 8004 | agent_db (PG) | 多智能体管线、RL训练/推理、策略管理、告警、报告 |

### 2.3 服务间通信

- **同步 HTTP**：Simulation 从 Asset/Env 拉配置
- **异步事件**：Redis Pub/Sub 承载仿真完成、策略产出、告警等事件
- **WebSocket**：Gateway → 前端实时推送 KPI/告警/状态

---

## 3. 设备资产服务（Asset Service）

### 3.1 设备类型模板

每种设备类型预置一套采集点模板：

```
EquipmentType
  id, type_code, type_name, category, created_at

PointTemplate
  id, equipment_type_id, code, name, unit, data_type,
  io_direction (input/calc/output), required, sort_order
```

**io_direction 语义：**
- **INPUT**：仿真模型输入参数，需外部提供（用户设定/环境数据/上游设备）
- **CALC**：仿真模型计算值（COP、功率、PLR）
- **OUTPUT**：最终输出，用于展示/告警/KPI（运行状态、累计小时）

**示例 — 离心式冷水主机模板采集点：** chw_supply_temp (INPUT), chw_return_temp (INPUT), cw_entering_temp (INPUT), cw_leaving_temp (CALC), power_kw (CALC), current_load_rt (CALC), run_status (OUTPUT), cumulative_hours (OUTPUT) 等。

### 3.2 设备实例

```
Equipment
  id, name, equipment_type_id, plant_id, design_params (JSONB),
  position (用于画布展示), is_active, created_at, updated_at

EquipmentPoint
  id, equipment_id, point_template_id, custom_name,
  current_value, last_updated
  protocol_binding (JSONB, nullable)  -- 真实硬件对接时使用
```

创建设备时，系统从 EquipmentType → PointTemplate 自动生成 EquipmentPoint 实例。required=True 的采集点保证仿真可用。用户可追加自定义点位。

### 3.3 制冷站（Plant）与拓扑

```
Plant
  id, name, description, location, site_id,
  data_source_mode (simulated/live/hybrid),
  is_active, created_at, updated_at

Loop
  id, plant_id, name, fluid_type (chilled_water/cooling_water/hot_water),
  loop_type (primary/secondary/tertiary), is_active

PipeSegment
  id, loop_id, from_point_id, to_point_id,
  diameter_mm, length_m, roughness_mm, insulation_type,
  valve_id (nullable)

Header
  id, loop_id, header_type (supply/return), name

HeaderJunction
  id, header_id, point_id, direction (inlet/outlet)

Bypass
  id, plant_id, from_loop_id, to_loop_id,
  bypass_valve_id, bypass_pipe_segment_id
```

**拓扑构建方式：**

1. **模板优先（推荐）**：选预置模板 → 配置参数（几用几备）→ 下拉绑定设备 → 保存
2. **表格编辑器**：所有管段列为一表，行内编辑，适合微调和特殊拓扑
3. **向导模式**：4 步问答自动生成拓扑，适合零基础用户
4. **拓扑画布**：只读展示，自动布局，高亮选中元素，标注校验问题

### 3.4 预置模板库

| 模板 | 适用场景 | 复杂度 |
|------|----------|--------|
| 一次泵定流量 | 负荷稳定，小型站 | ★ |
| 一次泵变流量 | 负荷波动大，最常见 | ★★ |
| 二次泵变流量 | 区域供冷，一二次解耦 | ★★★ |
| 水蓄冷系统 | 峰谷套利 | ★★★ |
| 自由冷却系统 | 寒冷地区，过渡季板换 | ★★★ |

模板存储为 JSON 文件，包含：slots（设备槽位，含类型/角色/数量参数）、loops（回路定义）、connections（槽位→槽位的管段，含默认管径/长度）。

### 3.5 多制冷站（Site）

```
Site
  id, name, location, description, created_at

Plant.site_id → Site
```

Site 级功能：跨站能效对标（kW/RT、COP 排行、碳排强度）、统一告警视图、区域供冷协同优化。

---

## 4. 环境数据服务（Environment Service）

### 4.1 气象时间序列

存储 TMY（典型气象年）或实时气象数据：

```
WeatherRecord (TimescaleDB hypertable, 1h chunks)
  timestamp, outdoor_db_temp, outdoor_wb_temp, relative_humidity,
  solar_radiation_wm2, wind_speed_ms, wind_direction, cloud_cover
```

支持 CSV/TMY3/EPW 格式导入。

### 4.2 电价 & 碳强度

```
EnergyPrice (TimescaleDB)
  timestamp, electricity_price_per_kwh, carbon_intensity_kg_per_kwh
```

支持分时电价配置，碳强度对接外部数据源。

### 4.3 时序降采样策略

| 层级 | 分辨率 | 保留期 | 用途 |
|------|--------|--------|------|
| Raw | 1s | 7天 | 实时监控、故障分析 |
| 1min | 1分钟 | 3个月 | 趋势图表 |
| 15min | 15分钟 | 2年 | RL 训练、能效对标 |
| Hourly | 1小时 | 永久 | 年度报告、碳核算 |

使用 TimescaleDB continuous aggregation 自动降采样。

### 4.4 室内条件 & 建筑模型

```
BuildingModel
  id, name, area_m2, floor_count, orientation, window_wall_ratio,
  wall_u_value, roof_u_value, glass_shgc, building_type, location

IndoorCondition
  id, building_id, timestamp, indoor_temp, indoor_rh, co2_ppm,
  occupancy_count, lighting_power_kw, equipment_power_kw
```

---

## 5. 仿真引擎服务（Simulation Engine）

### 5.1 现有物理模型增强

**已有模型：** CentrifugalChiller、CoolingTower、Pump

**新增模型：**

#### 阀门（ControlValve / IsolationValve / CheckValve）

```
ControlValve:
  输入: 开度 x (0-1), 阀前压力 P1, 阀后压力 P2
  模型: Q = Cv · f(x) · √(ΔP/SG)
  特性: 等百分比 f(x)=R^(x-1), 线性 f(x)=x, 快开 f(x)=√x
  参数: Cv, characteristic, rangeability, actuator_speed, leakage_rate
  采集点: valve_position, inlet_pressure, outlet_pressure, flow_rate
```

#### 管道（PipeSegment 物理计算）

```
沿程阻力: ΔP_f = f · (L/D) · (ρ·v²/2)
  摩擦系数 f: Colebrook 方程迭代求解
  粗糙度 ε: 新钢管 0.045mm → 结垢后可达 0.5mm

局部阻力: ΔP_m = K · (ρ·v²/2)
  弯头 K=0.3, 三通 K=1.5, 变径 K=0.5

温降: ΔT = (T_fluid − T_ambient) · (1 − e^(−U·A/(ṁ·cp)))
  取决于保温层 U 值和管长
```

#### 传感器（TemperatureSensor / PressureSensor / FlowSensor / PowerSensor）

```
输出值 = 物理真值 + N(0, σ²) + drift(t) + 量化误差(resolution)
  σ: 精度参数 (温度 ±0.1°C)
  drift: 年漂移率 (0.05°C/年)
  resolution: 量化分辨率 (0.01°C)
```

### 5.2 拓扑求解器

仿真时将 Plant 拓扑视为有向图，迭代求解：

1. 展开所有 PipeSegment（点→点的连接）
2. 遍历每条管段：from_point 当前值 + 管段物理参数 → 计算 to_point 值
3. 在每个设备节点：收集所有 INPUT 点 → 调用设备模型 → 产出 CALC/OUTPUT 值
4. 迭代至收敛（类似电路求解，管道压降影响流量，流量影响设备工况）

### 5.3 故障注入框架

三种故障类型：

| 类型 | 示例 | 注入方式 |
|------|------|----------|
| 设备故障 | 主机喘振、水泵气蚀、阀门卡涩、传感器失效 | 修改模型参数或返回值 |
| 退化故障 | 冷凝器结垢、管道生锈、传感器漂移、制冷剂泄漏 | 随时间渐进修改参数 |
| 外部扰动 | 极端气象、电网波动、负荷突变、通讯中断 | 修改输入数据 |

接口：`POST /simulation/faults/inject {"device_id": "CH-1", "fault_type": "fouling", "severity": 0.3, "onset_time": 7200}`

### 5.4 模型校准

数字孪生闭环：采集真实数据 → 对比仿真输出 → 贝叶斯优化调参 → 更新模型参数 → 验证。

校准指标：COP 偏差、供水温度偏差、功率偏差。当连续偏差 > 5% 时触发自动校准。

### 5.5 仿真模式

```
SimulationMode:
  SIMULATED → 物理模型计算所有值
  LIVE → 从 BACnet/Modbus 读取真实值
  HYBRID → 部分真实 + 部分仿真（如真实传感器 + 仿真管道）
```

切换模式修改 Plant.data_source_mode 字段。

### 5.6 What-if 场景

场景 = 同一 Plant + 同一气象数据 + 不同控制参数覆盖值。并行跑全年 8760h 仿真，产出对比报告（年能耗、COP 分布、碳排放）。

---

## 6. 智能体管线服务（Agent Pipeline）

### 6.1 现有多智能体管线

保持现有 8 个 Agent + LangGraph 编排不变：
Monitor → Predict → Strategy → Advocates (Reliability/Efficiency/Compliance) → Coordinator → Safety → Parameter

### 6.2 强化学习控制优化（新增 DRL）

与现有 Bandit RL（审核策略 approve/reject）互补，新增直接控制参数的 DRL 控制器。

**MDP 定义：**

| 要素 | 内容 |
|------|------|
| 状态 S | 室外温湿度、当前/预测冷负荷、电价、碳强、各设备 PLR/COP/频率/累计小时、时段 |
| 动作 A | CHW 供水温度(5~12°C)、CW 进水温度(24~35°C)、各主机 PLR 分配、泵频率(0~50Hz)、塔风机频率、阀门开度、启停组合 |
| 奖励 R | w₁·COP − w₂·功率偏差 − w₃·启停次数 − w₄·surge风险 − w₅·温度超限 − w₆·碳排放。冷量不满足时大幅惩罚 |

**训练与推理：**
- **离线训练**：TMY 数据批量生成场景，仿真 100x 加速
- **在线推理**：每 5-15 分钟运行，输出最优动作
- **Safety Gate**：动作执行前校验冷却量充足性、设备安全边界、温变速率的束

**跨服务协作：** Simulation Engine 提供标准 RL 环境接口（`reset()`, `step(action) → (state, reward, done)`），Agent Pipeline 持有 RL Agent（策略网络 + 训练循环）。离线训练时 Agent Pipeline 高频调用 Simulation Engine 的环境步进；在线推理时 Agent Pipeline 只需一次前向传播。

**模型数据：**

```
RLTrainingEpisode
  episode_id, plant_id, step, state_vector, action_vector,
  reward, next_state_vector, done

RLModelCheckpoint
  model_version, algorithm (PPO/SAC/TD3), model_path,
  avg_reward, training_episodes, safety_violation_rate, is_active

ControlAction
  plant_id, timestamp, action_vector,
  safety_passed, was_executed, actual_cop_achieved
```

---

## 7. 冷负荷预测

### 7.1 输入特征

| 类别 | 特征 |
|------|------|
| 建筑参数 | 面积、朝向、窗墙比、外墙/屋顶 K 值、玻璃 SHGC、使用类型 |
| 室外气象 | 干/湿球温度、相对湿度、太阳辐射、风速、云量、未来 24h 预报 |
| 室内条件 | 当前温湿度、CO₂、设定温度、照明/设备功率密度 |
| 人员时间 | 人员密度、时刻(0-23)、星期几、节假日、活动类型、新风量标准 |

### 7.2 双路径预测

**路径 A — 物理模型（白盒，冷启动可用）：**
Q_total = Q_envelope + Q_solar + Q_infiltration + Q_people + Q_lighting + Q_equipment + Q_fresh_air

**路径 B — 数据驱动（黑盒，积累数据后使用）：**
XGBoost/LSTM/Transformer 模型，学习历史输入→负荷映射。

**融合策略：** 实际预测 = α·物理预测 + (1−α)·ML预测，α 随 ML 模型置信度动态调整。

### 7.3 输出

未来 15min / 1h / 6h / 24h 冷负荷预测曲线 (RT)，同时喂给 DRL 控制器和 Agent Pipeline。

---

## 8. API Gateway

### 8.1 路由

| 前缀 | 后端服务 |
|------|----------|
| `/api/equipment/*` | Asset Service :8001 |
| `/api/plants/*` | Asset Service :8001 |
| `/api/env/*` | Environment Service :8002 |
| `/api/simulation/*` | Simulation Engine :8003 |
| `/api/strategies/*` | Agent Pipeline :8004 |
| `/api/monitoring/*` | Agent Pipeline :8004 |
| `/api/reports/*` | Agent Pipeline :8004 |
| `/ws/*` | Agent Pipeline WebSocket |

### 8.2 认证 & 权限

JWT Bearer Token。五角色 RBAC：

| 角色 | 核心权限 |
|------|----------|
| Viewer | 只看仪表盘和历史 |
| Operator | 确认告警、执行策略、手动启停、不能改拓扑 |
| Engineer | 管理设备、构建拓扑、配置环境、不能删 Plant |
| Admin | 全部权限、管理用户、系统配置 |
| Auditor | 只读审计日志、导出报告 |

### 8.3 操作审计日志

所有写操作记录：who/when/what/old_value/new_value/ip_address。不可删除，保留 7 年。

---

## 9. 前端（React SPA）

### 9.1 技术栈

- Vite + React 18 + TypeScript
- 状态管理：React Query（服务端状态）+ Zustand（客户端状态）
- UI：Tailwind CSS + 自建组件库
- 图表：Recharts / ECharts
- 拓扑画布：React Flow（只读展示）
- 实时：WebSocket 连接 Gateway

### 9.2 页面结构

| 页面 | 功能 |
|------|------|
| Dashboard | 总览 KPI、COP 趋势、设备状态、最近告警 |
| 设备管理 | 设备类型浏览、设备 CRUD、采集点查看 |
| 制冷站 | Plant 列表、模板创建、表格编辑器、拓扑画布（只读） |
| 环境配置 | TMY 气象数据导入/查看、电价曲线、建筑模型 |
| 仿真控制 | 启动/停止仿真、故障注入、What-if 场景、校准状态 |
| 策略中心 | 策略历史、RL 模型状态、控制参数建议、手动审批 |
| 报告 | 日报/月报/年报废、能效对标、碳排放报告 |
| 告警中心 | 实时告警流、告警规则配置、确认/抑制/升级 |
| 系统设置 | 用户管理、角色权限、审计日志、版本历史 |
| 个人设置 | 个人信息、密码修改、通知偏好 |

---

## 10. 告警引擎

### 10.1 告警规则

```yaml
rule: chiller_surge_risk
condition: equipment.ch-1.surge_risk > 0.8
duration: 60s        # 持续 60 秒才触发（防抖）
severity: critical
group: equipment_protection
```

### 10.2 抑制 & 升级

**抑制规则：** 父设备 OFF → 抑制子设备告警、维修模式 → 抑制已知告警、5 分钟内同因去重、告警风暴检测（>50条/分钟）。

**升级策略：** critical 5分钟未确认 → 电话通知、critical 30分钟未确认 → 通知上级、warning 4小时未确认 → 升级为 critical。

---

## 11. 配置版本化

### 11.1 可版本化实体

Plant 拓扑、设备参数、控制策略、RL 模型权重。

### 11.2 版本模型

```
EntityVersion
  entity_type, entity_id, version (自增整数), snapshot (完整 JSON),
  diff_from_prev (增量 diff), changed_by, change_reason, created_at
```

**原则：追加不覆盖。** 每次变更创建新版本。回滚 = 从历史选目标版本 → 预览 diff → 确认 → 创建新版本。回滚前自动跑仿真验证。

---

## 12. 硬件对接路径（远期）

### 12.1 数据源适配器

通过 EquipmentPoint.protocol_binding 存储协议映射：

```json
{ "protocol": "bacnet", "device_id": 2401,
  "object_type": "analog_input", "instance": 12,
  "poll_interval_sec": 5 }

{ "protocol": "modbus", "slave_id": 3,
  "register": 40001, "function_code": 3,
  "scale": 0.1, "offset": 0 }

{ "protocol": "opc_ua", "node_id": "ns=2;s=Temperature",
  "poll_interval_sec": 1 }
```

### 12.2 模式切换

Plant.data_source_mode 切换 SIMULATED → HYBRID → LIVE，逐步从纯仿真过渡到真实运行。

---

## 13. 数据实体总览

### 新增 DB 表

**Asset Service (asset_db):**
EquipmentType, PointTemplate, Equipment, EquipmentPoint, Plant, Site, Loop, PipeSegment, Header, HeaderJunction, Bypass, EntityVersion

**Environment Service (env_db, TimescaleDB):**
WeatherRecord (hypertable), EnergyPrice (hypertable), BuildingModel, IndoorCondition, LoadPrediction

**Simulation Engine (sim_db):**
FaultScenario, FaultEvent, CalibrationRun, Scenario, ScenarioResult

**Agent Pipeline (agent_db):**
已有（PlantSnapshot, Alert, Strategy, Report, MemoryLog 等）+ AlertRule, AlertGroup, RLTrainingEpisode, RLModelCheckpoint, ControlAction, AuditLog

**Gateway:**
User, Role, UserRole, RefreshToken

---

## 14. 实现优先级

### P0（第一版必须）

- 设备类型模板 + 设备 CRUD + 采集点自动生成
- Plant 拓扑（模板 + 表格编辑器 + 只读画布）
- 阀门/管道/传感器物理模型
- 仿真引擎动态构建（从 DB 加载配置）
- 用户认证 + RBAC（五角色）
- React SPA 框架搭建 + Dashboard + 设备管理 + 制冷站页面
- 拓扑校验规则
- 时序数据四级降采样
- 环境数据服务（TMY 导入 + 电价）

### P1（第二版重要）

- 冷负荷预测（物理 + ML 双路径）
- DRL 控制参数优化 + Safety Gate
- 故障注入框架
- 告警规则引擎 + 抑制 + 升级
- What-if 场景对比
- 配置版本化 + 回滚
- 多制冷站能效对标
- 操作审计日志

### P2（远期）

- 真实硬件对接（BACnet/Modbus/OPC UA）
- 模型自动校准
- 区域供冷协同优化
- 碳排放交易对接
- 移动端适配

---

## 15. 自检清单

- [x] 无 TBD/TODO 占位
- [x] 架构图与功能描述一致
- [x] 微服务边界清晰，无循环依赖
- [x] 所有新增 DB 表已列出
- [x] API 路由规划完整
- [x] 安全机制（认证/RBAC/Safety Gate/审计）覆盖关键路径
- [x] 数据生命周期（降采样/保留期）已定义
- [x] 仿真→真实硬件的迁移路径明确
- [x] 现有代码迁移路径明确

---

## 16. 现有代码迁移路径

当前代码库（Phase 1-16）已有完整的仿真模型、智能体管线和 FastAPI 后端。迁移到微服务架构时：

**保留并迁移的代码：**

| 现有模块 | 目标位置 | 说明 |
|----------|----------|------|
| `src/simulation/` (chiller, pump, cooling_tower) | Simulation Engine | 直接复用，新增阀门/管道/传感器模型 |
| `src/agents/` (全部 8 个 Agent) | Agent Pipeline | 直接复用，管线不变 |
| `src/optimization/` | Agent Pipeline | 复用优化求解器 |
| `src/graph/` | Agent Pipeline | LangGraph 编排逻辑 |
| `src/schemas/` | 各服务 | PlantSnapshot 等基础 schema 在服务间共享 |
| `src/control/` | Agent Pipeline | PID、互锁、死区逻辑作为 Safety Gate 的一部分 |
| `src/rl/` (bandit) | Agent Pipeline | 现有 Bandit RL 保留，新增 DRL 控制器 |
| `src/db/` | 各服务 | ORM 模型拆分到各自服务 |
| `src/reports/` | Agent Pipeline | 报告生成逻辑 |
| `src/rag/` | Agent Pipeline | RAG 检索 |
| `src/curves/` | Simulation Engine | 性能曲线辨识 |

**替换的代码：**

| 现有 | 替换为 | 原因 |
|------|--------|------|
| `src/__main__.py` 硬编码 ch1/ch2 | Asset Service 动态加载 | 设备需用户定义 |
| `src/api/main.py` 单 FastAPI app | API Gateway 多服务路由 | 微服务拆分 |
| `src/static/dashboard.html` 单页 | React SPA | 功能大幅扩展 |
| `ChillerPlant.__init__` 构造函数传入设备 | 从 DB 读取 Plant 拓扑动态构建 | 解耦配置与代码 |
| 内存存储 `_plant_snapshots` / `_alerts` | 各服务独立 DB | 持久化与扩展性 |

**迁移策略：** P0 阶段先搭建微服务骨架 + 新功能，现有 Agent Pipeline 代码整体保留在 Agent Pipeline 服务内，现有仿真模型整体保留在 Simulation Engine 内。不做大规模重写，只在接口层面适配微服务通信。
