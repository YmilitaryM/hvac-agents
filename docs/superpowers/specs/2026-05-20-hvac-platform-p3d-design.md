# P3-D: Multi-Station Aggregation & Operations UI

> **Goal:** Add 3 new frontend pages (Edge Devices, Work Orders, Maintenance) to the existing React dashboard, integrating with P3 backend APIs for edge-cloud ops visibility and control.

> **Architecture:** Extend existing React 19 + TypeScript + Vite frontend. Three new pages under an "Edge Ops" sidebar section, consuming edgemanager (:8006) and agent (:8004) REST APIs through the gateway (:8000). Reuse TanStack Query, Recharts, Tailwind CSS 4, Zustand patterns already established.

> **Tech Stack:** React 19, TypeScript 6, Vite 8, Tailwind CSS 4, TanStack Query 5, Recharts 3, Zustand 5, React Router 7

---

## 1. Navigation & Routing

### Sidebar change

Add a new "Edge Ops" section group in the Layout sidebar, below existing items, with 3 sub-items:

```
── Edge Ops ──
🖥️ Edge Devices    → /edges
🔧 Work Orders     → /workorders
🔮 Maintenance     → /maintenance
```

### Routes added to App.tsx

```tsx
<Route path="/edges" element={<EdgeDevices />} />
<Route path="/workorders" element={<WorkOrders />} />
<Route path="/maintenance" element={<Maintenance />} />
```

---

## 2. Page 1: Edge Devices (`/edges`)

### Purpose
View, register, and manage edge devices deployed across plants.

### API dependencies (edgemanager service, port 8006)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/edges/` | GET | List all edge devices |
| `/api/edges/register` | POST | Register new edge device |
| `/api/edges/{edge_id}` | GET | Get device detail |
| `/api/edges/{edge_id}/status` | GET | Get device online/offline status |
| `/api/edges/{edge_id}/config` | GET/POST | View/set device config |
| `/api/edges/{edge_id}/ota/` | GET/POST | List/create OTA tasks |

### UI components

- **Stats bar** (4 KPI cards): Online, Offline, Warning, Total — auto-refresh every 10s via `useQuery`
- **Toolbar**: Search input (by edge_id/plant_id), Status dropdown filter, "Register New" button
- **Device table**: Columns: Edge ID, Plant, Status (colored badge), Last Heartbeat, Version, Actions (Config / OTA / Delete)
- **Register modal**: Form with edge_id, plant_id, mode fields
- **Status badge**: Green (online, heartbeat < 60s), Yellow (warning, 60-300s), Red (offline, >300s or no heartbeat)
- **Config panel**: Slide-out drawer showing YAML config, editable with save
- **OTA panel**: Modal showing OTA task list, "Create OTA Task" button

### State
- `useQuery` for device list, auto-refetch every 10s
- `useMutation` for register, config update, OTA create, delete
- Local state: search query, status filter, selected device, modal/drawer open state

---

## 3. Page 2: Work Orders (`/workorders`)

### Purpose
View, create, and transition maintenance work orders across all plants. Supports the state machine: open → acknowledged → in_progress → resolved → closed | rejected.

### API dependencies (agent service, port 8004)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workorders/` | GET | List work orders (filters: status, edge_id) |
| `/api/workorders/` | POST | Create work order |
| `/api/workorders/{wo_id}` | GET | Get work order detail |
| `/api/workorders/{wo_id}/transition` | POST | Transition to next state |

### UI components

- **Status bar** (5 count cards): Open, Acknowledged, In Progress, Resolved, Closed/Rejected
- **Filter toolbar**: Status dropdown, Severity dropdown, Equipment search input, "New Order" button
- **Work order table**: Columns: ID, Title, Equipment, Severity (colored badge), Status (state badge), Source (auto/manual), Created, Action buttons
- **Action buttons** — context-sensitive per current state:
  - Open → [Acknowledge] [Reject]
  - Acknowledged → [Start Work] [Reject]
  - In Progress → [Resolve]
  - Resolved → [Close] [Reopen]
  - Closed/Rejected → (no actions)
- **Create modal**: Form with edge_id, equipment_id, severity (critical/warning/info), title, description, source
- **Transition modal**: Confirm transition, optional note field, show valid next states
- **Detail drawer**: Full work order info + transition history log

### State
- `useQuery` for work order list, auto-refetch every 15s
- `useMutation` for create and transition
- Local state: filters, selected WO, modal open states

---

## 4. Page 3: Maintenance (`/maintenance`)

### Purpose
Predictive maintenance dashboard: evaluate equipment degradation, predict failure probability, track equipment health trends.

### API dependencies (agent service, port 8004)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/maintenance/evaluate` | POST | Run degradation evaluation, returns rule_recommendations + schedule |
| `/api/maintenance/predict` | POST | Predict failure probability |

### Backend modules (added post-design, PR #1)

| Module | Purpose |
|--------|---------|
| `rule_advisor.py` | Rule engine: 5 static threshold rules for maintenance action recommendations |
| `maintenance_scheduler.py` | Suggests maintenance time windows by severity |
| `auto_generator.py` | Generates WorkOrder objects from anomaly/detection data |
| `assignment.py` | Maps equipment_type → role for auto-assignment |

### New endpoints (added post-design)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workorders/generate` | POST | Auto-generate work order from anomaly/degradation with auto-assignment |
| `/api/workorders/` POST | - | Now accepts optional `equipment_type` for auto role assignment |

### UI components

- **Health overview** (3 cards): Healthy (green), Degrading (yellow), Critical (red) — counts from recent evaluations
- **Evaluation panel** (left column):
  - Equipment selector dropdown
  - Input fields: Design COP, COP Window (comma-separated values), Approach Temp Avg, Vibration Window
  - "Run Evaluation" button
  - Result card showing: severity badge, COP degradation %, CUSUM triggered status, recommendation text
- **Prediction panel** (right column):
  - Input fields: Current COP, Vibration RMS, Approach Temp
  - "Predict Failure" button
  - Large probability gauge (percentage + color-coded)
- **Recent evaluations table**: Columns: Equipment, Severity, COP Deg %, ΔT Drift, Vib Trend, CUSUM, Timestamp
- **Trend chart** (future enhancement): COP degradation over time line chart (Recharts)

### State
- `useQuery` for recent evaluations (if an endpoint is added)
- `useMutation` for evaluate and predict
- Local state: form inputs, results

---

## 5. API Layer

### New API module files

```
frontend/src/api/edges.ts       — fetchEdges, registerEdge, getEdgeStatus, setEdgeConfig, createOTATask
frontend/src/api/workorders.ts  — fetchWorkOrders, createWorkOrder, transitionWorkOrder
frontend/src/api/maintenance.ts — evaluateDegradation, predictFailure
```

### API client pattern (follow existing `api/monitoring.ts` pattern)

```ts
const BASE = '/api';

export async function fetchEdges(params?: { status?: string; search?: string }) {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  const res = await fetch(`${BASE}/edges/${qs ? '?' + qs : ''}`);
  if (!res.ok) throw new Error('Failed to fetch edges');
  return res.json();
}
```

All API calls go through the gateway (:8000) which proxies to edgemanager (:8006) and agent (:8004).

---

## 6. Files Created/Modified

### New files (8)
| File | Purpose |
|------|---------|
| `frontend/src/pages/EdgeDevices.tsx` | Edge device management page |
| `frontend/src/pages/WorkOrders.tsx` | Work order list + transitions page |
| `frontend/src/pages/Maintenance.tsx` | Predictive maintenance dashboard |
| `frontend/src/api/edges.ts` | Edge device API functions |
| `frontend/src/api/workorders.ts` | Work order API functions |
| `frontend/src/api/maintenance.ts` | Maintenance API functions |
| `frontend/tests/EdgeDevices.test.tsx` | Edge page tests |
| `frontend/tests/WorkOrders.test.tsx` | Work order page tests |
| `frontend/tests/Maintenance.test.tsx` | Maintenance page tests |

### Modified files (2)
| File | Change |
|------|--------|
| `frontend/src/App.tsx` | Add 3 routes |
| `frontend/src/components/Layout.tsx` | Add "Edge Ops" sidebar section |

---

## 7. Testing

- **Component tests** (Vitest + React Testing Library): each page renders stats cards, tables with mock API data
- **API function tests**: mock fetch, verify URL construction and error handling
- **Accessibility**: form labels, button aria-labels, table headers
- **Existing regression**: all 11 existing pages continue to render without errors

---

## 8. Known Limitations & Pending Work

### 8.1 工单人员分配 (Work Order Assignment)
**当前状态：** `assignment.py` 使用硬编码的设备类型→角色映射表，不是真实人员。
- chiller / cooling_tower → `hvac-technician`
- pump / valve → `mechanic`
- sensor → `instrumentation-tech`
- 严重级别加 `-lead` 后缀

**待实现：**
- 技术人员表 (id, name, role, skills, shift, available)
- 按设备类型+技能匹配找到可用技术人员
- 排班和负载均衡
- 对接 auth 模块的用户系统

### 8.2 维护规则引擎 (Rule Advisor)
**当前状态：** `rule_advisor.py` 内置 5 条静态阈值规则，规则硬编码不可配置。
**待实现：** 规则应支持通过 API 动态管理（CRUD），或至少从配置文件加载。

### 8.3 维护调度窗口 (Maintenance Scheduler)
**当前状态：** `maintenance_scheduler.py` 按严重程度给固定时间窗口（严重:4h/2d, 退化:3d/14d, 其他:7d/30d）。
**待实现：** 结合日历、人员空闲时间、备件库存等实际约束。

### 8.4 工单自动生成 (Auto Generator)
**当前状态：** `auto_generator.py` 通过 `/api/workorders/generate` 端点手动调用。
**待实现：** 应作为维护评估的自动后续动作 — 当 degradation 达到 critical 时自动创建工单。

---

## 9. Self-Check

- [ ] No TBD/TODO placeholders
- [ ] All API endpoints match existing backend routes
- [ ] State machine transitions match lifecycle.py VALID_TRANSITIONS
- [ ] Color/status conventions consistent with existing Dashboard
- [ ] Tech stack fully compatible with existing package.json
- [ ] All new files and modified files listed
