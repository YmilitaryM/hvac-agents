# Energy Management & Equipment Health Management — Design Spec

**Date:** 2026-05-21
**Status:** Design Complete
**Scope:** Two new MVP modules for the HVAC chiller plant platform

---

## 1. Overview

This spec defines two new production modules for the HVAC multi-agent chiller plant platform:

- **Energy Management (能源管理):** Dedicated application for real-time energy efficiency monitoring, peak-valley load scheduling, demand management, energy reporting, and IPMVP/GB-based measurement & verification.
- **Equipment Health Management (设备健康):** Dedicated application for real-time health scoring, remaining useful life (RUL) estimation, component-level fault diagnosis, FMEA knowledge base, and vibration spectrum analysis.

Both modules have solid algorithmic foundations already in the codebase (COP calculation, degradation tracking, failure prediction, KPI computation). This spec focuses on assembling those parts into product-facing applications with dedicated APIs, databases, and frontend pages.

---

## 2. Deployment Architecture (Hybrid)

```
Data Source Layer (unchanged)
  └── acquisition service — BACnet/Modbus/OPC UA sensor data

Compute & Intelligence Layer (agent service — existing, extended)
  ├── energy/  — COP calc, optimization solver, baseline engine, peak-valley scheduler, M&V verifier
  └── health/  — RUL estimator, FFT analyzer, fault diagnoser, degradation model, FMEA matcher, closed-loop validator

Presentation & Report Layer (new independent services)
  ├── services/energy/  — Energy API, dashboard aggregation, report generation, TimescaleDB
  └── services/health/ — Health API, heatmap, FMEA knowledge base API, PostgreSQL

Frontend Layer (React SPA — existing, extended)
  ├── pages/energy/  — 5 pages
  └── pages/health/  — 5 pages
```

**Key decisions:**

| Decision | Choice |
|----------|--------|
| Energy database | TimescaleDB (time-series dense: 15s granularity power/COP/price data) |
| Health database | PostgreSQL (relation dense: equipment-component-fault-FMEA-maintenance) |
| Inter-service comm | Synchronous HTTP via gateway proxy (matches existing pattern); real-time push via WebSocket EventBus |
| Auth/Audit/Rate-limit | Reuse gateway service (existing JWT + RBAC + audit middleware) |
| Container delta | +2 service containers + 2 database containers (docker-compose: 12 → 16) |

---

## 3. Energy Management Module

### 3.1 Data Models (TimescaleDB, `energy_db`)

| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `EnergySnapshot` | timestamp, plant_id, total_power_kw, cop, cooling_load_rt, equipment_power_breakdown(jsonb), outdoor_wb_temp | 15s granularity energy snapshot, hypertable partitioned |
| `EnergyPrice` | timestamp, price_per_kwh, period(peak/valley/flat), carbon_intensity | TOU price table (cached from env_service) |
| `EnergyBaseline` | plant_id, period_start/end, baseline_kwh_per_rt, method(regression/simple), r_squared, climate_zone, building_type | IPMVP + GB/T 51161 baseline model |
| `DemandEvent` | start_time, end_time, peak_kw, target_kw, strategy(load_shift/shed/storage), actual_reduction_kw | Demand management event log |
| `EnergyReport` | plant_id, period, report_type(daily/weekly/monthly/annual/audit/certificate), summary(jsonb), file_path | Report metadata (PDF/Excel in object storage) |
| `PowerQuality` | timestamp, equipment_id, thd_v_pct, thd_i_pct, power_factor, voltage_unbalance_pct, frequency_hz | Power quality (on-demand, 5min granularity) |

### 3.2 API Endpoints (`services/energy/`)

All endpoints mounted under `/api/energy/` via gateway proxy.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Real-time aggregated energy data (COP/power/load/cost trend) |
| GET | `/breakdown` | Equipment-level energy breakdown (chiller/pump/tower share) |
| GET | `/peak-demand` | Demand trend + forecast + event list |
| POST | `/peak-demand/optimize` | Trigger demand optimization (calls agent solver) |
| GET | `/baseline` | Baseline data and fit parameters |
| POST | `/baseline/calibrate` | Re-fit baseline (select time window and method) |
| GET | `/reports` | Report list (filter by period + type) |
| POST | `/reports/generate` | Generate report (async task, returns task_id) |
| GET | `/mv/verify` | IPMVP + GB/T 28750 M&V results (energy savings, uncertainty) |
| GET | `/power-quality` | Power quality trends (THD, power factor, voltage unbalance) |
| GET | `/comparison` | YoY/MoM comparison data |

### 3.3 Compute Engines (agent service `energy/`)

| Engine | Input | Method | Output |
|--------|-------|--------|--------|
| Peak-Valley Scheduler | Next-day forecast load + TOU price table | Dynamic programming + existing MILP solver | Chiller start/stop plan + storage strategy |
| Baseline Engine | Historical energy + cooling load + outdoor WB temp | Multiple linear regression + climate zone correction | Baseline kWh/RT + confidence interval; dual-standard: IPMVP Option C + GB/T 51161 constraint/leading values |
| Demand Predictor | Current power trend + weather + price period | 15-min sliding window max forecast | Demand warning + suggested load-shedding strategy |
| M&V Verifier | Baseline vs actual energy | Dual-standard: ASHRAE G14 (CV(RMSE) < 20%, NMBE) AND GB/T 28750 (M&V plan) + GB/T 13234 (overall/measure method) | Avoided energy savings + uncertainty + coal-equivalent savings + carbon reduction equivalent |

### 3.4 Standards Compliance

| Standard | Application |
|----------|-------------|
| GB 19577-2024 | Equipment-level COP 1/2/3 efficiency grade lines (mandatory, effective 2025-02-01) |
| GB 50189-2015 | System-level SCOP ≥ 5.0 high-efficiency benchmark |
| GB/T 51161-2016 | Building energy consumption constraint/leading values by building type and climate zone |
| GB/T 13234-2018 | Energy savings calculation — overall method and measure method (equiv. ISO 50047) |
| GB/T 28750-2012 | M&V plan design and uncertainty analysis (under revision) |
| GB/T 2589-2020 | Comprehensive energy calculation, coal-equivalent conversion |
| DB11/T 1617-2025 | Beijing local standard — cooling energy intensity limits by building type |

### 3.5 Frontend Pages

| Route | Title | Content |
|-------|-------|---------|
| `/energy/dashboard` | 能效看板 | Real-time COP/power/load/cost 4-quadrant view + equipment energy share Sankey diagram + 24h trend + anomaly highlighting |
| `/energy/scheduling` | 峰谷负荷调度 | TOU price heatmap + before/after optimization comparison + schedule Gantt chart + expected savings |
| `/energy/demand` | 需量管理 | Real-time demand gauge + forecast curve + event log + historical demand comparison |
| `/energy/reports` | 能源报告 | Daily/weekly/monthly/annual reports + energy audit reports + energy savings certificate + PDF/Excel export |
| `/energy/mv` | M&V验证 | Baseline vs actual comparison + energy savings quantification + uncertainty analysis + carbon reduction equivalent + standards compliance status |

---

## 4. Equipment Health Management Module

### 4.1 Data Models (PostgreSQL, `health_db`)

| Model | Key Fields | Purpose |
|-------|-----------|---------|
| `HealthScore` | equipment_id, timestamp, overall_score(0-100), component_scores(jsonb), trend(direction+slope) | Equipment + component-level health score time series |
| `RULPrediction` | equipment_id, component, predicted_hours, confidence_interval(lo/hi), model_version, degradation_model(linear/exp/weibull) | Remaining useful life estimation |
| `FaultDiagnosis` | equipment_id, timestamp, symptom_signature(jsonb), matched_fmea_id, confidence, root_cause, severity(1-5), cert_level(1-4) | Component-level fault diagnosis (GB/T 23718 cert levels) |
| `FMEARecord` | equipment_type, component, failure_mode, effects, severity, occurrence, detection, rpn, mitigation, symptoms(jsonb) | FMEA knowledge base (editable, searchable) |
| `VibrationSpectrum` | equipment_id, timestamp, sample_rate, fft_bins(jsonb), peak_frequencies(jsonb), bearing_fault_freqs(jsonb), crest_factor, vibration_zone(A/B/C/D) | Vibration spectrum data (on-demand, GB/T 6075 zones) |
| `OilAnalysis` | equipment_id, sample_date, viscosity, tan, moisture_ppm, wear_metals(jsonb), particle_count_iso | Oil analysis (manual lab entry) |
| `ModelValidation` | prediction_id, actual_outcome, accuracy, feedback_source(workorder/inspection), retrained | Closed-loop: prediction vs actual outcome |

### 4.2 API Endpoints (`services/health/`)

All endpoints mounted under `/api/health/` via gateway proxy.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Plant-wide equipment health heatmap + score overview |
| GET | `/equipment/{id}` | Single equipment health detail (score/degradation/RUL/diagnosis history) |
| GET | `/rul` | RUL prediction list (filter by equipment/component) |
| POST | `/rul/compute` | Trigger RUL recalculation (calls agent service) |
| GET | `/diagnosis` | Fault diagnosis history and trends |
| POST | `/diagnosis/run` | Trigger fault diagnosis (symptom signature → agent FMEA matching) |
| GET | `/fmea` | FMEA knowledge base search (full-text + filter) |
| POST | `/fmea` | Create/update FMEA record |
| GET | `/vibration` | Vibration spectrum data + waterfall plot data |
| GET | `/oil` | Oil analysis records and trends |
| GET | `/validation` | Model validation closed-loop data |

### 4.3 Compute Engines (agent service `health/`)

| Engine | Input | Method | Output |
|--------|-------|--------|--------|
| Health Scoring Engine | COP degradation, vibration RMS, approach temp, run hours, days since last maintenance | AHP weight determination + degradation curve fitting | 0-100 overall score + per-component scores + trend direction |
| RUL Estimator | Historical health score sequence + operating conditions | Weibull reliability model + exponential degradation model + 80% confidence interval | Predicted remaining hours + recommended inspection window |
| Fault Diagnoser | Multi-dimensional feature vector (vibration spectrum, temp, pressure, current) | Feature extraction → FMEA cosine similarity matching → Bayesian confidence; GB/T 23718 4-level cert annotation | Top-3 failure modes + confidence + recommended actions |
| FFT Analyzer | Raw accelerometer waveform | FFT → envelope spectrum → harmonic extraction; GB/T 19873 data description; GB/T 6075 zone classification | Labeled spectrum (unbalance 1x, misalignment 2x, bearing BPFI/BPFO/FTF/BSF) |
| Closed-loop Validator | Prediction records + work order outcomes + inspection records | Compare actual failures/repairs against historical RUL/diagnosis predictions; compute accuracy | Auto-trigger model retraining when accuracy drops below threshold |

### 4.4 Standards Compliance

| Standard | Application |
|----------|-------------|
| GB/T 19873.1-2005 | Vibration condition monitoring — general guidelines (measurement methods, sensor selection, data collection) |
| GB/T 19873.2-2009 | Vibration data processing, analysis and description (FFT output format, spectral labeling) |
| GB/T 6075 series | Mechanical vibration evaluation — A/B/C/D zone classification (A=new, B=long-term OK, C=plan repair, D=possible damage) |
| GB/T 23713.1-2009 | Machine condition monitoring and diagnostics — prognostics general guide (RUL output format) |
| GB/T 23718 series | Personnel training and certification — 4-level cert scheme (used to annotate diagnosis confidence levels) |

### 4.5 Frontend Pages

| Route | Title | Content |
|-------|-------|---------|
| `/health/dashboard` | 健康看板 | Plant-wide equipment health heatmap (green/yellow/red) + score distribution + Top N degradation trends + pending alerts |
| `/health/rul` | RUL预测 | Equipment-level RUL gauge + degradation curve + confidence interval + recommended repair window + historical trajectory replay |
| `/health/diagnosis` | 故障诊断 | Multi-dimensional feature input panel + suspected faults Top-3 + confidence + FMEA match details + quick work order creation |
| `/health/fmea` | FMEA知识库 | Equipment type-component-failure mode 3-level structure + full-text search + RPN sort + edit/create + linked diagnosis records |
| `/health/spectrum` | 频谱分析 | Vibration time-domain waveform + FFT spectrum + envelope spectrum + waterfall plot + fault frequency labels (BPFI/BPFO etc.) + GB/T 6075 zone overlay + oil analysis trends |

---

## 5. Navigation Structure

Current 16 flat routes restructured into collapsible groups. Two new top-level groups added:

```
HVAC Platform
├── 📊 仪表盘 (Dashboard)
├── 监控与分析 (Monitoring & Analysis)        [collapsible group]
│   ├── ⚡ 能源管理 ▾                           [new, expanded by default]
│   │   ├── 能效看板    /energy/dashboard
│   │   ├── 峰谷调度    /energy/scheduling
│   │   ├── 需量管理    /energy/demand
│   │   ├── 能源报告    /energy/reports
│   │   └── M&V验证     /energy/mv
│   ├── 💚 设备健康 ▸                           [new, expanded by default]
│   │   ├── 健康看板    /health/dashboard
│   │   ├── RUL预测     /health/rul
│   │   ├── 故障诊断    /health/diagnosis
│   │   ├── FMEA知识库  /health/fmea
│   │   └── 频谱分析    /health/spectrum
│   ├── 🔧 设备管理
│   └── 🚨 告警
├── 运维管理 (Operations)                      [collapsible group]
│   ├── 🧠 策略中心
│   ├── 📋 工单管理
│   ├── 📡 边缘设备
│   └── 🖐️ 手动干预
├── 仿真与分析 (Simulation & Analysis)
│   ├── 🏗️ 3D制冷站
│   ├── 🔬 仿真模拟
│   └── 🌤️ 环境数据
├── 碳交易 (Carbon)
│   └── 💰 碳交易
├── 📊 报告
└── ⚙️ 设置
```

---

## 6. Data Refresh Strategy (Mixed)

| Data Category | Strategy | Frequency |
|---------------|----------|-----------|
| Energy dashboard KPIs (COP/power/load/price) | WebSocket push | 10-15s |
| Health heatmap / status cards | WebSocket push | 15-30s |
| Degradation trends / RUL predicted values | Polling + cache | 2-5 min |
| Alerts / alarm events | WebSocket push | Real-time |
| Reports / historical trends / FMEA library | On-demand | User-triggered |
| Vibration spectrum / power quality | On-demand (expensive) | User-triggered |

---

## 7. Integration Points

| Existing System | Integration |
|-----------------|-------------|
| Gateway (JWT + RBAC) | Both services route through gateway, reuse auth/audit/rate-limit |
| Alert engine | Health degradation → auto-alert; energy anomaly → auto-alert |
| Work order system | Health diagnosis → auto-generate work order; RUL threshold → auto-create |
| Carbon trading | Energy savings → carbon reduction equivalent → CEA quota linkage |
| WebSocket EventBus | Extended event types: `energy_snapshot`, `health_score_update`, `demand_warning`, `rul_change` |
| Predictive maintenance | `degradation_tracker` → feeds into health scoring engine |
| KPI calculator | `compute_cop/eer/carbon_intensity` → reused by energy baseline engine |
| MILP optimizer | Extended with TOU price constraints → peak-valley scheduler |
| Efficiency Advocate | Extended prompts to reference GB standards in strategy review |

---

## 8. Container/Infrastructure Changes

`docker-compose.yml` additions:

```yaml
# New services
energy_service:   port 8008, depends on energy_db, redis, gateway
health_service:   port 8009, depends on health_db, redis, gateway

# New databases
energy_db:        timescaledb:2.16-pg16, port 5436
health_db:        postgres:16, port 5437
```

Total containers: 12 → 16

---

## 9. Out of Scope (Post-MVP)

- Power quality real-time monitoring (sampled data only in MVP)
- Infrared thermography image integration
- Online oil analysis sensor integration (manual entry only)
- Multi-plant aggregation dashboard
- Mobile native app (PWA supported)
- Regulatory filing automation (report templates only)
