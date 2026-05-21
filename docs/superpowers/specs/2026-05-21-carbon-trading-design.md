# 碳排放与碳交易系统设计

**日期**: 2026-05-21
**状态**: 设计完成，待实现

## 一、背景与目标

HVAC制冷站多智能体系统已具备基础碳排放计算能力（排放因子法、CEA区域因子、碳成本优化、合规审查），但缺少碳交易能力和完整的碳资产管理体系。

### 目标

1. 实现完整的碳资产管理（CEA配额 + CCER 自愿减排量）
2. 构建模拟碳交易市场（连续竞价订单簿 + 做市商 + 虚拟参与者），架构可切换至真实交易所
3. 分钟级碳排放监测与T+0交易结算
4. 覆盖配额分配→排放→交易→履约清缴的完整闭环
5. 前端碳管理专用页面

### 非目标（本期不做）

- 对接真实上海/北京碳交易所API（接口预留）
- AI驱动的碳交易策略（后续迭代）
- 碳排放权期货/期权等衍生品

## 二、市场机制设计

### 市场蓝本

以中国全国碳市场（CEA，上海环境能源交易所）为蓝本：
- 配额发放：免费分配为主 + 有偿竞买为辅
- 交易机制：连续竞价（价格优先→时间优先）
- 履约周期：年度履约，年末清缴
- CCER抵消上限：应缴配额的 5%

### 碳价形成机制（混合模式）

| 组成部分 | 说明 |
|----------|------|
| 连续竞价订单簿 | 买卖双方挂单撮合，价格优先→时间优先 |
| 做市商 | 基准价 ± spread 双向报价，保证基础流动性 |
| 虚拟参与者 | 4种策略模拟外部对手，提供价格发现 |

### 交易对手

- 内部多站（plant-to-plant）：站间调拨 + 限价/市价交易
- 虚拟合规买家：临近履约期集中买入
- 虚拟投机交易者：低买高卖套利
- 虚拟盈余卖出者：配额富余时持续卖出
- 虚拟CCER持有者：在价差合适时出售CCER

## 三、架构设计

### 整体方案

采用混合架构——碳规则引擎（排放计算、碳成本、合规审查）留在 agent_service 内，交易与资产管理作为 agent_service 的内部模块，market_adapter 提供可插拔的模拟↔真实市场切换：

```
services/agent/agent_service/carbon/
├── emission/              # 排放监测（分钟级实时）
│   ├── emission_monitor   # 从acquisition拉数据，写入时序表
│   ├── emission_calc      # 扩展——增加基准线法、CCER减排量核算
│   └── factor_registry    # 排放因子管理（区域、季节、时段）
├── assets/                # 碳资产台账 + 预算
│   ├── allowance_mgr      # 配额生命周期（分配→消费→清缴）
│   ├── ccer_mgr           # CCER项目注册/核证/签发
│   ├── budget_planner     # 碳预算编制与预警
│   └── profit_loss        # 碳资产损益分析
├── trading/               # 交易引擎
│   ├── order_book         # 买卖簿维护（sortedcontainers）
│   ├── matching_engine    # 撮合引擎（价格优先→时间优先）
│   ├── settlement         # T+0 即时结算
│   └── trade_history      # 成交历史查询
├── compliance/            # 履约管理
│   ├── mrv_engine         # 监测-报告-核查
│   ├── surrender          # 履约清缴
│   └── audit_trail        # 审计线索
└── market_adapter/        # ← 可插拔接口
    ├── interface.py       # CarbonMarketAdapter Protocol (18个方法)
    ├── simulated_market   # 模拟市场实现
    └── (real_connector)   # 未来：真实交易所对接
```

### 与其他模块的关系

```
acquisition service (功率/冷量/COP)
        │ 分钟级点位
        ▼
agent_service/carbon/emission/ ← 读取原始数据，计算排放
        │
        │ tCO2 数据
        ▼
src/optimization/solver.py  ← 碳成本纳入 MILP 目标函数 (已有)
src/agents/advocates/compliance.py ← 合规审查 (已有，需扩展)
        │
        │ 优化结果（含碳决策）
        ▼
agent_service/carbon/trading/ ← 执行交易策略
agent_service/carbon/compliance/ ← 履约清缴
```

## 四、数据模型

### ER关系

```
carbon_ledger        ← 碳资产流水账（复式记账，所有配额变动都在这）
├── entry_type: allocation | auction_purchase | emission | market_buy
│              | market_sell | surrender | ccer_offset | penalty
│              | transfer_in | transfer_out | ccer_issued
├── direction: debit(减少) | credit(增加)
├── links: emission_id?, trade_id?, compliance_id?
└── balance_after: 变动后余额（冗余，加速查询）

carbon_emissions     ← 分钟级排放（TimescaleDB hypertable）
├── 每小时自动分区，24h后压缩
├── 连续聚合：1h → 1d → 1month 物化视图
└── 保留策略：原始1个月，聚合3年

carbon_orders        ← 订单簿
├── side: buy/sell, allowance_type: CEA/CCER
├── order_type: market/limit/iceberg
├── status: pending → partial_fill → filled/cancelled
└── 卖单挂出时锁定配额（ledger available↓, locked↑）

carbon_trades        ← 成交记录（T+0即时生成）
carbon_compliance    ← 履约记录
carbon_holdings_snapshot ← 日终持仓快照
carbon_price_history ← 价格历史（OHLCV）
carbon_auctions      ← 有偿竞买
```

### 关键设计原则

1. **ledger 为核心**：所有配额变动写入流水，余额可全程追溯
2. **锁仓机制**：卖单挂出即锁定配额，防止超额卖出
3. **时序优化**：emissions 表使用 TimescaleDB（如不可用则普通分区+定时聚合）
4. **快照冗余**：日终快照避免历史查询全表 SUM

## 五、交易引擎设计

### 撮合规则

- 价格优先 → 时间优先（与真实交易所一致）
- 可成交条件：买单价格 >= 卖方最低价；卖单价格 <= 买方最高价
- 市价单：立即按对手最优价成交，剩余未成交部分自动撤销
- 限价单：满足价格条件时成交，否则入簿等待
- Iceberg订单：仅暴露 peak_qty，成交后自动补充

### 做市商参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 基准价 | 上一笔成交价 | 或初始碳价 80元/t |
| 买卖价差 | 基准价 ± 2% | 可配置 |
| 单笔深度 | 500-2000吨 | 每侧，可配置 |
| 刷新频率 | 30秒/成交后 | 可配置 |
| 库存风控 | 净头寸 > 阈值时调整报价倾斜 | 可配置 |

### 虚拟参与者策略

| 类型 | 行为 | 占比 | 模拟对象 |
|------|------|------|----------|
| 合规买家 | 临履约期集中买入，平时观望 | ~30% | 配额不足的控排企业 |
| 投机交易者 | 价格低买高卖，日内/跨期套利 | ~25% | 金融机构/碳基金 |
| 盈余卖出者 | 配额富余时持续挂卖单 | ~25% | 高效能/减产企业 |
| CCER持有者 | 价差合适时出售CCER | ~20% | 新能源/减排项目业主 |

## 六、Market Adapter 接口

定义 `CarbonMarketAdapter` Protocol，18个方法，分为 5 组：

```
行情 (Market Data):
  get_order_book, get_latest_price, get_ohlcv, subscribe_tick

交易 (Trading):
  place_order, cancel_order, get_order, get_my_orders, get_my_trades, get_trade_fee

配额生命周期 (Allowance Lifecycle):
  receive_allocation, participate_auction, transfer, surrender

持仓 (Holdings):
  get_holdings, get_holdings_snapshot

市场元数据 (Market Info):
  get_market_calendar, get_compliance_deadline
```

### 切换方式

```python
# 配置驱动，启动时注入
config = {"carbon.market_adapter": "simulated"}
adapter: CarbonMarketAdapter = create_adapter(config)
# 未来: config = {"carbon.market_adapter": "shanghai_ee", "api_key": "..."}
```

## 七、CCER 生命周期（模拟简化版）

| 阶段 | 真实流程 | 模拟简化 |
|------|----------|----------|
| 项目识别 | 选择方法学，编写PDD | COP同比提升>5% 或能耗强度下降>3%时自动触发 |
| 减排量计算 | 基准线排放 - 项目排放 | 历史COP基准线 × 当前冷量 = 基准排放；实际 - 基准 = 减排量，每月核算 |
| 核证 | DOE现场审核 | 每季度自动核证，1-3天延迟，95-99%通过率 |
| 签发 | 主管部门登记 | 5-15天审批延迟，签发后写入ledger(ccer_issued) |
| 交易 | 挂牌交易 | 与CEA同订单簿，价格通常为CEA的40-80% |
| 抵消 | 用于履约，上限5% | 履约时自动计算CCER可用量 |

制冷站方法学基准：采用历史COP基准线法（改造前12个月COP加权平均）。
CCER年产上限 = 年排放量 × 20%。

## 八、API 设计

### REST 端点（5组）

```
/api/carbon/emissions     排放监测
  GET /realtime            当前分钟快照
  GET /history             历史时序
  GET /summary             期间汇总
  GET /factors             排放因子配置

/api/carbon/holdings       碳资产
  GET /                    持仓总览
  GET /ledger              资产流水
  POST /allocate           发放配额
  POST /transfer           站间调拨

/api/carbon/trading        交易
  GET /order-book          订单簿深度
  POST /orders             下单
  DELETE /orders/{id}      撤单
  GET /orders              我的订单
  GET /orders/{id}         订单详情
  GET /trades              成交历史

/api/carbon/compliance     履约管理
  GET /status              履约进度
  POST /surrender          提交清缴
  GET /history             历史履约
  GET /report              MRV报告

/api/carbon/market         行情信息
  GET /price               最新价
  GET /ohlcv               K线数据
  GET /calendar            交易日历
  GET /auctions            拍卖列表
  POST /auctions/{id}/bid  参与竞买
```

### WebSocket 推送（5个频道）

| 频道 | 内容 | 频率 |
|------|------|------|
| tick | 最新成交价+量 | 每笔成交 |
| depth | 订单簿深度更新 | 变化时 |
| emission | 实时排放数据 | 每分钟 |
| alert | 配额不足/履约预警 | 触发时 |
| big_trade | 大单成交公告(>500t) | 触发时 |

### 现有端点扩展

- `GET /api/status` + carbon_rate, carbon_cost_today
- `GET /api/monitoring/kpi` + carbon_intensity, daily_tco2
- `GET /api/reports/daily` + carbon_trading_pnl

## 九、前端设计

### 路由与导航

- 路由：`/carbon`
- 导航栏新增"碳管理"入口（中文标签）
- 页面：`CarbonTrading.tsx`，4个Tab页签

### Tab内容

| Tab | 内容 | 主要组件 |
|-----|------|----------|
| 排放总览 | 实时排放仪表、小时/日/月趋势图、排放源分布 | KpiCard, AreaChart, 因子配置表 |
| 交易市场 | K线图 + 订单簿 + 下单面板 + 当前挂单 | OHLCV Chart, OrderBook, OrderForm, MyOrders |
| 碳资产 | CEA/CCER持仓图、资产流水表、站间调拨 | HoldingsCard, LedgerTable, TransferDialog |
| 履约报告 | 履约进度条、历史履约记录、MRV报告预览 | ProgressBar, ComplianceTable, ReportPreview |

### 技术选型

- 图表：Recharts（已安装）或 lightweight-charts
- 数据刷新：React Query（30s轮询）+ WebSocket（实时推送）
- 样式：Tailwind CSS，暗色主题，与现有 Report.tsx 风格一致

## 十、实现优先级

| 优先级 | 模块 | 预估工作量 | 理由 |
|--------|------|-----------|------|
| P0 | carbon_ledger + 5张表 + Alembic迁移 | 1.5天 | 数据基础，所有功能依赖 |
| P0 | 排放监测（分钟级写入+聚合） | 1天 | 核心数据源 |
| P0 | 配额台账管理 + 站间调拨 | 0.5天 | 资产管理基础 |
| P1 | 交易引擎（订单簿+撮合+做市商+虚拟对手） | 3天 | 核心交易能力 |
| P1 | API端点（5组REST + WS推送） | 1.5天 | 前后端对接 |
| P1 | 碳管理前端页面 | 2天 | 用户可见 |
| P2 | CCER完整生命周期 | 1.5天 | 碳资产多样化 |
| P2 | 履约管理 + MRV报告 | 1天 | 合规闭环 |
| P2 | 与优化引擎/合规审查联动 | 0.5天 | 充分利用已有能力 |

总计约：~12天（P0+P1 约9.5天，P2 约2.5天）
