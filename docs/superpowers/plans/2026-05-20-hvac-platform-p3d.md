# P3-D: Multi-Station Aggregation & Operations UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3 new frontend pages (Edge Devices, Work Orders, Maintenance) with API modules, routing, and sidebar navigation to the existing React dashboard.

**Architecture:** Extend existing React 19 + TypeScript + Vite frontend. Three new pages under an "Edge Ops" sidebar section group, consuming edgemanager (:8006) and agent (:8004) REST APIs through the gateway (:8000). Reuse KpiCard, TanStack Query, Tailwind CSS 4 dark-theme patterns from existing pages.

**Tech Stack:** React 19, TypeScript 6, Vite 8, Tailwind CSS 4, TanStack Query 5, Recharts 3, React Router 7, Vitest + @testing-library/react

---

### Task 1: Create edges API module

**Files:**
- Create: `frontend/src/api/edges.ts`

- [ ] **Step 1: Write the API functions**

```typescript
const BASE = '/api/edges';

export interface EdgeDevice {
  edge_id: string;
  plant_id: string;
  mode: string;
  status: string;
  last_heartbeat: string | null;
  version: string;
  registered_at: string;
}

export async function fetchEdges(params?: { status?: string; search?: string }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.search) qs.set('search', params.search);
  const r = await fetch(`${BASE}/${qs.toString() ? '?' + qs.toString() : ''}`);
  if (!r.ok) throw new Error('Failed to fetch edges');
  return r.json();
}

export async function registerEdge(body: { edge_id: string; plant_id: string; mode: string }) {
  const r = await fetch(`${BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to register edge');
  return r.json();
}

export async function fetchEdgeStatus(edgeId: string) {
  const r = await fetch(`${BASE}/${edgeId}/status`);
  if (!r.ok) throw new Error('Failed to fetch edge status');
  return r.json();
}

export async function fetchEdgeConfig(edgeId: string) {
  const r = await fetch(`${BASE}/${edgeId}/config`);
  if (!r.ok) throw new Error('Failed to fetch edge config');
  return r.json();
}

export async function setEdgeConfig(edgeId: string, config: Record<string, unknown>) {
  const r = await fetch(`${BASE}/${edgeId}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!r.ok) throw new Error('Failed to set edge config');
  return r.json();
}

export async function fetchOTATasks(edgeId: string) {
  const r = await fetch(`${BASE}/${edgeId}/ota/`);
  if (!r.ok) throw new Error('Failed to fetch OTA tasks');
  return r.json();
}

export async function createOTATask(edgeId: string, body: { version: string; url?: string }) {
  const r = await fetch(`${BASE}/${edgeId}/ota/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to create OTA task');
  return r.json();
}

export async function deleteEdge(edgeId: string) {
  const r = await fetch(`${BASE}/${edgeId}`, { method: 'DELETE' });
  if (!r.ok) throw new Error('Failed to delete edge');
  return r.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/edges.ts
git commit -m "feat(p3d): add edges API module"
```

---

### Task 2: Create workorders API module

**Files:**
- Create: `frontend/src/api/workorders.ts`

- [ ] **Step 1: Write the API functions**

```typescript
const BASE = '/api/workorders';

export interface WorkOrder {
  id: string;
  edge_id: string;
  equipment_id: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  status: 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'closed' | 'rejected';
  assigned_to: string | null;
  source: 'auto' | 'manual';
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export async function fetchWorkOrders(params?: { status?: string; severity?: string; edge_id?: string; search?: string }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.severity) qs.set('severity', params.severity);
  if (params?.edge_id) qs.set('edge_id', params.edge_id);
  if (params?.search) qs.set('search', params.search);
  const r = await fetch(`${BASE}/${qs.toString() ? '?' + qs.toString() : ''}`);
  if (!r.ok) throw new Error('Failed to fetch work orders');
  return r.json();
}

export async function createWorkOrder(body: {
  edge_id: string;
  equipment_id: string;
  severity: string;
  title: string;
  description: string;
  source?: string;
}) {
  const r = await fetch(`${BASE}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to create work order');
  return r.json();
}

export async function fetchWorkOrderDetail(woId: string) {
  const r = await fetch(`${BASE}/${woId}`);
  if (!r.ok) throw new Error('Failed to fetch work order');
  return r.json();
}

export async function transitionWorkOrder(woId: string, toStatus: string, note?: string) {
  const r = await fetch(`${BASE}/${woId}/transition`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ to_status: toStatus, note }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || 'Transition failed');
  }
  return r.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/workorders.ts
git commit -m "feat(p3d): add workorders API module"
```

---

### Task 3: Create maintenance API module

**Files:**
- Create: `frontend/src/api/maintenance.ts`

- [ ] **Step 1: Write the API functions**

```typescript
const BASE = '/api/maintenance';

export interface DegradationRequest {
  equipment_id: string;
  design_cop: number;
  cop_window: number[];
  approach_temp_avg: number;
  vibration_window: number[];
}

export interface DegradationResult {
  severity: 'healthy' | 'degrading' | 'critical';
  cop_degradation_pct: number;
  cusum_triggered: boolean;
  recommended_action: string;
}

export interface PredictRequest {
  current_cop: number;
  vibration_rms: number;
  approach_temp: number;
}

export interface PredictResult {
  failure_probability: number;
}

export async function evaluateDegradation(body: DegradationRequest): Promise<DegradationResult> {
  const r = await fetch(`${BASE}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to evaluate degradation');
  return r.json();
}

export async function predictFailure(body: PredictRequest): Promise<PredictResult> {
  const r = await fetch(`${BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to predict failure');
  return r.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/maintenance.ts
git commit -m "feat(p3d): add maintenance API module"
```

---

### Task 4: Add Edge Ops section to Layout sidebar

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Add Edge Ops section group to NAV**

Replace the NAV array in `Layout.tsx` with one that includes the Edge Ops section:

```typescript
const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/equipment', label: '设备管理' },
  { to: '/plant', label: '制冷站' },
  { to: '/environment', label: '环境配置' },
  { to: '/simulation', label: '仿真控制' },
  { to: '/strategies', label: '策略中心' },
  { to: '/reports', label: '报告' },
  { to: '/alerts', label: '告警' },
  { to: '/override', label: '手动干预' },
  { to: '/settings', label: '系统设置' },
  // P3-D Edge Ops section
  { section: '── Edge Ops ──' },
  { to: '/edges', label: '🖥️ Edge Devices' },
  { to: '/workorders', label: '🔧 Work Orders' },
  { to: '/maintenance', label: '🔮 Maintenance' },
];
```

Then update the JSX nav rendering to handle section headers. Replace the existing `<nav>` block with:

```tsx
<nav className="flex-1 space-y-1">
  {NAV.map(n => {
    if ('section' in n) {
      return (
        <div key={n.section} className="px-3 py-2 text-xs text-slate-500 font-semibold tracking-wide uppercase mt-4 first:mt-0">
          {n.section}
        </div>
      );
    }
    return (
      <NavLink key={n.to} to={n.to} end={n.to === '/'}
        className={({isActive}) => `block px-3 py-2 rounded text-sm ${isActive ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}>
        {n.label}
      </NavLink>
    );
  })}
</nav>
```

- [ ] **Step 2: Verify the file renders without TypeScript errors**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors related to Layout.tsx

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat(p3d): add Edge Ops section group to sidebar navigation"
```

---

### Task 5: Create EdgeDevices page + add route

**Files:**
- Create: `frontend/src/pages/EdgeDevices.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write the EdgeDevices page component**

```typescript
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import KpiCard from '../components/KpiCard';
import { fetchEdges, registerEdge, fetchEdgeConfig, setEdgeConfig, fetchOTATasks, createOTATask, deleteEdge, type EdgeDevice } from '../api/edges';

function statusColor(s: string) {
  if (s === 'online') return 'bg-green-500';
  if (s === 'warning') return 'bg-yellow-500';
  return 'bg-red-500';
}

function statusLabel(s: string) {
  if (s === 'online') return 'Online';
  if (s === 'warning') return 'Warning';
  return 'Offline';
}

export default function EdgeDevices() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showRegister, setShowRegister] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<EdgeDevice | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [showOTA, setShowOTA] = useState(false);

  // Register form state
  const [regEdgeId, setRegEdgeId] = useState('');
  const [regPlantId, setRegPlantId] = useState('');
  const [regMode, setRegMode] = useState('acquisition');

  // Config form state
  const [configYaml, setConfigYaml] = useState('');

  // OTA form state
  const [otaVersion, setOtaVersion] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['edges', { status: statusFilter, search }],
    queryFn: () => fetchEdges({ status: statusFilter || undefined, search: search || undefined }),
    refetchInterval: 10000,
  });

  const edges: EdgeDevice[] = data?.edges || [];
  const online = edges.filter(e => e.status === 'online').length;
  const offline = edges.filter(e => e.status === 'offline').length;
  const warning = edges.filter(e => e.status === 'warning').length;

  const registerMut = useMutation({
    mutationFn: registerEdge,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      setShowRegister(false);
      setRegEdgeId(''); setRegPlantId(''); setRegMode('acquisition');
    },
  });

  const configMut = useMutation({
    mutationFn: ({ edgeId, config }: { edgeId: string; config: Record<string, unknown> }) =>
      setEdgeConfig(edgeId, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edges'] });
      setShowConfig(false);
    },
  });

  const otaMut = useMutation({
    mutationFn: ({ edgeId, version }: { edgeId: string; version: string }) =>
      createOTATask(edgeId, { version }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edges'] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteEdge,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['edges'] }),
  });

  const openConfig = async (edge: EdgeDevice) => {
    setSelectedEdge(edge);
    try {
      const cfg = await fetchEdgeConfig(edge.edge_id);
      setConfigYaml(typeof cfg === 'string' ? cfg : JSON.stringify(cfg, null, 2));
    } catch {
      setConfigYaml('# Failed to load config');
    }
    setShowConfig(true);
  };

  const openOTA = async (edge: EdgeDevice) => {
    setSelectedEdge(edge);
    setShowOTA(true);
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Edge Devices</h2>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard label="Online" value={String(online)} color="text-green-400" />
        <KpiCard label="Offline" value={String(offline)} color="text-red-400" />
        <KpiCard label="Warning" value={String(warning)} color="text-yellow-400" />
        <KpiCard label="Total" value={String(edges.length)} />
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by Edge ID or Plant ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-400 flex-1 min-w-[200px]"
        />
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200"
        >
          <option value="">All Status</option>
          <option value="online">Online</option>
          <option value="warning">Warning</option>
          <option value="offline">Offline</option>
        </select>
        <button
          onClick={() => setShowRegister(true)}
          className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium"
        >
          Register New
        </button>
      </div>

      {/* Device table */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-left">
              <th className="px-4 py-3">Edge ID</th>
              <th className="px-4 py-3">Plant</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last Heartbeat</th>
              <th className="px-4 py-3">Version</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">Loading...</td></tr>
            ) : edges.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">No devices found</td></tr>
            ) : (
              edges.map(e => (
                <tr key={e.edge_id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="px-4 py-3 font-mono text-xs">{e.edge_id}</td>
                  <td className="px-4 py-3">{e.plant_id}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(e.status)} text-white`}>
                      {statusLabel(e.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {e.last_heartbeat ? new Date(e.last_heartbeat).toLocaleString() : '--'}
                  </td>
                  <td className="px-4 py-3 text-xs">{e.version}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <button onClick={() => openConfig(e)} className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">Config</button>
                      <button onClick={() => openOTA(e)} className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">OTA</button>
                      <button onClick={() => { if (confirm('Delete this device?')) deleteMut.mutate(e.edge_id); }} className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 text-red-300 rounded">Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Register Modal */}
      {showRegister && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">Register New Edge Device</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Edge ID</label>
                <input value={regEdgeId} onChange={e => setRegEdgeId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Plant ID</label>
                <input value={regPlantId} onChange={e => setRegPlantId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Mode</label>
                <select value={regMode} onChange={e => setRegMode(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
                  <option value="acquisition">Acquisition</option>
                  <option value="control">Control</option>
                  <option value="inspection">Inspection</option>
                  <option value="full">Full</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowRegister(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
              <button
                onClick={() => registerMut.mutate({ edge_id: regEdgeId, plant_id: regPlantId, mode: regMode })}
                disabled={registerMut.isPending || !regEdgeId || !regPlantId}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {registerMut.isPending ? 'Registering...' : 'Register'}
              </button>
            </div>
            {registerMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(registerMut.error as Error).message}</p>
            )}
          </div>
        </div>
      )}

      {/* Config Drawer */}
      {showConfig && selectedEdge && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-lg">
            <h3 className="text-lg font-bold mb-2">Config: {selectedEdge.edge_id}</h3>
            <textarea
              value={configYaml}
              onChange={e => setConfigYaml(e.target.value)}
              rows={12}
              className="w-full bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 font-mono"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowConfig(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Close</button>
              <button
                onClick={() => {
                  try {
                    const parsed = JSON.parse(configYaml);
                    configMut.mutate({ edgeId: selectedEdge.edge_id, config: parsed });
                  } catch {
                    alert('Invalid JSON');
                  }
                }}
                disabled={configMut.isPending}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {configMut.isPending ? 'Saving...' : 'Save'}
              </button>
            </div>
            {configMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(configMut.error as Error).message}</p>
            )}
          </div>
        </div>
      )}

      {/* OTA Modal */}
      {showOTA && selectedEdge && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">OTA Update: {selectedEdge.edge_id}</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Target Version</label>
                <input value={otaVersion} onChange={e => setOtaVersion(e.target.value)} placeholder="e.g. 1.2.0" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowOTA(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
              <button
                onClick={() => otaMut.mutate({ edgeId: selectedEdge.edge_id, version: otaVersion })}
                disabled={otaMut.isPending || !otaVersion}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {otaMut.isPending ? 'Creating...' : 'Create OTA Task'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add route in App.tsx**

Add import:
```typescript
import EdgeDevices from './pages/EdgeDevices';
```

Add route inside the Layout Route element (after existing routes):
```typescript
<Route path="/edges" element={<EdgeDevices />} />
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/EdgeDevices.tsx frontend/src/App.tsx
git commit -m "feat(p3d): add EdgeDevices page with stats, table, register/config/OTA modals"
```

---

### Task 6: Create WorkOrders page + add route

**Files:**
- Create: `frontend/src/pages/WorkOrders.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write the WorkOrders page component**

```typescript
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import KpiCard from '../components/KpiCard';
import { fetchWorkOrders, createWorkOrder, transitionWorkOrder, type WorkOrder } from '../api/workorders';

const VALID_TRANSITIONS: Record<string, string[]> = {
  open: ['acknowledged', 'rejected'],
  acknowledged: ['in_progress', 'rejected'],
  in_progress: ['resolved'],
  resolved: ['closed', 'in_progress'],
  closed: [],
  rejected: [],
};

function statusBadge(s: string) {
  const colors: Record<string, string> = {
    open: 'bg-blue-600',
    acknowledged: 'bg-purple-600',
    in_progress: 'bg-yellow-500 text-black',
    resolved: 'bg-green-600',
    closed: 'bg-slate-600',
    rejected: 'bg-red-600',
  };
  return `px-2 py-0.5 rounded-full text-xs font-medium text-white ${colors[s] || 'bg-slate-600'}`;
}

function severityBadge(s: string) {
  const colors: Record<string, string> = {
    critical: 'bg-red-600',
    warning: 'bg-yellow-500 text-black',
    info: 'bg-blue-600',
  };
  return `px-2 py-0.5 rounded text-xs font-medium text-white ${colors[s] || 'bg-slate-600'}`;
}

export default function WorkOrders() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showTransition, setShowTransition] = useState<WorkOrder | null>(null);
  const [transitionNote, setTransitionNote] = useState('');
  const [selectedDetail, setSelectedDetail] = useState<WorkOrder | null>(null);

  // Create form state
  const [woEdgeId, setWoEdgeId] = useState('');
  const [woEquipId, setWoEquipId] = useState('');
  const [woSeverity, setWoSeverity] = useState('warning');
  const [woTitle, setWoTitle] = useState('');
  const [woDesc, setWoDesc] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['workorders', { status: statusFilter, severity: severityFilter, search }],
    queryFn: () => fetchWorkOrders({
      status: statusFilter || undefined,
      severity: severityFilter || undefined,
      search: search || undefined,
    }),
    refetchInterval: 15000,
  });

  const orders: WorkOrder[] = data?.work_orders || [];

  const counts = {
    open: orders.filter(o => o.status === 'open').length,
    acknowledged: orders.filter(o => o.status === 'acknowledged').length,
    in_progress: orders.filter(o => o.status === 'in_progress').length,
    resolved: orders.filter(o => o.status === 'resolved').length,
    closed_rejected: orders.filter(o => o.status === 'closed' || o.status === 'rejected').length,
  };

  const createMut = useMutation({
    mutationFn: createWorkOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workorders'] });
      setShowCreate(false);
      setWoEdgeId(''); setWoEquipId(''); setWoSeverity('warning'); setWoTitle(''); setWoDesc('');
    },
  });

  const transitionMut = useMutation({
    mutationFn: ({ woId, toStatus, note }: { woId: string; toStatus: string; note?: string }) =>
      transitionWorkOrder(woId, toStatus, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workorders'] });
      setShowTransition(null);
      setTransitionNote('');
    },
  });

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Work Orders</h2>

      {/* Status bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <KpiCard label="Open" value={String(counts.open)} color="text-blue-400" />
        <KpiCard label="Acknowledged" value={String(counts.acknowledged)} color="text-purple-400" />
        <KpiCard label="In Progress" value={String(counts.in_progress)} color="text-yellow-400" />
        <KpiCard label="Resolved" value={String(counts.resolved)} color="text-green-400" />
        <KpiCard label="Closed/Rejected" value={String(counts.closed_rejected)} color="text-slate-400" />
      </div>

      {/* Filter toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="Search by title or equipment..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-400 flex-1 min-w-[200px]"
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
          <option value="rejected">Rejected</option>
        </select>
        <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
          <option value="">All Severity</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
        <button onClick={() => setShowCreate(true)} className="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium">
          New Order
        </button>
      </div>

      {/* Work order table */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-left">
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Equipment</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">Loading...</td></tr>
            ) : orders.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">No work orders found</td></tr>
            ) : (
              orders.map(wo => {
                const nextStates = VALID_TRANSITIONS[wo.status] || [];
                return (
                  <tr key={wo.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="px-4 py-3 font-mono text-xs">{wo.id?.slice(0, 8)}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => setSelectedDetail(wo)} className="text-cyan-400 hover:underline text-left">
                        {wo.title}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs">{wo.equipment_id}</td>
                    <td className="px-4 py-3"><span className={severityBadge(wo.severity)}>{wo.severity}</span></td>
                    <td className="px-4 py-3"><span className={statusBadge(wo.status)}>{wo.status}</span></td>
                    <td className="px-4 py-3 text-xs"><span className={`px-1.5 py-0.5 rounded text-xs ${wo.source === 'auto' ? 'bg-purple-900 text-purple-300' : 'bg-slate-700 text-slate-300'}`}>{wo.source}</span></td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{new Date(wo.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 flex-wrap">
                        {nextStates.map(ns => (
                          <button
                            key={ns}
                            onClick={() => { setShowTransition(wo); setTransitionNote(''); }}
                            className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded"
                          >
                            {ns === 'acknowledged' ? 'Acknowledge' :
                             ns === 'in_progress' ? 'Start Work' :
                             ns === 'resolved' ? 'Resolve' :
                             ns === 'closed' ? 'Close' :
                             ns === 'rejected' ? 'Reject' : ns}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-md">
            <h3 className="text-lg font-bold mb-4">Create Work Order</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Edge ID</label>
                <input value={woEdgeId} onChange={e => setWoEdgeId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Equipment ID</label>
                <input value={woEquipId} onChange={e => setWoEquipId(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Severity</label>
                <select value={woSeverity} onChange={e => setWoSeverity(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200">
                  <option value="critical">Critical</option>
                  <option value="warning">Warning</option>
                  <option value="info">Info</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Title</label>
                <input value={woTitle} onChange={e => setWoTitle(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Description</label>
                <textarea value={woDesc} onChange={e => setWoDesc(e.target.value)} rows={3} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
              <button
                onClick={() => createMut.mutate({ edge_id: woEdgeId, equipment_id: woEquipId, severity: woSeverity, title: woTitle, description: woDesc })}
                disabled={createMut.isPending || !woEdgeId || !woEquipId || !woTitle}
                className="px-4 py-2 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
              >
                {createMut.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
            {createMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(createMut.error as Error).message}</p>
            )}
          </div>
        </div>
      )}

      {/* Transition Modal */}
      {showTransition && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-sm">
            <h3 className="text-lg font-bold mb-2">Transition Work Order</h3>
            <p className="text-sm text-slate-400 mb-3">{showTransition.title} — Current: <span className={statusBadge(showTransition.status)}>{showTransition.status}</span></p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Available transitions:</label>
                <div className="flex gap-2 flex-wrap">
                  {(VALID_TRANSITIONS[showTransition.status] || []).map(ns => (
                    <button
                      key={ns}
                      onClick={() => transitionMut.mutate({ woId: showTransition.id, toStatus: ns, note: transitionNote || undefined })}
                      disabled={transitionMut.isPending}
                      className="px-3 py-1.5 text-sm bg-cyan-600 hover:bg-cyan-700 text-white rounded disabled:opacity-50"
                    >
                      → {ns}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Note (optional)</label>
                <input value={transitionNote} onChange={e => setTransitionNote(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setShowTransition(null)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Cancel</button>
            </div>
            {transitionMut.isError && (
              <p className="text-red-400 text-xs mt-2">{(transitionMut.error as Error).message}</p>
            )}
          </div>
        </div>
      )}

      {/* Detail Drawer */}
      {selectedDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 w-full max-w-lg max-h-[80vh] overflow-auto">
            <h3 className="text-lg font-bold mb-4">Work Order Detail</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-400">ID</dt><dd className="font-mono">{selectedDetail.id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Title</dt><dd>{selectedDetail.title}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Equipment</dt><dd>{selectedDetail.equipment_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Edge</dt><dd>{selectedDetail.edge_id}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Severity</dt><dd><span className={severityBadge(selectedDetail.severity)}>{selectedDetail.severity}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Status</dt><dd><span className={statusBadge(selectedDetail.status)}>{selectedDetail.status}</span></dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Source</dt><dd>{selectedDetail.source}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Assigned To</dt><dd>{selectedDetail.assigned_to || '--'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Created</dt><dd>{new Date(selectedDetail.created_at).toLocaleString()}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-400">Updated</dt><dd>{new Date(selectedDetail.updated_at).toLocaleString()}</dd></div>
              {selectedDetail.resolved_at && <div className="flex justify-between"><dt className="text-slate-400">Resolved</dt><dd>{new Date(selectedDetail.resolved_at).toLocaleString()}</dd></div>}
            </dl>
            {selectedDetail.description && (
              <div className="mt-4">
                <h4 className="text-xs text-slate-400 mb-1">Description</h4>
                <p className="text-sm text-slate-300 bg-slate-700/50 rounded p-3">{selectedDetail.description}</p>
              </div>
            )}
            <div className="flex justify-end mt-6">
              <button onClick={() => setSelectedDetail(null)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add route in App.tsx**

Add import:
```typescript
import WorkOrders from './pages/WorkOrders';
```

Add route:
```typescript
<Route path="/workorders" element={<WorkOrders />} />
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/WorkOrders.tsx frontend/src/App.tsx
git commit -m "feat(p3d): add WorkOrders page with state machine transitions"
```

---

### Task 7: Create Maintenance page + add route

**Files:**
- Create: `frontend/src/pages/Maintenance.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write the Maintenance page component**

```typescript
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import KpiCard from '../components/KpiCard';
import { evaluateDegradation, predictFailure, type DegradationResult, type PredictResult } from '../api/maintenance';

export default function Maintenance() {
  // Evaluation form
  const [equipmentId, setEquipmentId] = useState('');
  const [designCop, setDesignCop] = useState('5.5');
  const [copWindow, setCopWindow] = useState('5.2,5.1,5.0,4.9,4.8');
  const [approachTempAvg, setApproachTempAvg] = useState('2.5');
  const [vibrationWindow, setVibrationWindow] = useState('1.2,1.3,1.5,1.8,2.1');
  const [evalResult, setEvalResult] = useState<DegradationResult | null>(null);

  // Prediction form
  const [predCop, setPredCop] = useState('4.5');
  const [predVib, setPredVib] = useState('2.5');
  const [predApproach, setPredApproach] = useState('3.2');
  const [predResult, setPredResult] = useState<PredictResult | null>(null);

  const evalMut = useMutation({
    mutationFn: evaluateDegradation,
    onSuccess: (data) => setEvalResult(data),
  });

  const predMut = useMutation({
    mutationFn: predictFailure,
    onSuccess: (data) => setPredResult(data),
  });

  const severityColor = (s: string) => {
    if (s === 'healthy') return 'bg-green-500';
    if (s === 'degrading') return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const probGaugeColor = (p: number) => {
    if (p < 0.3) return 'text-green-400';
    if (p < 0.7) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Predictive Maintenance</h2>

      {/* Health overview */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <KpiCard label="Healthy" value="--" color="text-green-400" />
        <KpiCard label="Degrading" value="--" color="text-yellow-400" />
        <KpiCard label="Critical" value="--" color="text-red-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evaluation panel */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="text-sm text-slate-400 uppercase mb-4">Degradation Evaluation</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Equipment ID</label>
              <input value={equipmentId} onChange={e => setEquipmentId(e.target.value)} placeholder="e.g. chiller-1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Design COP</label>
              <input value={designCop} onChange={e => setDesignCop(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">COP Window (comma-separated)</label>
              <input value={copWindow} onChange={e => setCopWindow(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Approach Temp Avg (°C)</label>
              <input value={approachTempAvg} onChange={e => setApproachTempAvg(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Vibration Window (comma-separated)</label>
              <input value={vibrationWindow} onChange={e => setVibrationWindow(e.target.value)} className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <button
              onClick={() => evalMut.mutate({
                equipment_id: equipmentId || 'chiller-1',
                design_cop: parseFloat(designCop) || 5.5,
                cop_window: copWindow.split(',').map(Number),
                approach_temp_avg: parseFloat(approachTempAvg) || 2.5,
                vibration_window: vibrationWindow.split(',').map(Number),
              })}
              disabled={evalMut.isPending}
              className="w-full bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
            >
              {evalMut.isPending ? 'Evaluating...' : 'Run Evaluation'}
            </button>
          </div>

          {evalMut.isError && (
            <p className="text-red-400 text-xs mt-3">{(evalMut.error as Error).message}</p>
          )}

          {evalResult && (
            <div className="mt-4 bg-slate-700/50 rounded p-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${severityColor(evalResult.severity)}`} />
                <span className="font-semibold capitalize">{evalResult.severity}</span>
              </div>
              <div className="text-sm text-slate-300 grid grid-cols-2 gap-2">
                <div>COP Degradation: <span className="text-white">{evalResult.cop_degradation_pct.toFixed(1)}%</span></div>
                <div>CUSUM Triggered: <span className={evalResult.cusum_triggered ? 'text-red-400' : 'text-green-400'}>{evalResult.cusum_triggered ? 'Yes' : 'No'}</span></div>
              </div>
              {evalResult.recommended_action && (
                <div className="text-sm bg-slate-800 rounded p-2 text-slate-300">{evalResult.recommended_action}</div>
              )}
            </div>
          )}
        </div>

        {/* Prediction panel */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
          <h3 className="text-sm text-slate-400 uppercase mb-4">Failure Prediction</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Current COP</label>
              <input value={predCop} onChange={e => setPredCop(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Vibration RMS</label>
              <input value={predVib} onChange={e => setPredVib(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Approach Temp (°C)</label>
              <input value={predApproach} onChange={e => setPredApproach(e.target.value)} type="number" step="0.1" className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-2 text-sm text-slate-200" />
            </div>
            <button
              onClick={() => predMut.mutate({
                current_cop: parseFloat(predCop) || 4.5,
                vibration_rms: parseFloat(predVib) || 2.5,
                approach_temp: parseFloat(predApproach) || 3.2,
              })}
              disabled={predMut.isPending}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
            >
              {predMut.isPending ? 'Predicting...' : 'Predict Failure'}
            </button>
          </div>

          {predMut.isError && (
            <p className="text-red-400 text-xs mt-3">{(predMut.error as Error).message}</p>
          )}

          {predResult && (
            <div className="mt-4 bg-slate-700/50 rounded p-4 flex flex-col items-center">
              <div className="text-xs text-slate-400 mb-2">Failure Probability</div>
              <div className={`text-5xl font-bold ${probGaugeColor(predResult.failure_probability)}`}>
                {(predResult.failure_probability * 100).toFixed(1)}%
              </div>
              <div className="w-full bg-slate-800 rounded-full h-3 mt-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${predResult.failure_probability < 0.3 ? 'bg-green-500' : predResult.failure_probability < 0.7 ? 'bg-yellow-500' : 'bg-red-500'}`}
                  style={{ width: `${predResult.failure_probability * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add route in App.tsx**

Add import:
```typescript
import Maintenance from './pages/Maintenance';
```

Add route:
```typescript
<Route path="/maintenance" element={<Maintenance />} />
```

- [ ] **Step 3: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Maintenance.tsx frontend/src/App.tsx
git commit -m "feat(p3d): add Maintenance page with degradation evaluation and failure prediction"
```

---

### Task 8: Install test dependencies, setup, and write tests

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Modify: `frontend/src/setupTests.ts` (if exists) or create `frontend/src/test-setup.ts`
- Create: `frontend/tests/EdgeDevices.test.tsx`
- Create: `frontend/tests/WorkOrders.test.tsx`
- Create: `frontend/tests/Maintenance.test.tsx`

- [ ] **Step 1: Install test dependencies**

```bash
cd frontend && npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```
Expected: Packages install successfully

- [ ] **Step 2: Create vitest config**

Create `frontend/vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    globals: true,
  },
});
```

- [ ] **Step 3: Create test setup file**

Create `frontend/src/test-setup.ts`:
```typescript
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 4: Add test script to package.json**

In `package.json`, add to `"scripts"`:
```json
"test": "vitest run"
```

- [ ] **Step 5: Write EdgeDevices test**

Create `frontend/tests/EdgeDevices.test.tsx`:
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import EdgeDevices from '../src/pages/EdgeDevices';

const mockEdges = {
  edges: [
    { edge_id: 'edge-01', plant_id: 'plant-a', mode: 'full', status: 'online', last_heartbeat: new Date().toISOString(), version: '1.0.0', registered_at: '2026-01-01T00:00:00Z' },
    { edge_id: 'edge-02', plant_id: 'plant-b', mode: 'acquisition', status: 'offline', last_heartbeat: null, version: '0.9.0', registered_at: '2026-01-02T00:00:00Z' },
    { edge_id: 'edge-03', plant_id: 'plant-a', mode: 'control', status: 'warning', last_heartbeat: new Date(Date.now() - 120000).toISOString(), version: '1.1.0', registered_at: '2026-01-03T00:00:00Z' },
  ],
};

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EdgeDevices />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('EdgeDevices page', () => {
  it('renders the page title', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEdges),
    } as Response);
    renderPage();
    expect(screen.getByText('Edge Devices')).toBeDefined();
  });

  it('renders stats cards with counts', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEdges),
    } as Response);
    renderPage();
    expect(await screen.findByText('1')).toBeDefined(); // online count
    expect(screen.getByText('Total')).toBeDefined();
  });

  it('renders device table with edge IDs', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEdges),
    } as Response);
    renderPage();
    expect(await screen.findByText('edge-01')).toBeDefined();
    expect(screen.getByText('edge-02')).toBeDefined();
    expect(screen.getByText('edge-03')).toBeDefined();
  });
});
```

- [ ] **Step 6: Write WorkOrders test**

Create `frontend/tests/WorkOrders.test.tsx`:
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import WorkOrders from '../src/pages/WorkOrders';

const mockOrders = {
  work_orders: [
    { id: 'wo-001', edge_id: 'edge-01', equipment_id: 'chiller-1', severity: 'critical', title: 'Compressor failure', description: 'Noise detected', status: 'open', assigned_to: null, source: 'auto', created_at: '2026-05-20T08:00:00Z', updated_at: '2026-05-20T08:00:00Z', resolved_at: null },
    { id: 'wo-002', edge_id: 'edge-02', equipment_id: 'pump-3', severity: 'warning', title: 'Bearing wear', description: 'Vibration high', status: 'acknowledged', assigned_to: 'tech-1', source: 'manual', created_at: '2026-05-20T07:00:00Z', updated_at: '2026-05-20T09:00:00Z', resolved_at: null },
    { id: 'wo-003', edge_id: 'edge-01', equipment_id: 'tower-2', severity: 'info', title: 'Routine check', description: '', status: 'resolved', assigned_to: null, source: 'auto', created_at: '2026-05-19T12:00:00Z', updated_at: '2026-05-20T10:00:00Z', resolved_at: '2026-05-20T10:00:00Z' },
  ],
};

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <WorkOrders />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('WorkOrders page', () => {
  it('renders the page title', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    } as Response);
    renderPage();
    expect(screen.getByText('Work Orders')).toBeDefined();
  });

  it('renders status count cards', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    } as Response);
    renderPage();
    expect(await screen.findByText('Open')).toBeDefined();
    expect(screen.getByText('Acknowledged')).toBeDefined();
    expect(screen.getByText('Resolved')).toBeDefined();
  });

  it('renders work order titles in table', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    } as Response);
    renderPage();
    expect(await screen.findByText('Compressor failure')).toBeDefined();
    expect(screen.getByText('Bearing wear')).toBeDefined();
    expect(screen.getByText('Routine check')).toBeDefined();
  });
});
```

- [ ] **Step 7: Write Maintenance test**

Create `frontend/tests/Maintenance.test.tsx`:
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Maintenance from '../src/pages/Maintenance';

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Maintenance />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('Maintenance page', () => {
  it('renders the page title', () => {
    renderPage();
    expect(screen.getByText('Predictive Maintenance')).toBeDefined();
  });

  it('renders health overview cards', () => {
    renderPage();
    expect(screen.getByText('Healthy')).toBeDefined();
    expect(screen.getByText('Degrading')).toBeDefined();
    expect(screen.getByText('Critical')).toBeDefined();
  });

  it('renders evaluation and prediction panels', () => {
    renderPage();
    expect(screen.getByText('Degradation Evaluation')).toBeDefined();
    expect(screen.getByText('Failure Prediction')).toBeDefined();
  });

  it('renders Run Evaluation and Predict Failure buttons', () => {
    renderPage();
    expect(screen.getByText('Run Evaluation')).toBeDefined();
    expect(screen.getByText('Predict Failure')).toBeDefined();
  });
});
```

- [ ] **Step 8: Run tests**

```bash
cd frontend && npx vitest run
```
Expected: All tests pass (9 tests across 3 suites)

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/src/test-setup.ts frontend/tests/
git commit -m "test(p3d): add vitest setup and tests for EdgeDevices, WorkOrders, Maintenance"
```

---

## Final Verification

After all 8 tasks complete:

1. **TypeScript compilation:** `cd frontend && npx tsc --noEmit` — zero errors
2. **All tests pass:** `cd frontend && npx vitest run` — 9 tests passing
3. **Existing page regression:** All 11 existing routes work (verify via `npx tsc --noEmit` confirms route imports resolve)
4. **Vite dev server starts:** `cd frontend && npx vite` — no build errors
5. **Git log:** 8 commits on master

## Self-Check

- [x] No TBD/TODO placeholders
- [x] All API endpoints match existing backend routes (edgemanager :8006, agent :8004 via gateway :8000)
- [x] State machine transitions match lifecycle.py VALID_TRANSITIONS
- [x] Color/status conventions consistent with existing Dashboard (dark theme, Tailwind classes)
- [x] Tech stack fully compatible with existing package.json
- [x] All new files and modified files listed
- [x] Every step has exact code, commands, and expected output
