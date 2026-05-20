# HVAC 制冷站平台 P3 设计规格

> 日期: 2026-05-20 | 状态: 设计完成 | 版本: 1.0

## 1. 概述

### 1.1 P0-P2 回顾

| 阶段 | 交付 |
|------|------|
| P0 | 微服务骨架 (5服务) + 设备CRUD + 制冷站拓扑 + 仿真引擎 + 智能体管线 + API Gateway + React SPA |
| P1 | 冷负荷预测 + DRL优化 + 故障注入 + 告警引擎 + What-if + 版本化 + 能效对标 + 审计日志 |
| P2 | 硬件采集服务 + 模型校准 + 数据质量5层 + MAPPO多智能体RL + 站间调度 + 碳交易 + 生产化加固 |

### 1.2 P3 目标

将系统从"单站数字孪生平台"升级为**可边缘自主运维、云端集中分析、预测性维护闭环**的多站智能运维平台。

### 1.3 核心场景

- **边缘自主运维**：采集 + 实时控制 + 自动巡检 + 本地工单，断网不瘫痪
- **预测性维护**：基于退化追踪和ML的故障预测，自动生成维护计划
- **边缘-云协同**：边缘跑实时控制/巡检/推理，云端跑分析/训练/跨站对标
- **弹性部署**：标准站 Docker 部署，低配工控机裸进程，共用代码库

### 1.4 核心原则

- **断网自主**：实时控制、巡检、工单在边缘端独立闭环
- **边缘优先**：数据在边缘预处理和降采样，云端做聚合分析和模型训练
- **渐进投运**：沿用 P2 的 simulated→shadow→hybrid→live 四级模式
- **最小依赖**：边缘端零外部服务依赖（嵌入式 DB + ONNX Runtime）

## 2. 系统架构

### 2.1 整体拓扑

```
每个制冷站 — 边缘层
┌──────────────────────────────────────────────┐
│  hvac-edge  (单体进程)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ 采集引擎  │ │ 控制引擎  │ │ 巡检引擎      │  │
│  │ Modbus   │ │ Safety   │ │ 点检计划      │  │
│  │ BACnet   │ │ Gate     │ │ 异常检测(L1)  │  │
│  │ OPC UA   │ │ PID/互锁  │ │ 本地工单      │  │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘  │
│       └────────────┴───────────────┘          │
│                    │                          │
│  ┌─────────────────▼──────────────────────┐   │
│  │ 本地存储 (DuckDB) + 边缘AI (ONNX)       │   │
│  └─────────────────┬──────────────────────┘   │
│                    │                          │
│  ┌─────────────────▼──────────────────────┐   │
│  │ Sync Agent (MQTT + HTTP Bulk)          │   │
│  └────────────────────────────────────────┘   │
└──────────────────┬───────────────────────────┘
                   │ MQTT (实时) + HTTP (批量)
┌──────────────────▼───────────────────────────┐
│  云端 — 扩展现有服务                            │
│                                               │
│  ┌──────────┐ ┌──────────────┐                │
│  │ MQTT     │ │ Edge Manager │ ← 新增         │
│  │ Broker   │ │ Service :8006│                │
│  └────┬─────┘ └──────┬───────┘                │
│       │              │                        │
│  ┌────▼──────────────▼────────┐               │
│  │ Agent Service :8004 (扩展)  │               │
│  │ + 预测维护引擎               │               │
│  │ + 工单系统                   │               │
│  │ + 模型训练 → ONNX 导出       │               │
│  └────────────────────────────┘               │
│                                               │
│  其余5个微服务保持不变                           │
└──────────────────────────────────────────────┘
```

### 2.2 新增/变更清单

| 组件 | 类型 | 说明 |
|------|------|------|
| `hvac-edge` | **新建** | 边缘单体进程，独立 Python 包 |
| MQTT Broker (Mosquitto) | **新建** | 边-云实时通信通道 |
| Edge Manager Service :8006 | **新建** | 云端边缘设备生命周期管理 |
| Agent Service 扩展 | **变更** | +预测维护引擎 +工单系统 +ONNX导出 |
| DuckDB | **新建** | 边缘端嵌入式分析型存储 |

### 2.3 关键技术选型

| 选型 | 替代方案 | 理由 |
|------|---------|------|
| DuckDB（边缘） | SQLite | 原生时序窗口函数、Parquet 导出、OLAP 分析 |
| MQTT（边-云） | Redis Pub/Sub | 弱网友好、断线重连、QoS分级 |
| ONNX Runtime（边缘） | PyTorch 直接推理 | 轻量无框架依赖、推理快 |
| XGBoost（云端训练） | 深度学习 | 表格数据最优、ONNX导出成熟、可解释 |
| Mosquitto | EMQX/Vernemq | 轻量、Docker 友好、社区活跃 |

## 3. 边缘端 hvac-edge

### 3.1 进程拓扑

单进程、多模块、asyncio 协程并发。

```
hvac-edge/
├── pyproject.toml
├── edge/
│   ├── __init__.py
│   ├── main.py                 # 入口 + 生命周期管理
│   ├── config.py               # 本地 YAML 配置（模式/采集/控制/巡检/ML）
│   ├── db.py                   # DuckDB 连接管理
│   ├── engine/
│   │   ├── collector.py        # 采集引擎
│   │   ├── controller.py       # 控制引擎（Safety Gate + PID + 互锁）
│   │   └── inspector.py        # 巡检引擎（点检计划 + L1异常 + 本地工单）
│   ├── ml/
│   │   ├── runtime.py          # ONNX Runtime 推理封装
│   │   └── models/             # 放置 .onnx 模型文件
│   ├── sync/
│   │   ├── agent.py            # Sync Agent：MQTT + HTTP Bulk + 离线缓冲
│   │   └── queue.py            # 持久化离线队列（DuckDB 表）
│   └── templates/              # 巡检计划 YAML 模板
└── tests/
```

### 3.2 三大引擎

| 引擎 | 职责 | 实现来源 |
|------|------|---------|
| collector | 从硬件读点位，写入 DuckDB，推送最新值到 controller | 复用现有 3 协议适配器，去掉 HTTP 层 |
| controller | Safety Gate 校验 + PID 调节 + 设备互锁 + 执行指令写回硬件 | 移植 agent/agents/safety.py + src/control/ |
| inspector | 按计划执行点检项，L1异常检测，生成本地工单 | 移植 simulation/data_quality/realtime_rules.py Layer 1 |

### 3.3 DuckDB 本地存储

单文件 `edge_data.duckdb`，4 张核心表：

```sql
CREATE TABLE readings (
    time       TIMESTAMPTZ NOT NULL,
    point_id   VARCHAR(32) NOT NULL,
    value      DOUBLE NOT NULL,
    quality    VARCHAR(16) DEFAULT 'good',
    PRIMARY KEY (time, point_id)
);

CREATE TABLE inspections (
    id         BIGINT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at   TIMESTAMPTZ,
    plan_id    VARCHAR(64) NOT NULL,
    status     VARCHAR(16) DEFAULT 'running',
    result     JSON
);

CREATE TABLE work_orders (
    id            BIGINT PRIMARY KEY,
    created_at    TIMESTAMPTZ NOT NULL,
    equipment_id  VARCHAR(32) NOT NULL,
    severity      VARCHAR(16) NOT NULL,
    title         VARCHAR(256) NOT NULL,
    description   TEXT,
    status        VARCHAR(16) DEFAULT 'open',
    synced_at     TIMESTAMPTZ
);

CREATE TABLE sync_queue (
    id         BIGINT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    topic      VARCHAR(128) NOT NULL,
    payload    JSON NOT NULL,
    qos        TINYINT DEFAULT 1,
    retries    INT DEFAULT 0,
    synced     BOOLEAN DEFAULT FALSE
);
```

### 3.4 运行模式配置

```yaml
mode: hybrid  # simulated | shadow | hybrid | live

control:
  safety_gate: true
  pid_enabled: true
  interlock_enabled: true

acquisition:
  poll_interval_ms: 1000
  protocols:
    - type: modbus
      port: /dev/ttyUSB0
      baudrate: 19200

inspection:
  plans_dir: /etc/hvac-edge/plans/
  default_interval_hours: 4

ml:
  onnx_model_path: /etc/hvac-edge/models/anomaly_v1.onnx
  feature_window_hours: 24
```

## 4. 云端新增与扩展

### 4.1 Edge Manager Service :8006

职责：边缘设备生命周期管理（注册、心跳、配置下发、OTA升级）。

```
services/edgemanager/
├── pyproject.toml
├── Dockerfile
├── edgemanager_service/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py            # EdgeDevice, Heartbeat, OTARecord
│   └── api/
│       ├── __init__.py
│       ├── registry.py       # 设备注册/注销/列表
│       ├── heartbeat.py      # 心跳接收/超时检测
│       ├── config.py         # 配置下发/回传
│       ├── data.py           # 时序数据批量接收
│       └── ota.py            # 固件/模型/巡检计划升级
└── tests/
```

**核心表：**

```sql
CREATE TABLE edge_devices (
    id            VARCHAR(32) PRIMARY KEY,
    name          VARCHAR(128) NOT NULL,
    plant_id      VARCHAR(32) NOT NULL,
    mode          VARCHAR(16) DEFAULT 'hybrid',
    version       VARCHAR(32) NOT NULL,
    config_hash   VARCHAR(64),
    registered_at TIMESTAMPTZ NOT NULL,
    last_seen_at  TIMESTAMPTZ
);

CREATE TABLE heartbeats (
    id            BIGINT PRIMARY KEY,
    edge_id       VARCHAR(32) NOT NULL,
    received_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cpu_pct       DOUBLE,
    mem_mb        DOUBLE,
    disk_pct      DOUBLE,
    collector_ok  BOOLEAN,
    controller_ok BOOLEAN,
    inspector_ok  BOOLEAN
);

CREATE TABLE ota_tasks (
    id            BIGINT PRIMARY KEY,
    edge_id       VARCHAR(32) NOT NULL,
    target_type   VARCHAR(16) NOT NULL,
    version       VARCHAR(32) NOT NULL,
    payload_url   VARCHAR(512) NOT NULL,
    status        VARCHAR(16) DEFAULT 'pending',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

CREATE TABLE sync_watermarks (
    edge_id       VARCHAR(32) NOT NULL,
    table_name    VARCHAR(64) NOT NULL,
    last_synced_until TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (edge_id, table_name)
);
```

**API 路由：**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/edges/register` | 设备首次注册 |
| POST | `/api/edges/:id/heartbeat` | 心跳上报 |
| GET | `/api/edges/` | 边缘设备列表 |
| GET | `/api/edges/:id/status` | 设备详情 |
| POST | `/api/edges/:id/config` | 配置下发 |
| POST | `/api/edges/:id/ota` | 创建OTA任务 |
| GET | `/api/edges/:id/ota/:task_id` | OTA任务状态 |
| POST | `/api/edges/:id/data/ingest` | 批量时序数据接收 |

### 4.2 MQTT Topic 规范

```
hvac/{edge_id}/alert          # 边→云：告警实时推送 (QoS 1)
hvac/{edge_id}/status         # 边→云：引擎状态变更 (QoS 1)
hvac/{edge_id}/control        # 云→边：控制指令/超控 (QoS 1)
hvac/{edge_id}/config         # 云→边：配置变更通知 (QoS 1)
hvac/{edge_id}/ota            # 云→边：OTA通知 (QoS 1)
```

### 4.3 Agent Service 扩展：预测维护引擎

```
services/agent/agent_service/predictive_maintenance/
├── __init__.py
├── degradation_tracker.py    # 设备退化趋势追踪（COP衰减、振动上升、CUSUM突变检测）
├── failure_predictor.py      # 故障概率预测（XGBoost → ONNX导出）
├── maintenance_scheduler.py  # 维护窗口推荐（最小影响时段）
├── rule_advisor.py           # 规则引擎：退化阈值 → 维护建议
└── api/
    └── maintenance.py        # REST API
```

**退化追踪策略（每种设备类型一组）：**

- COP 相对设计值滑动窗口中位数偏移
- 逼近温度（approach temperature ΔT）变化
- 振动谱能量百分比变化
- CUSUM 突变点检测
- 综合等级：normal / degrading / critical

**模型训练与导出流程：**

```
云端每周/每月汇总各站数据 → 训练 XGBoost 故障分类器
→ onnxmltools 导出 .onnx
→ Edge Manager OTA 下发
→ 边缘 ONNX Runtime 加载，实时推理
```

### 4.4 Agent Service 扩展：工单系统

```
services/agent/agent_service/workorder/
├── __init__.py
├── models.py          # WorkOrder, WorkOrderLog
├── lifecycle.py       # 状态机：open→acknowledged→in_progress→resolved→closed (rejected)
├── auto_generator.py  # 从巡检异常/退化告警自动生成工单
├── assignment.py      # 按角色/技能自动分配
└── api/
    └── workorders.py
```

**工单来源优先级：**

| 来源 | 触发条件 | 优先级 |
|------|----------|--------|
| 巡检异常 | 点检项连续 3 次不通过 | warning |
| 退化告警 | degradation_tracker severity=critical | critical |
| ML 异常 | ONNX 推理 score > 0.85 | critical |
| 阈值告警 | 实时值超硬限 | 取决于参数 |

### 4.5 数据库变更汇总

| 数据库 | 新增表 |
|--------|--------|
| `edge_db` (新) | edge_devices, heartbeats, ota_tasks, sync_watermarks |
| `agent_db` (扩展) | degradation_results, failure_predictions, maintenance_plans, work_orders, work_order_logs |

## 5. 同步协议

### 5.1 同步水位线

每张表维护 watermark，只拉增量：

- 云端：`sync_watermarks(edge_id, table_name) → last_synced_until`
- 边缘：`sync_meta(table_name) → last_sent_at`

流程：定期(30s) tick → SELECT 增量 → DuckDB 15min 窗口聚合 → NDJSON → HTTP POST → 更新水位线

### 5.2 通信分工

| 数据 | 通道 | 方式 | QoS |
|------|------|------|-----|
| 告警通知 | MQTT | 实时单条 | 1 |
| 状态变更 | MQTT | 实时单条 | 1 |
| 控制指令 | MQTT | 实时单条 | 1 |
| 时序读数 | HTTP | 30s 批量，15min 窗口聚合 (min/max/avg/std) | — |
| 巡检结果 | HTTP | 任务结束时发送 | — |
| 工单变更 | HTTP | 状态转移时发送 | — |
| 心跳 | MQTT | 30s 轻量 JSON | 1 |

### 5.3 离线缓冲与断点续传

- 断网检测：连续 3 次 MQTT PING 无响应 → offline
- 断网期间：readings 写 DuckDB（无上限）、alerts 入 sync_queue、控制独立运行
- 恢复连接：MQTT 重连 + sync_queue FIFO 重放 + HTTP 批量补传读数（每批 5000 行，云端 UPSERT 去重）
- 工单冲突：last_updated_at 取胜
- 配置冲突：云端优先，边缘拒绝降级

### 5.4 运维流程闭环

```
边缘：collector → readings → inspector 点检 → ONNX 推理(L2)
  → 异常? No → 日志 / Yes → 本地工单(open) + MQTT告警
  → 现场确认(acknowledged) → 维修(in_progress) → 复检(resolved) → 同步(closed)

云端：汇聚 N 站 readings → degradation_tracker
  → failure_predictor (XGBoost) → maintenance_scheduler
  → 生成维护计划推送边缘
  → 周期训练新模型 → ONNX导出 → OTA → 边缘模型更新

闭环验证：维修后连续 7 天 COP 恢复至设计值 ±3% → 标记工单有效 → 反馈训练标签
```

## 6. 实施优先级

### P3-A（第一优先）：边缘基础 + 实时控制 + 同步

- hvac-edge 项目骨架 + DuckDB + 配置系统
- collector 采集引擎（移植三协议适配器）
- controller 控制引擎（Safety Gate + PID + 互锁）
- Sync Agent（MQTT + HTTP Bulk + 离线缓冲）
- Edge Manager Service + MQTT Broker 集成
- Docker Compose + 裸进程双部署模式

### P3-B（第二优先）：巡检自动化 + 工单闭环

- inspector 巡检引擎（点检计划 + L1异常）
- 本地工单系统（状态机 + auto_generator）
- 云端工单系统（lifecycle + assignment）
- 巡检计划模板与 OTA 下发
- 巡检报告导出（DuckDB → Parquet → 前端展示）

### P3-C（第三优先）：预测维护 + 边缘 AI

- degradation_tracker 退化追踪（CUSUM + COP/振动/逼近温度）
- XGBoost 故障分类器训练
- ONNX 模型导出 → OTA 下发 → 边缘 ONNX Runtime 推理
- maintenance_scheduler 维护窗口推荐
- 工单闭环验证与训练标签反馈

### P3-D（远期）：多站聚合与 UI

- 多站健康仪表盘（前端新增页面）
- 边缘设备管理 UI（注册/状态/OTA）
- 跨站维护优先级排序
- 维护知识库（工单→故障→处理方案关联）

## 7. 自检清单

- [x] 无 TBD/TODO 占位
- [x] 架构图与功能描述一致
- [x] 边缘-云边界清晰，无循环依赖
- [x] 所有新增 DB 表已列出
- [x] API 路由规划完整
- [x] 断网自主运行方案完整
- [x] 离线缓冲与冲突处理已定义
- [x] 渐进投运模式延续 P2 设计
- [x] 预测维护算法选型与理由明确
- [x] 双部署模式（Docker/裸进程）覆盖弹性硬件
