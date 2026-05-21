# Plant 3D Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 3D chiller plant topology builder with Three.js — add equipment from library, position in 3D space, connect via pipes with drag interactions, save/restore from API.

**Architecture:** Pure logic (pipe math, auto-layout, data transforms) separated from React UI (panels, tables, page shell) separated from Three.js rendering (canvas, models, interactions). Logic fully unit-testable; UI testable with jsdom + mocked fetch; 3D rendering tested via manual integration. All state in zustand store, synced to Asset Service API.

**Tech Stack:** React 19, TypeScript, Three.js, @react-three/fiber, @react-three/drei, zustand, @tanstack/react-query, vitest, @testing-library/react

---

### Task 1: Install Three.js Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install Three.js packages**

```bash
cd frontend && npm install three @react-three/fiber @react-three/drei @types/three
```

- [ ] **Step 2: Verify install**

```bash
node -e "const THREE = require('three'); console.log('THREE version:', THREE.REVISION)"
```

Expected: Prints THREE version number

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add three.js, @react-three/fiber, @react-three/drei dependencies"
```

---

### Task 2: Equipment Type Definitions & Point Metadata

**Files:**
- Create: `frontend/src/plant/types.ts`
- Create: `frontend/tests/plant/types.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/plant/types.test.ts
import { describe, it, expect } from 'vitest';
import {
  getEquipmentTraits,
  getDisplayPoints,
  getControlPoints,
  POINT_COLORS,
} from '../../src/plant/types';

describe('Equipment types', () => {
  it('centrifugal_chiller has correct traits', () => {
    const traits = getEquipmentTraits('centrifugal_chiller');
    expect(traits.label).toBe('离心式冷水主机');
    expect(traits.color).toBe('#3b82f6');
    expect(traits.dimensions).toEqual({ width: 4, height: 2, depth: 2 });
  });

  it('pump has correct traits', () => {
    const traits = getEquipmentTraits('pump');
    expect(traits.label).toBe('水泵');
    expect(traits.color).toBe('#22c55e');
  });

  it('cooling_tower has correct traits', () => {
    const traits = getEquipmentTraits('cooling_tower');
    expect(traits.label).toBe('冷却塔');
    expect(traits.color).toBe('#f97316');
  });

  it('control_valve has correct traits', () => {
    const traits = getEquipmentTraits('control_valve');
    expect(traits.label).toBe('电动调节阀');
    expect(traits.color).toBe('#eab308');
  });

  it('throws for unknown type', () => {
    expect(() => getEquipmentTraits('unknown_type')).toThrow('Unknown equipment type');
  });
});

describe('Point helpers', () => {
  it('getDisplayPoints returns output and calc points', () => {
    const points = getDisplayPoints('centrifugal_chiller');
    expect(points.length).toBeGreaterThan(0);
    expect(points.every(p => p.io_direction === 'output' || p.io_direction === 'calc')).toBe(true);
  });

  it('getControlPoints returns input points', () => {
    const points = getControlPoints('centrifugal_chiller');
    expect(points.length).toBeGreaterThan(0);
    expect(points.every(p => p.io_direction === 'input')).toBe(true);
  });

  it('POINT_COLORS maps directions', () => {
    expect(POINT_COLORS.input).toBe('#ef4444');
    expect(POINT_COLORS.output).toBe('#22d3ee');
    expect(POINT_COLORS.calc).toBe('#22d3ee');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run tests/plant/types.test.ts
```

Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/plant/types.ts

export interface EquipmentTraits {
  type_code: string;
  label: string;
  color: string;
  dimensions: { width: number; height: number; depth: number };
}

export interface PointDef {
  code: string;
  name: string;
  unit: string;
  data_type: string;
  io_direction: 'input' | 'output' | 'calc';
  required: boolean;
  sort_order: number;
}

const EQUIPMENT_TRAITS: Record<string, EquipmentTraits> = {
  centrifugal_chiller: {
    type_code: 'centrifugal_chiller',
    label: '离心式冷水主机',
    color: '#3b82f6',
    dimensions: { width: 4, height: 2, depth: 2 },
  },
  pump: {
    type_code: 'pump',
    label: '水泵',
    color: '#22c55e',
    dimensions: { width: 1.5, height: 1, depth: 1 },
  },
  cooling_tower: {
    type_code: 'cooling_tower',
    label: '冷却塔',
    color: '#f97316',
    dimensions: { width: 3, height: 3, depth: 3 },
  },
  control_valve: {
    type_code: 'control_valve',
    label: '电动调节阀',
    color: '#eab308',
    dimensions: { width: 0.5, height: 0.3, depth: 0.8 },
  },
  temperature_sensor: {
    type_code: 'temperature_sensor',
    label: '温度传感器',
    color: '#94a3b8',
    dimensions: { width: 0.15, height: 0.15, depth: 0.15 },
  },
  pressure_sensor: {
    type_code: 'pressure_sensor',
    label: '压力传感器',
    color: '#94a3b8',
    dimensions: { width: 0.15, height: 0.15, depth: 0.15 },
  },
  flow_sensor: {
    type_code: 'flow_sensor',
    label: '流量计',
    color: '#94a3b8',
    dimensions: { width: 0.2, height: 0.15, depth: 0.3 },
  },
  power_meter: {
    type_code: 'power_meter',
    label: '功率计',
    color: '#94a3b8',
    dimensions: { width: 0.2, height: 0.15, depth: 0.2 },
  },
};

const POINT_DEFS: Record<string, PointDef[]> = {
  centrifugal_chiller: [
    { code: 'chw_supply_temp', name: '冷冻水供水温度', unit: '°C', data_type: 'float', io_direction: 'input', required: true, sort_order: 1 },
    { code: 'chw_return_temp', name: '冷冻水回水温度', unit: '°C', data_type: 'float', io_direction: 'input', required: true, sort_order: 2 },
    { code: 'cw_entering_temp', name: '冷却水进水温度', unit: '°C', data_type: 'float', io_direction: 'input', required: true, sort_order: 3 },
    { code: 'cw_leaving_temp', name: '冷却水出水温度', unit: '°C', data_type: 'float', io_direction: 'calc', required: true, sort_order: 4 },
    { code: 'power_kw', name: '实时功率', unit: 'kW', data_type: 'float', io_direction: 'calc', required: true, sort_order: 5 },
    { code: 'current_load_rt', name: '实时冷负荷', unit: 'RT', data_type: 'float', io_direction: 'calc', required: true, sort_order: 6 },
    { code: 'evap_flow_rate', name: '蒸发器流量', unit: 'L/s', data_type: 'float', io_direction: 'output', sort_order: 7 },
    { code: 'cond_flow_rate', name: '冷凝器流量', unit: 'L/s', data_type: 'float', io_direction: 'output', sort_order: 8 },
    { code: 'run_status', name: '运行状态', unit: 'enum', data_type: 'string', io_direction: 'output', required: true, sort_order: 9 },
    { code: 'cumulative_hours', name: '累计运行小时', unit: 'h', data_type: 'float', io_direction: 'output', sort_order: 10 },
  ],
  pump: [
    { code: 'speed_hz', name: '运行频率', unit: 'Hz', data_type: 'float', io_direction: 'input', required: true, sort_order: 1 },
    { code: 'power_kw', name: '实时功率', unit: 'kW', data_type: 'float', io_direction: 'calc', required: true, sort_order: 2 },
    { code: 'flow_lps', name: '流量', unit: 'L/s', data_type: 'float', io_direction: 'calc', required: true, sort_order: 3 },
    { code: 'inlet_pressure', name: '进口压力', unit: 'kPa', data_type: 'float', io_direction: 'input', sort_order: 4 },
    { code: 'outlet_pressure', name: '出口压力', unit: 'kPa', data_type: 'float', io_direction: 'calc', sort_order: 5 },
    { code: 'run_status', name: '运行状态', unit: 'enum', data_type: 'string', io_direction: 'output', required: true, sort_order: 6 },
  ],
  cooling_tower: [
    { code: 'fan_speed_hz', name: '风机频率', unit: 'Hz', data_type: 'float', io_direction: 'input', required: true, sort_order: 1 },
    { code: 'water_in_temp', name: '进水温度', unit: '°C', data_type: 'float', io_direction: 'input', required: true, sort_order: 2 },
    { code: 'water_out_temp', name: '出水温度', unit: '°C', data_type: 'float', io_direction: 'calc', required: true, sort_order: 3 },
    { code: 'water_flow_lps', name: '水流量', unit: 'L/s', data_type: 'float', io_direction: 'input', sort_order: 4 },
    { code: 'fan_power_kw', name: '风机功率', unit: 'kW', data_type: 'float', io_direction: 'calc', sort_order: 5 },
    { code: 'run_status', name: '运行状态', unit: 'enum', data_type: 'string', io_direction: 'output', required: true, sort_order: 6 },
  ],
  control_valve: [
    { code: 'valve_position', name: '阀门开度', unit: '%', data_type: 'float', io_direction: 'input', required: true, sort_order: 1 },
    { code: 'inlet_pressure', name: '阀前压力', unit: 'kPa', data_type: 'float', io_direction: 'input', required: true, sort_order: 2 },
    { code: 'outlet_pressure', name: '阀后压力', unit: 'kPa', data_type: 'float', io_direction: 'calc', required: true, sort_order: 3 },
    { code: 'flow_rate', name: '通过流量', unit: 'L/s', data_type: 'float', io_direction: 'calc', sort_order: 4 },
    { code: 'actuator_status', name: '执行器状态', unit: 'enum', data_type: 'string', io_direction: 'output', sort_order: 5 },
  ],
  temperature_sensor: [
    { code: 'measured_temp', name: '测量温度', unit: '°C', data_type: 'float', io_direction: 'output', required: true, sort_order: 1 },
  ],
  pressure_sensor: [
    { code: 'measured_pressure', name: '测量压力', unit: 'kPa', data_type: 'float', io_direction: 'output', required: true, sort_order: 1 },
  ],
  flow_sensor: [
    { code: 'measured_flow', name: '测量流量', unit: 'L/s', data_type: 'float', io_direction: 'output', required: true, sort_order: 1 },
  ],
  power_meter: [
    { code: 'measured_power', name: '测量功率', unit: 'kW', data_type: 'float', io_direction: 'output', required: true, sort_order: 1 },
  ],
};

export const POINT_COLORS: Record<string, string> = {
  input: '#ef4444',
  output: '#22d3ee',
  calc: '#22d3ee',
};

export function getEquipmentTraits(typeCode: string): EquipmentTraits {
  const traits = EQUIPMENT_TRAITS[typeCode];
  if (!traits) throw new Error(`Unknown equipment type: ${typeCode}`);
  return traits;
}

export function getPointDefs(typeCode: string): PointDef[] {
  return POINT_DEFS[typeCode] ?? [];
}

export function getDisplayPoints(typeCode: string): PointDef[] {
  return getPointDefs(typeCode).filter(p => p.io_direction === 'output' || p.io_direction === 'calc');
}

export function getControlPoints(typeCode: string): PointDef[] {
  return getPointDefs(typeCode).filter(p => p.io_direction === 'input');
}

export function getAllTypeCodes(): string[] {
  return Object.keys(EQUIPMENT_TRAITS);
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run tests/plant/types.test.ts
```

Expected: PASS — all 6 tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/plant/types.ts frontend/tests/plant/types.test.ts
git commit -m "feat: add equipment type definitions and point metadata"
```

---

### Task 3: Plant Data Store (Zustand)

**Files:**
- Create: `frontend/src/plant/store.ts`
- Create: `frontend/tests/plant/store.test.ts`

This store holds the working state of the plant builder: selected equipment, pipe segments, UI state. Pure logic, no rendering.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/plant/store.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { usePlantStore } from '../../src/plant/store';

describe('PlantStore', () => {
  beforeEach(() => {
    usePlantStore.setState({
      equipment: [],
      pipeSegments: [],
      selectedId: null,
      plantId: null,
      plantName: '',
    });
  });

  it('adds equipment to the store', () => {
    usePlantStore.getState().addEquipment({
      id: 'eq-1',
      name: 'CH-1',
      type_code: 'centrifugal_chiller',
      position: { x: 0, y: 0, z: 0 },
      design_params: {},
    });
    expect(usePlantStore.getState().equipment).toHaveLength(1);
    expect(usePlantStore.getState().equipment[0].name).toBe('CH-1');
  });

  it('removes equipment and its connected pipes', () => {
    const store = usePlantStore.getState();
    store.addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    store.addEquipment({ id: 'eq-2', name: 'P-1', type_code: 'pump', position: { x: 2, y: 0, z: 0 }, design_params: {} });
    store.addPipeSegment({
      id: 'pipe-1', from_equipment_id: 'eq-1', from_point_code: 'cw_leaving_temp',
      to_equipment_id: 'eq-2', to_point_code: 'inlet_pressure',
      diameter_mm: 200, length_m: 5, waypoints: [],
    });
    store.removeEquipment('eq-1');
    expect(store.equipment).toHaveLength(1);
    expect(store.pipeSegments).toHaveLength(0);
  });

  it('updates equipment position', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().updateEquipmentPosition('eq-1', { x: 5, y: 1, z: 2 });
    expect(usePlantStore.getState().equipment[0].position).toEqual({ x: 5, y: 1, z: 2 });
  });

  it('sets and clears selection', () => {
    usePlantStore.getState().setSelection('eq-1');
    expect(usePlantStore.getState().selectedId).toBe('eq-1');
    usePlantStore.getState().setSelection(null);
    expect(usePlantStore.getState().selectedId).toBeNull();
  });

  it('adds and removes pipe segments', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().addEquipment({ id: 'eq-2', name: 'CT-1', type_code: 'cooling_tower', position: { x: 3, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().addPipeSegment({
      id: 'pipe-1', from_equipment_id: 'eq-1', from_point_code: 'cw_leaving_temp',
      to_equipment_id: 'eq-2', to_point_code: 'water_in_temp',
      diameter_mm: 250, length_m: 10, waypoints: [{ x: 1, y: 0, z: 0 }],
    });
    expect(usePlantStore.getState().pipeSegments).toHaveLength(1);
    usePlantStore.getState().removePipeSegment('pipe-1');
    expect(usePlantStore.getState().pipeSegments).toHaveLength(0);
  });

  it('loads plant data from API response', () => {
    usePlantStore.getState().loadPlantData({
      id: 'plant-1',
      name: 'Test Plant',
      equipment: [
        { id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 } },
      ],
      pipe_segments: [],
    });
    expect(usePlantStore.getState().plantId).toBe('plant-1');
    expect(usePlantStore.getState().plantName).toBe('Test Plant');
    expect(usePlantStore.getState().equipment).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run tests/plant/store.test.ts
```

Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/plant/store.ts
import { create } from 'zustand';

export interface Position3D {
  x: number;
  y: number;
  z: number;
}

export interface PlantEquipment {
  id: string;
  name: string;
  type_code: string;
  position: Position3D;
  design_params: Record<string, unknown>;
}

export interface PipeSegment {
  id: string;
  from_equipment_id: string;
  from_point_code: string;
  to_equipment_id: string;
  to_point_code: string;
  diameter_mm: number;
  length_m: number;
  waypoints: Position3D[];
}

interface PlantState {
  plantId: string | null;
  plantName: string;
  equipment: PlantEquipment[];
  pipeSegments: PipeSegment[];
  selectedId: string | null;

  loadPlantData: (data: { id: string; name: string; equipment: PlantEquipment[]; pipe_segments: PipeSegment[] }) => void;
  addEquipment: (eq: PlantEquipment) => void;
  removeEquipment: (id: string) => void;
  updateEquipmentPosition: (id: string, pos: Position3D) => void;
  addPipeSegment: (ps: PipeSegment) => void;
  removePipeSegment: (id: string) => void;
  setSelection: (id: string | null) => void;
}

export const usePlantStore = create<PlantState>((set) => ({
  plantId: null,
  plantName: '',
  equipment: [],
  pipeSegments: [],
  selectedId: null,

  loadPlantData: (data) => set({
    plantId: data.id,
    plantName: data.name,
    equipment: data.equipment,
    pipeSegments: data.pipe_segments,
    selectedId: null,
  }),

  addEquipment: (eq) => set((s) => ({ equipment: [...s.equipment, eq] })),

  removeEquipment: (id) => set((s) => ({
    equipment: s.equipment.filter(e => e.id !== id),
    pipeSegments: s.pipeSegments.filter(p => p.from_equipment_id !== id && p.to_equipment_id !== id),
    selectedId: s.selectedId === id ? null : s.selectedId,
  })),

  updateEquipmentPosition: (id, pos) => set((s) => ({
    equipment: s.equipment.map(e => e.id === id ? { ...e, position: pos } : e),
  })),

  addPipeSegment: (ps) => set((s) => ({ pipeSegments: [...s.pipeSegments, ps] })),

  removePipeSegment: (id) => set((s) => ({
    pipeSegments: s.pipeSegments.filter(p => p.id !== id),
    selectedId: s.selectedId === id ? null : s.selectedId,
  })),

  setSelection: (id) => set({ selectedId: id }),
}));
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run tests/plant/store.test.ts
```

Expected: PASS — all 6 tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/plant/store.ts frontend/tests/plant/store.test.ts
git commit -m "feat: add plant data store with zustand"
```

---

### Task 4: Pipe Path Calculation Logic

**Files:**
- Create: `frontend/src/plant/pipePath.ts`
- Create: `frontend/tests/plant/pipePath.test.ts`

Pure math: given two 3D points (start, end) and a preferred alignment, produce L-shaped or Z-shaped waypoints for pipe routing.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/plant/pipePath.test.ts
import { describe, it, expect } from 'vitest';
import { computePipePath, computePipeLength, type Point3D } from '../../src/plant/pipePath';

describe('computePipePath', () => {
  it('generates L-path when X axis is dominant', () => {
    const start: Point3D = { x: 0, y: 0, z: 0 };
    const end: Point3D = { x: 5, y: 0, z: 2 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(2);
    // Intermediate turn point
    expect(waypoints[0].x).toBeCloseTo(5);
    expect(waypoints[0].y).toBe(0);
    expect(waypoints[0].z).toBe(0);
  });

  it('generates L-path when Z axis is dominant', () => {
    const start: Point3D = { x: 0, y: 0, z: 0 };
    const end: Point3D = { x: 2, y: 0, z: 5 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(2);
    expect(waypoints[0].x).toBe(0);
    expect(waypoints[0].y).toBe(0);
    expect(waypoints[0].z).toBeCloseTo(5);
  });

  it('handles vertical offset with Z-path', () => {
    const start: Point3D = { x: 0, y: 0, z: 0 };
    const end: Point3D = { x: 3, y: 4, z: 0 };
    const waypoints = computePipePath(start, end);
    // Z-path: horizontal out, then vertical, then horizontal in
    expect(waypoints).toHaveLength(3);
  });

  it('returns empty waypoints for same position', () => {
    const start: Point3D = { x: 1, y: 1, z: 1 };
    const end: Point3D = { x: 1, y: 1, z: 1 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(0);
  });
});

describe('computePipeLength', () => {
  it('computes straight line length', () => {
    const waypoints: Point3D[] = [];
    const length = computePipeLength({ x: 0, y: 0, z: 0 }, { x: 3, y: 4, z: 0 }, waypoints);
    expect(length).toBeCloseTo(5);
  });

  it('computes length through waypoints', () => {
    const waypoints: Point3D[] = [{ x: 3, y: 0, z: 0 }];
    const length = computePipeLength({ x: 0, y: 0, z: 0 }, { x: 3, y: 0, z: 4 }, waypoints);
    // First segment: (0,0,0) → (3,0,0) = 3
    // Second segment: (3,0,0) → (3,0,4) = 4
    expect(length).toBeCloseTo(7);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run tests/plant/pipePath.test.ts
```

Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/plant/pipePath.ts

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

function dist(a: Point3D, b: Point3D): number {
  return Math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2);
}

export function computePipePath(start: Point3D, end: Point3D): Point3D[] {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dz = end.z - start.z;

  if (Math.abs(dx) < 0.01 && Math.abs(dy) < 0.01 && Math.abs(dz) < 0.01) {
    return [];
  }

  if (Math.abs(dy) > 0.01 && (Math.abs(dx) > 0.01 || Math.abs(dz) > 0.01)) {
    // Z-path: horizontal → vertical → horizontal
    const midY = start.y + dy * 0.5;
    if (Math.abs(dx) >= Math.abs(dz)) {
      return [
        { x: start.x + dx * 0.5, y: start.y, z: start.z },
        { x: start.x + dx * 0.5, y: end.y, z: end.z },
      ];
    } else {
      return [
        { x: start.x, y: start.y, z: start.z + dz * 0.5 },
        { x: end.x, y: start.y, z: start.z + dz * 0.5 },
      ];
    }
  }

  // L-path: pick dominant horizontal axis
  if (Math.abs(dx) >= Math.abs(dz)) {
    return [{ x: end.x, y: start.y, z: start.z }];
  } else {
    return [{ x: start.x, y: start.y, z: end.z }];
  }
}

export function computePipeLength(start: Point3D, end: Point3D, waypoints: Point3D[]): number {
  let total = 0;
  let prev = start;
  for (const wp of waypoints) {
    total += dist(prev, wp);
    prev = wp;
  }
  total += dist(prev, end);
  return Math.round(total * 100) / 100;
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run tests/plant/pipePath.test.ts
```

Expected: PASS — all 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/plant/pipePath.ts frontend/tests/plant/pipePath.test.ts
git commit -m "feat: add pipe path calculation logic"
```

---

### Task 5: Auto-Layout Algorithm

**Files:**
- Create: `frontend/src/plant/autoLayout.ts`
- Create: `frontend/tests/plant/autoLayout.test.ts`

Given a list of equipment grouped by type, compute default 3D positions in a sensible arrangement.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/plant/autoLayout.test.ts
import { describe, it, expect } from 'vitest';
import { computeLayout } from '../../src/plant/autoLayout';

describe('computeLayout', () => {
  it('arranges chillers in a row, pumps after, towers after', () => {
    const equipment = [
      { id: 'ch-1', type_code: 'centrifugal_chiller' },
      { id: 'ch-2', type_code: 'centrifugal_chiller' },
      { id: 'p-1', type_code: 'pump' },
      { id: 'ct-1', type_code: 'cooling_tower' },
    ];
    const positions = computeLayout(equipment);
    expect(positions).toHaveLength(4);
    // Chillers are at x=0 plane
    expect(positions[0].z).toBe(0);
    expect(positions[1].z).toBe(0);
    expect(positions[0].x).toBeLessThan(positions[1].x);
    // Pumps are at z > 0
    expect(positions[2].z).toBeGreaterThan(0);
    // Towers are furthest
    expect(positions[3].z).toBeGreaterThan(positions[2].z);
  });

  it('returns empty array for empty input', () => {
    expect(computeLayout([])).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run tests/plant/autoLayout.test.ts
```

Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/plant/autoLayout.ts
import type { Position3D } from './store';

interface LayoutInput {
  id: string;
  type_code: string;
}

const LAYOUT_ORDER = [
  'centrifugal_chiller',
  'pump',
  'cooling_tower',
  'control_valve',
  'temperature_sensor',
  'pressure_sensor',
  'flow_sensor',
  'power_meter',
];

const SPACING_X = 6;
const SPACING_Z = 8;

export function computeLayout(equipment: LayoutInput[]): Position3D[] {
  if (equipment.length === 0) return [];

  const positions: Position3D[] = [];
  const rowCounts: Record<string, number> = {};
  const rowBaseZ: Record<string, number> = {};

  let currentZ = 0;
  for (const typeCode of LAYOUT_ORDER) {
    const items = equipment.filter(e => e.type_code === typeCode);
    if (items.length > 0) {
      rowBaseZ[typeCode] = currentZ;
      rowCounts[typeCode] = items.length;
      currentZ += SPACING_Z;
    }
  }

  for (const eq of equipment) {
    const typeIdx = LAYOUT_ORDER.indexOf(eq.type_code);
    if (typeIdx === -1) {
      positions.push({ x: 0, y: 0, z: 0 });
      continue;
    }
    const z = rowBaseZ[eq.type_code] ?? 0;
    const rowItems = equipment.filter(e => e.type_code === eq.type_code);
    const itemIdx = rowItems.indexOf(eq);
    const totalInRow = rowItems.length;
    const x = (itemIdx - (totalInRow - 1) / 2) * SPACING_X;
    positions.push({ x, y: 0, z });
  }

  return positions;
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run tests/plant/autoLayout.test.ts
```

Expected: PASS — both tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/plant/autoLayout.ts frontend/tests/plant/autoLayout.test.ts
git commit -m "feat: add auto-layout algorithm for equipment placement"
```

---

### Task 6: PlantBuilder Page Shell & Routing

**Files:**
- Modify: `frontend/src/App.tsx:29` (update route)
- Modify: `frontend/src/pages/PlantBuilder.tsx` (replace old content)
- Create: `frontend/tests/plant/PlantBuilder.test.tsx`

Replace the old PlantBuilder with the new 3D builder page shell. The 3D canvas is stubbed at this point — just the layout structure.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/plant/PlantBuilder.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PlantBuilder from '../../src/pages/PlantBuilder';

function renderPage(route = '/plant') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/plant" element={<PlantBuilder />} />
          <Route path="/plant/:id" element={<PlantBuilder />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('PlantBuilder page', () => {
  it('renders the toolbar with add equipment button', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ templates: [] }),
    } as Response);
    renderPage();
    expect(screen.getByText('制冷站构建')).toBeDefined();
    expect(screen.getByText('添加设备')).toBeDefined();
  });

  it('shows loading state when fetching plant by id', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/plants/plant-1')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: 'plant-1', name: 'Test Plant', equipment: [], pipe_segments: [],
          }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage('/plant/plant-1');
    await waitFor(() => {
      expect(screen.getByText('制冷站: Test Plant')).toBeDefined();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run tests/plant/PlantBuilder.test.tsx
```

Expected: FAIL — PlantBuilder page renders old content, tests fail on new expectations

- [ ] **Step 3: Write the page shell implementation**

```typescript
// frontend/src/pages/PlantBuilder.tsx
import { useQuery, useMutation } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { usePlantStore } from '../plant/store';
import { useEffect } from 'react';

export default function PlantBuilder() {
  const { id } = useParams();
  const loadPlantData = usePlantStore(s => s.loadPlantData);
  const plantName = usePlantStore(s => s.plantName);
  const [showEquipmentPanel, setShowEquipmentPanel] = useState(false);

  const { isLoading } = useQuery({
    queryKey: ['plant', id],
    queryFn: () => fetch(`/api/plants/${id}`).then(r => r.json()),
    enabled: !!id,
  });

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-800 border-b border-slate-700">
        <h2 className="text-lg font-bold text-slate-100">
          {id ? `制冷站: ${plantName || id}` : '制冷站构建'}
        </h2>
        <div className="flex-1" />
        <button
          onClick={() => setShowEquipmentPanel(!showEquipmentPanel)}
          className="px-3 py-1.5 bg-cyan-600 text-white rounded text-sm hover:bg-cyan-500"
        >
          添加设备
        </button>
        <button className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded text-sm hover:bg-slate-600">
          校验拓扑
        </button>
        <button className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-500">
          保存
        </button>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {showEquipmentPanel && (
          <div className="w-56 bg-slate-800 border-r border-slate-700 p-3 overflow-y-auto">
            <h3 className="text-sm font-semibold text-slate-400 mb-2">设备库</h3>
            <p className="text-xs text-slate-600">从 /equipment 选择设备</p>
          </div>
        )}
        <div className="flex-1 relative bg-slate-900">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-slate-400">
              加载制冷站...
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-600">
              {/* 3D Canvas placeholder — Task 7 */}
              3D 画布
            </div>
          )}
        </div>
        <div className="w-64 bg-slate-800 border-l border-slate-700 p-3 overflow-y-auto">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">属性</h3>
          <p className="text-xs text-slate-600">选择设备或管段查看属性</p>
        </div>
      </div>

      {/* Pipe table (collapsible) */}
      <div className="h-32 bg-slate-800 border-t border-slate-700 p-3 overflow-y-auto">
        <h3 className="text-sm font-semibold text-slate-400 mb-2">管段列表</h3>
        <p className="text-xs text-slate-600">暂无管段</p>
      </div>
    </div>
  );
}
```

Note: The PlantBuilder page uses the full-height layout. Since the Layout component has `overflow-auto`, we need the PlantBuilder to use `h-full` and manage its own scrolling internally. Actually, let me re-check the Layout. Looking at `Layout.tsx:44`, `<main>` has `overflow-auto p-6`. The PlantBuilder needs to fill the height. Let me adjust the PlantBuilder to use a fixed height approach.

Wait — the Layout.tsx uses `flex-1 overflow-auto p-6` for the `<main>`. This means the PlantBuilder will scroll in the main area. For the 3D builder, we actually want it to fill the available height exactly. Let me update the approach: the PlantBuilder will use `h-[calc(100vh-64px)]` to fill the viewport minus the top bar.

Actually, the Layout has a sidebar (w-56) and the main area. The PlantBuilder needs to fill the main area's height. Let me use `h-full` with flex column layout inside the main area.

Let me revise:

```typescript
// frontend/src/pages/PlantBuilder.tsx
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { usePlantStore } from '../plant/store';

export default function PlantBuilder() {
  const { id } = useParams();
  const loadPlantData = usePlantStore(s => s.loadPlantData);
  const plantName = usePlantStore(s => s.plantName);
  const [showEquipmentPanel, setShowEquipmentPanel] = useState(false);

  const { data: plant, isLoading } = useQuery({
    queryKey: ['plant', id],
    queryFn: () => fetch(`/api/plants/${id}`).then(r => r.json()),
    enabled: !!id,
  });

  useEffect(() => {
    if (plant && id) {
      loadPlantData(plant);
    }
  }, [plant, id, loadPlantData]);

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 5rem)' }}>
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-800 border-b border-slate-700 shrink-0">
        <h2 className="text-lg font-bold text-slate-100">
          {id ? `制冷站: ${plantName || id}` : '制冷站构建'}
        </h2>
        <span className="text-xs text-slate-500">
          {usePlantStore(s => s.equipment.length)} 设备 | {usePlantStore(s => s.pipeSegments.length)} 管段
        </span>
        <div className="flex-1" />
        <button
          onClick={() => setShowEquipmentPanel(v => !v)}
          className="px-3 py-1.5 bg-cyan-600 text-white rounded text-sm hover:bg-cyan-500"
        >
          添加设备
        </button>
        <button className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded text-sm hover:bg-slate-600">
          校验拓扑
        </button>
        <button className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-500">
          保存
        </button>
      </div>

      {/* Main area: equipment panel | canvas | property panel */}
      <div className="flex flex-1 overflow-hidden">
        {showEquipmentPanel && (
          <div className="w-56 bg-slate-800 border-r border-slate-700 p-3 overflow-y-auto shrink-0">
            <h3 className="text-sm font-semibold text-slate-400 mb-2">设备库</h3>
            <p className="text-xs text-slate-600">从设备管理选择设备</p>
          </div>
        )}
        <div className="flex-1 relative bg-slate-900">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-slate-400">加载制冷站...</div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-600">3D 画布</div>
          )}
        </div>
        <div className="w-64 bg-slate-800 border-l border-slate-700 p-3 overflow-y-auto shrink-0">
          <h3 className="text-sm font-semibold text-slate-400 mb-2">属性</h3>
          <p className="text-xs text-slate-600">选择设备或管段查看属性</p>
        </div>
      </div>

      {/* Pipe table */}
      <div className="h-32 bg-slate-800 border-t border-slate-700 p-3 overflow-y-auto shrink-0">
        <h3 className="text-sm font-semibold text-slate-400 mb-2">管段列表</h3>
        <p className="text-xs text-slate-600">暂无管段</p>
      </div>
    </div>
  );
}
```

This looks good. Let me complete the task with proper code.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run tests/plant/PlantBuilder.test.tsx
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PlantBuilder.tsx frontend/tests/plant/PlantBuilder.test.tsx
git commit -m "feat: add PlantBuilder page shell with toolbar and panel layout"
```

---

### Task 7: 3D Canvas with React Three Fiber

**Files:**
- Create: `frontend/src/plant/PlantCanvas.tsx`
- Create: `frontend/src/plant/models/ChillerModel.tsx`
- Create: `frontend/src/plant/models/PumpModel.tsx`
- Create: `frontend/src/plant/models/CoolingTowerModel.tsx`
- Create: `frontend/src/plant/models/ValveModel.tsx`
- Create: `frontend/src/plant/models/PipeMesh.tsx`
- Create: `frontend/src/plant/models/index.ts`

Build the 3D scene: floor grid, equipment models (programmatic geometry), camera controls. Tested manually — Three.js rendering cannot run in jsdom.

- [ ] **Step 1: Write the canvas container and equipment model factories**

```typescript
// frontend/src/plant/models/ChillerModel.tsx
import * as THREE from 'three';
import { useRef } from 'react';
import { getEquipmentTraits } from '../types';

interface ChillerModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
}

export function ChillerModel({ position, onClick, selected }: ChillerModelProps) {
  const groupRef = useRef<THREE.Group>(null);
  const { color, dimensions } = getEquipmentTraits('centrifugal_chiller');
  const { width, height, depth } = dimensions;

  return (
    <group ref={groupRef} position={position} onClick={onClick}>
      {/* Main body */}
      <mesh castShadow position={[0, height / 2, 0]}>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial color={color} metalness={0.3} roughness={0.5} />
      </mesh>
      {/* Motor cylinder on top */}
      <mesh castShadow position={[0, height + 0.3, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.3, 0.3, width * 0.6, 16]} />
        <meshStandardMaterial color="#64748b" metalness={0.6} roughness={0.3} />
      </mesh>
      {/* Nozzles: 4 pipe stubs on sides */}
      {[[-1, 0.3, depth / 2], [1, 0.3, depth / 2], [-1, 0.3, -depth / 2], [1, 0.3, -depth / 2]].map(([nx, ny, nz], i) => (
        <mesh key={i} position={[nx * width / 2, ny + height * 0.3, nz]}>
          <cylinderGeometry args={[0.15, 0.15, 0.5, 8]} />
          <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.2} />
        </mesh>
      ))}
      {/* Selection highlight */}
      {selected && (
        <mesh position={[0, height / 2, 0]}>
          <boxGeometry args={[width + 0.2, height + 0.2, depth + 0.2]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
```

```typescript
// frontend/src/plant/models/PumpModel.tsx
import * as THREE from 'three';
import { useRef } from 'react';
import { getEquipmentTraits } from '../types';

interface PumpModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
}

export function PumpModel({ position, onClick, selected }: PumpModelProps) {
  const { color, dimensions } = getEquipmentTraits('pump');
  const { width, height, depth } = dimensions;

  return (
    <group position={position} onClick={onClick}>
      {/* Pump body (horizontal cylinder) */}
      <mesh castShadow rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[height * 0.35, height * 0.35, width * 0.6, 16]} />
        <meshStandardMaterial color={color} metalness={0.4} roughness={0.3} />
      </mesh>
      {/* Motor on top */}
      <mesh castShadow position={[0, height * 0.5, 0]}>
        <boxGeometry args={[width * 0.4, height * 0.4, depth * 0.4]} />
        <meshStandardMaterial color="#475569" metalness={0.6} roughness={0.3} />
      </mesh>
      {/* Flanges */}
      <mesh position={[width * 0.3, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[height * 0.3, 0.05, 8, 16]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.2} />
      </mesh>
      <mesh position={[-width * 0.3, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
        <torusGeometry args={[height * 0.3, 0.05, 8, 16]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.2} />
      </mesh>
      {selected && (
        <mesh>
          <boxGeometry args={[width + 0.2, height + 0.2, depth + 0.2]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
```

```typescript
// frontend/src/plant/models/CoolingTowerModel.tsx
import * as THREE from 'three';
import { getEquipmentTraits } from '../types';

interface CoolingTowerModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
}

export function CoolingTowerModel({ position, onClick, selected }: CoolingTowerModelProps) {
  const { color, dimensions } = getEquipmentTraits('cooling_tower');
  const { width, height, depth } = dimensions;

  return (
    <group position={position} onClick={onClick}>
      {/* Tower body */}
      <mesh castShadow position={[0, height * 0.6, 0]}>
        <boxGeometry args={[width, height * 0.8, depth]} />
        <meshStandardMaterial color={color} metalness={0.1} roughness={0.7} />
      </mesh>
      {/* Fan deck on top */}
      <mesh castShadow position={[0, height, 0]}>
        <cylinderGeometry args={[width * 0.3, width * 0.35, 0.3, 16]} />
        <meshStandardMaterial color="#64748b" metalness={0.4} roughness={0.4} />
      </mesh>
      {/* Fan grill */}
      <mesh position={[0, height + 0.15, 0]} rotation={[0, 0, 0]}>
        <ringGeometry args={[0.1, width * 0.28, 32]} />
        <meshBasicMaterial color="#475569" side={THREE.DoubleSide} />
      </mesh>
      {selected && (
        <mesh position={[0, height / 2, 0]}>
          <boxGeometry args={[width + 0.2, height + 0.2, depth + 0.2]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
```

```typescript
// frontend/src/plant/models/ValveModel.tsx
import * as THREE from 'three';
import { getEquipmentTraits } from '../types';

interface ValveModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
}

export function ValveModel({ position, onClick, selected }: ValveModelProps) {
  const { color, dimensions } = getEquipmentTraits('control_valve');
  const { width, height, depth } = dimensions;

  return (
    <group position={position} onClick={onClick}>
      {/* Pipe section */}
      <mesh castShadow rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.15, 0.15, width, 8]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.3} />
      </mesh>
      {/* Actuator box on top */}
      <mesh castShadow position={[0, height * 0.6, 0]}>
        <boxGeometry args={[width * 0.5, height * 0.8, depth * 0.6]} />
        <meshStandardMaterial color={color} metalness={0.4} roughness={0.4} />
      </mesh>
      {/* Handwheel */}
      <mesh position={[0, height * 0.6 + height * 0.4, 0]} rotation={[0, 0, 0]}>
        <torusGeometry args={[0.15, 0.03, 8, 16]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.2} />
      </mesh>
      {selected && (
        <mesh>
          <boxGeometry args={[width + 0.1, height + 0.1, depth + 0.1]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
```

```typescript
// frontend/src/plant/models/PipeMesh.tsx
import * as THREE from 'three';
import { useMemo } from 'react';
import type { Position3D } from '../store';

interface PipeMeshProps {
  start: Position3D;
  end: Position3D;
  waypoints: Position3D[];
  diameter: number;
  color?: string;
  onClick?: () => void;
  selected?: boolean;
}

export function PipeMesh({ start, end, waypoints, diameter, color = '#64748b', onClick, selected }: PipeMeshProps) {
  const radius = (diameter / 1000) / 2; // convert mm to m radius

  const path = useMemo(() => {
    const points: THREE.Vector3[] = [];
    points.push(new THREE.Vector3(start.x, start.y, start.z));
    for (const wp of waypoints) {
      points.push(new THREE.Vector3(wp.x, wp.y, wp.z));
    }
    points.push(new THREE.Vector3(end.x, end.y, end.z));
    const curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0);
    return curve;
  }, [start, end, waypoints]);

  return (
    <mesh onClick={onClick}>
      <tubeGeometry args={[path, 16, radius, 8, false]} />
      <meshStandardMaterial color={selected ? '#38bdf8' : color} metalness={0.7} roughness={0.3} />
    </mesh>
  );
}
```

```typescript
// frontend/src/plant/models/index.ts
export { ChillerModel } from './ChillerModel';
export { PumpModel } from './PumpModel';
export { CoolingTowerModel } from './CoolingTowerModel';
export { ValveModel } from './ValveModel';
export { PipeMesh } from './PipeMesh';
```

- [ ] **Step 2: Write the PlantCanvas component**

```typescript
// frontend/src/plant/PlantCanvas.tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import { usePlantStore } from './store';
import { ChillerModel, PumpModel, CoolingTowerModel, ValveModel, PipeMesh } from './models';
import { getPointDefs, POINT_COLORS } from './types';
import * as THREE from 'three';

function EquipmentNode({ eq }: { eq: { id: string; name: string; type_code: string; position: { x: number; y: number; z: number } } }) {
  const selectedId = usePlantStore(s => s.selectedId);
  const setSelection = usePlantStore(s => s.setSelection);
  const pos: [number, number, number] = [eq.position.x, eq.position.y, eq.position.z];
  const selected = selectedId === eq.id;

  const props = { position: pos, onClick: () => setSelection(eq.id), selected };

  switch (eq.type_code) {
    case 'centrifugal_chiller': return <ChillerModel {...props} />;
    case 'pump': return <PumpModel {...props} />;
    case 'cooling_tower': return <CoolingTowerModel {...props} />;
    case 'control_valve': return <ValveModel {...props} />;
    default: return <ChillerModel {...props} />;
  }
}

function PointBadges({ eq }: { eq: { id: string; type_code: string; position: { x: number; y: number; z: number } } }) {
  const points = getPointDefs(eq.type_code);
  return (
    <group>
      {points.map((p, i) => {
        const angle = (i / points.length) * Math.PI * 2;
        const r = 1.2;
        const px = eq.position.x + Math.cos(angle) * r;
        const py = eq.position.y + 1 + (i % 3) * 0.3;
        const pz = eq.position.z + Math.sin(angle) * r;
        const color = POINT_COLORS[p.io_direction] || '#ffffff';
        return (
          <mesh key={p.code} position={[px, py, pz]}>
            <sphereGeometry args={[0.1, 16, 16]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
          </mesh>
        );
      })}
    </group>
  );
}

function PipeLines() {
  const pipeSegments = usePlantStore(s => s.pipeSegments);
  const equipment = usePlantStore(s => s.equipment);
  const selectedId = usePlantStore(s => s.selectedId);
  const setSelection = usePlantStore(s => s.setSelection);

  return (
    <group>
      {pipeSegments.map(ps => {
        const fromEq = equipment.find(e => e.id === ps.from_equipment_id);
        const toEq = equipment.find(e => e.id === ps.to_equipment_id);
        if (!fromEq || !toEq) return null;
        return (
          <PipeMesh
            key={ps.id}
            start={fromEq.position}
            end={toEq.position}
            waypoints={ps.waypoints}
            diameter={ps.diameter_mm}
            onClick={() => setSelection(ps.id)}
            selected={selectedId === ps.id}
          />
        );
      })}
    </group>
  );
}

export default function PlantCanvas() {
  const equipment = usePlantStore(s => s.equipment);

  return (
    <Canvas
      shadows
      camera={{ position: [15, 12, 15], fov: 50, near: 0.1, far: 200 }}
      style={{ width: '100%', height: '100%' }}
    >
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[20, 30, 10]}
        intensity={0.8}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <Grid
        position={[0, -0.01, 0]}
        args={[40, 40]}
        cellSize={2}
        cellThickness={0.5}
        cellColor="#334155"
        sectionSize={10}
        sectionThickness={1}
        sectionColor="#1e293b"
        fadeDistance={50}
        infiniteGrid
      />
      <group>
        {equipment.map(eq => (
          <group key={eq.id}>
            <EquipmentNode eq={eq} />
            <PointBadges eq={eq} />
          </group>
        ))}
        <PipeLines />
      </group>
      <OrbitControls
        makeDefault
        maxPolarAngle={Math.PI / 2.2}
        minDistance={5}
        maxDistance={60}
        target={[0, 1, 0]}
      />
    </Canvas>
  );
}
```

- [ ] **Step 3: Integrate canvas into PlantBuilder page**

Replace the placeholder `3D 画布` div with `<PlantCanvas />` in `frontend/src/pages/PlantBuilder.tsx`.

Add import:
```typescript
import PlantCanvas from '../plant/PlantCanvas';
```

Replace:
```typescript
<div className="flex items-center justify-center h-full text-slate-600">3D 画布</div>
```
with:
```typescript
<PlantCanvas />
```

- [ ] **Step 4: Verify the app compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: No errors (or only pre-existing errors unrelated to our code)

- [ ] **Step 5: Manual verification**

Start the dev server and verify:
- `/plant` page loads with 3D canvas
- Grid floor is visible
- OrbitControls work (rotate, zoom, pan)
- Add equipment via store → verify it renders

- [ ] **Step 6: Commit**

```bash
git add frontend/src/plant/models/ frontend/src/plant/PlantCanvas.tsx frontend/src/pages/PlantBuilder.tsx
git commit -m "feat: add 3D plant canvas with equipment models and pipe rendering"
```

---

### Task 8: Equipment Panel (Device Library)

**Files:**
- Create: `frontend/src/plant/EquipmentPanel.tsx`
- Create: `frontend/tests/plant/EquipmentPanel.test.tsx`

Left sidebar that fetches equipment from `/api/equipment` (or uses mock data), groups by type, allows selecting and adding to the plant.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/plant/EquipmentPanel.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EquipmentPanel } from '../../src/plant/EquipmentPanel';
import { usePlantStore } from '../../src/plant/store';

const mockEquipment = [
  { id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', plant_id: null, design_params: {} },
  { id: 'eq-2', name: 'CH-2', type_code: 'centrifugal_chiller', plant_id: null, design_params: {} },
  { id: 'eq-3', name: 'P-1', type_code: 'pump', plant_id: null, design_params: {} },
];

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <EquipmentPanel />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  usePlantStore.setState({ equipment: [], pipeSegments: [], selectedId: null, plantId: null, plantName: '' });
});

describe('EquipmentPanel', () => {
  it('fetches and displays equipment grouped by type', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEquipment),
    } as Response);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('CH-1')).toBeDefined();
      expect(screen.getByText('CH-2')).toBeDefined();
      expect(screen.getByText('P-1')).toBeDefined();
    });
  });

  it('adds equipment to plant store on click', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEquipment),
    } as Response);
    renderPanel();
    await waitFor(() => screen.getByText('CH-1'));
    await userEvent.click(screen.getByText('CH-1'));
    const store = usePlantStore.getState();
    expect(store.equipment).toHaveLength(1);
    expect(store.equipment[0].name).toBe('CH-1');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run tests/plant/EquipmentPanel.test.tsx
```

Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

```typescript
// frontend/src/plant/EquipmentPanel.tsx
import { useQuery } from '@tanstack/react-query';
import { usePlantStore } from './store';
import { getEquipmentTraits, getAllTypeCodes } from './types';
import { computeLayout } from './autoLayout';

interface EquipmentItem {
  id: string;
  name: string;
  type_code: string;
  plant_id: string | null;
  design_params: Record<string, unknown>;
}

export function EquipmentPanel() {
  const addEquipment = usePlantStore(s => s.addEquipment);
  const existingIds = usePlantStore(s => s.equipment.map(e => e.id));

  const { data, isLoading } = useQuery({
    queryKey: ['equipment-library'],
    queryFn: () => fetch('/api/equipment').then(r => r.json()),
  });

  const equipment: EquipmentItem[] = Array.isArray(data) ? data : (data?.equipment ?? []);

  const availableEquipment = equipment.filter(
    e => !existingIds.includes(e.id) && !e.plant_id
  );

  const grouped: Record<string, EquipmentItem[]> = {};
  for (const eq of availableEquipment) {
    (grouped[eq.type_code] ??= []).push(eq);
  }

  const handleAdd = (eq: EquipmentItem) => {
    const pos = computeLayout([{ id: eq.id, type_code: eq.type_code }])[0];
    addEquipment({
      id: eq.id,
      name: eq.name,
      type_code: eq.type_code,
      position: pos,
      design_params: eq.design_params,
    });
  };

  return (
    <div className="w-56 bg-slate-800 border-r border-slate-700 flex flex-col shrink-0">
      <div className="p-3 border-b border-slate-700">
        <h3 className="text-sm font-semibold text-slate-400">设备库</h3>
        <p className="text-xs text-slate-600 mt-1">点击设备添加到画布</p>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-3">
        {isLoading ? (
          <p className="text-xs text-slate-500 p-2">加载设备库...</p>
        ) : availableEquipment.length === 0 ? (
          <p className="text-xs text-slate-600 p-2">暂无可选设备</p>
        ) : (
          Object.entries(grouped).map(([typeCode, items]) => {
            const traits = getEquipmentTraits(typeCode);
            return (
              <div key={typeCode}>
                <div className="text-xs text-slate-500 font-semibold mb-1 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: traits.color }} />
                  {traits.label} ({items.length})
                </div>
                {items.map(eq => (
                  <button
                    key={eq.id}
                    onClick={() => handleAdd(eq)}
                    className="w-full text-left px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-700 rounded mb-0.5 truncate"
                  >
                    {eq.name}
                  </button>
                ))}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run tests/plant/EquipmentPanel.test.tsx
```

Expected: PASS

- [ ] **Step 5: Integrate into PlantBuilder**

In `PlantBuilder.tsx`, replace the equipment panel placeholder:
```typescript
{showEquipmentPanel && <EquipmentPanel />}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/plant/EquipmentPanel.tsx frontend/tests/plant/EquipmentPanel.test.tsx frontend/src/pages/PlantBuilder.tsx
git commit -m "feat: add equipment panel with device library and drag-to-add"
```

---

### Task 9: Property Panel

**Files:**
- Create: `frontend/src/plant/PropertyPanel.tsx`
- Create: `frontend/tests/plant/PropertyPanel.test.tsx`

Right sidebar showing selected equipment/pipe details, with display points and control points.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/plant/PropertyPanel.test.tsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PropertyPanel } from '../../src/plant/PropertyPanel';
import { usePlantStore } from '../../src/plant/store';

beforeEach(() => {
  usePlantStore.setState({ equipment: [], pipeSegments: [], selectedId: null, plantId: null, plantName: '' });
});

describe('PropertyPanel', () => {
  it('shows empty state when nothing selected', () => {
    render(<PropertyPanel />);
    expect(screen.getByText('选择设备或管段查看属性')).toBeDefined();
  });

  it('shows equipment properties when equipment selected', () => {
    usePlantStore.setState({
      equipment: [
        { id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: { capacity_rt: 500 } },
      ],
      selectedId: 'eq-1',
    });
    render(<PropertyPanel />);
    expect(screen.getByText('CH-1')).toBeDefined();
    expect(screen.getByText('离心式冷水主机')).toBeDefined();
    // Display points section
    expect(screen.getByText('显示点位')).toBeDefined();
    // Control points section
    expect(screen.getByText('控制点位')).toBeDefined();
  });

  it('shows pipe properties when pipe selected', () => {
    usePlantStore.setState({
      equipment: [
        { id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} },
        { id: 'eq-2', name: 'P-1', type_code: 'pump', position: { x: 2, y: 0, z: 0 }, design_params: {} },
      ],
      pipeSegments: [
        { id: 'pipe-1', from_equipment_id: 'eq-1', from_point_code: 'cw_leaving_temp', to_equipment_id: 'eq-2', to_point_code: 'inlet_pressure', diameter_mm: 200, length_m: 5, waypoints: [] },
      ],
      selectedId: 'pipe-1',
    });
    render(<PropertyPanel />);
    expect(screen.getByText(/管段/)).toBeDefined();
    expect(screen.getByText(/DN200/)).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run tests/plant/PropertyPanel.test.tsx
```

Expected: FAIL

- [ ] **Step 3: Write implementation**

```typescript
// frontend/src/plant/PropertyPanel.tsx
import { usePlantStore } from './store';
import { getEquipmentTraits, getDisplayPoints, getControlPoints } from './types';

export function PropertyPanel() {
  const selectedId = usePlantStore(s => s.selectedId);
  const equipment = usePlantStore(s => s.equipment);
  const pipeSegments = usePlantStore(s => s.pipeSegments);
  const setSelection = usePlantStore(s => s.setSelection);

  const selectedEquipment = equipment.find(e => e.id === selectedId);
  const selectedPipe = pipeSegments.find(p => p.id === selectedId);

  if (!selectedId) {
    return (
      <div className="w-64 bg-slate-800 border-l border-slate-700 p-3 overflow-y-auto shrink-0">
        <h3 className="text-sm font-semibold text-slate-400 mb-2">属性</h3>
        <p className="text-xs text-slate-600">选择设备或管段查看属性</p>
      </div>
    );
  }

  if (selectedEquipment) {
    const traits = getEquipmentTraits(selectedEquipment.type_code);
    const displayPoints = getDisplayPoints(selectedEquipment.type_code);
    const controlPoints = getControlPoints(selectedEquipment.type_code);

    return (
      <div className="w-64 bg-slate-800 border-l border-slate-700 overflow-y-auto shrink-0">
        <div className="p-3 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: traits.color }} />
            <h3 className="text-sm font-semibold text-slate-200">{selectedEquipment.name}</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">{traits.label}</p>
        </div>

        {/* Control points */}
        <div className="p-3 border-b border-slate-700">
          <h4 className="text-xs font-semibold text-red-400 mb-2">控制点位</h4>
          {controlPoints.length === 0 ? (
            <p className="text-xs text-slate-600">无</p>
          ) : (
            <div className="space-y-1.5">
              {controlPoints.map(p => (
                <div key={p.code} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400" title={p.code}>{p.name}</span>
                  <span className="text-slate-500">{p.unit}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Display points */}
        <div className="p-3 border-b border-slate-700">
          <h4 className="text-xs font-semibold text-cyan-400 mb-2">显示点位</h4>
          {displayPoints.length === 0 ? (
            <p className="text-xs text-slate-600">无</p>
          ) : (
            <div className="space-y-1.5">
              {displayPoints.map(p => (
                <div key={p.code} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400" title={p.code}>{p.name}</span>
                  <span className="text-slate-500">{p.unit}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Design params */}
        {Object.keys(selectedEquipment.design_params).length > 0 && (
          <div className="p-3">
            <h4 className="text-xs font-semibold text-slate-400 mb-2">设计参数</h4>
            <div className="space-y-1">
              {Object.entries(selectedEquipment.design_params).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">{k}</span>
                  <span className="text-slate-300">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (selectedPipe) {
    const fromEq = equipment.find(e => e.id === selectedPipe.from_equipment_id);
    const toEq = equipment.find(e => e.id === selectedPipe.to_equipment_id);

    return (
      <div className="w-64 bg-slate-800 border-l border-slate-700 overflow-y-auto shrink-0">
        <div className="p-3 border-b border-slate-700">
          <h3 className="text-sm font-semibold text-slate-200">管段</h3>
          <p className="text-xs text-slate-500 mt-1 font-mono">{selectedPipe.id}</p>
        </div>
        <div className="p-3 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">源设备</span>
            <span className="text-slate-300">{fromEq?.name || selectedPipe.from_equipment_id}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">源点位</span>
            <span className="text-cyan-400 font-mono">{selectedPipe.from_point_code}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">目标设备</span>
            <span className="text-slate-300">{toEq?.name || selectedPipe.to_equipment_id}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">目标点位</span>
            <span className="text-cyan-400 font-mono">{selectedPipe.to_point_code}</span>
          </div>
          <hr className="border-slate-700" />
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">管径</span>
            <span className="text-slate-300">DN{selectedPipe.diameter_mm}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">长度</span>
            <span className="text-slate-300">{selectedPipe.length_m}m</span>
          </div>
          <button
            onClick={() => setSelection(null)}
            className="w-full px-2 py-1 bg-red-900/30 text-red-400 text-xs rounded hover:bg-red-900/50 mt-2"
          >
            删除管段
          </button>
        </div>
      </div>
    );
  }

  return null;
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run tests/plant/PropertyPanel.test.tsx
```

Expected: PASS

- [ ] **Step 5: Integrate into PlantBuilder**

Replace the property panel placeholder in `PlantBuilder.tsx` with `<PropertyPanel />`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/plant/PropertyPanel.tsx frontend/tests/plant/PropertyPanel.test.tsx frontend/src/pages/PlantBuilder.tsx
git commit -m "feat: add property panel with equipment points and pipe details"
```

---

### Task 10: Pipe Table (Bottom Panel)

**Files:**
- Create: `frontend/src/plant/PipeTable.tsx`
- Create: `frontend/tests/plant/PipeTable.test.tsx`

Bottom collapsible table showing all pipe segments with inline editing.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/plant/PipeTable.test.tsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PipeTable } from '../../src/plant/PipeTable';
import { usePlantStore } from '../../src/plant/store';

beforeEach(() => {
  usePlantStore.setState({ equipment: [], pipeSegments: [], selectedId: null, plantId: null, plantName: '' });
});

describe('PipeTable', () => {
  it('shows empty state when no pipes', () => {
    render(<PipeTable />);
    expect(screen.getByText('暂无管段')).toBeDefined();
  });

  it('displays pipe segments with equipment names', () => {
    usePlantStore.setState({
      equipment: [
        { id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} },
        { id: 'eq-2', name: 'CT-1', type_code: 'cooling_tower', position: { x: 3, y: 0, z: 0 }, design_params: {} },
      ],
      pipeSegments: [
        { id: 'pipe-1', from_equipment_id: 'eq-1', from_point_code: 'cw_leaving_temp', to_equipment_id: 'eq-2', to_point_code: 'water_in_temp', diameter_mm: 200, length_m: 15, waypoints: [] },
      ],
    });
    render(<PipeTable />);
    expect(screen.getByText('CH-1')).toBeDefined();
    expect(screen.getByText('CT-1')).toBeDefined();
    expect(screen.getByText('DN200')).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run tests/plant/PipeTable.test.tsx
```

Expected: FAIL

- [ ] **Step 3: Write implementation**

```typescript
// frontend/src/plant/PipeTable.tsx
import { usePlantStore } from './store';

export function PipeTable() {
  const pipeSegments = usePlantStore(s => s.pipeSegments);
  const equipment = usePlantStore(s => s.equipment);
  const setSelection = usePlantStore(s => s.setSelection);

  const getEqName = (id: string) => equipment.find(e => e.id === id)?.name || id;

  return (
    <div className="h-40 bg-slate-800 border-t border-slate-700 flex flex-col shrink-0">
      <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-400">管段列表</h3>
        <span className="text-xs text-slate-600">{pipeSegments.length} 条</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {pipeSegments.length === 0 ? (
          <p className="text-xs text-slate-600 p-3">暂无管段 — 在画布上拖拽点位连线</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-700">
                <th className="text-left px-3 py-1.5 font-medium">#</th>
                <th className="text-left px-3 py-1.5 font-medium">源设备</th>
                <th className="text-left px-3 py-1.5 font-medium">源点位</th>
                <th className="text-left px-3 py-1.5 font-medium">目标设备</th>
                <th className="text-left px-3 py-1.5 font-medium">管径</th>
                <th className="text-left px-3 py-1.5 font-medium">长度</th>
              </tr>
            </thead>
            <tbody>
              {pipeSegments.map((ps, i) => (
                <tr
                  key={ps.id}
                  onClick={() => setSelection(ps.id)}
                  className="border-b border-slate-700/50 hover:bg-slate-700/50 cursor-pointer text-slate-300"
                >
                  <td className="px-3 py-1 text-slate-600">{i + 1}</td>
                  <td className="px-3 py-1">{getEqName(ps.from_equipment_id)}</td>
                  <td className="px-3 py-1 text-cyan-400 font-mono">{ps.from_point_code}</td>
                  <td className="px-3 py-1">{getEqName(ps.to_equipment_id)}</td>
                  <td className="px-3 py-1">DN{ps.diameter_mm}</td>
                  <td className="px-3 py-1">{ps.length_m}m</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npx vitest run tests/plant/PipeTable.test.tsx
```

Expected: PASS

- [ ] **Step 5: Integrate into PlantBuilder**

Replace pipe table placeholder in `PlantBuilder.tsx` with `<PipeTable />`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/plant/PipeTable.tsx frontend/tests/plant/PipeTable.test.tsx frontend/src/pages/PlantBuilder.tsx
git commit -m "feat: add pipe table with equipment names and specs"
```

---

### Task 11: Integration — Wiring PlantBuilder Together

**Files:**
- Modify: `frontend/src/pages/PlantBuilder.tsx` (final integration)
- Modify: `frontend/src/plant/PlantCanvas.tsx` (add TransformControls for positioning)
- Modify: `frontend/src/plant/models/ChillerModel.tsx` (add drag via TransformControls)

Wire all components together, add save/load functionality, handle equipment positioning via TransformControls.

- [ ] **Step 1: Add save functionality and TransformControls to PlantCanvas**

Update `PlantCanvas.tsx` to add TransformControls for selected equipment:

```typescript
// Add to imports:
import { TransformControls } from '@react-three/drei';
import { useRef, useCallback } from 'react';

// Add inside PlantCanvas component, before OrbitControls:
function SelectedTransform() {
  const selectedId = usePlantStore(s => s.selectedId);
  const equipment = usePlantStore(s => s.equipment);
  const updatePosition = usePlantStore(s => s.updateEquipmentPosition);
  const meshRef = useRef<THREE.Mesh>(null);

  const selected = equipment.find(e => e.id === selectedId);
  if (!selected) return null;

  const handleChange = useCallback(() => {
    if (meshRef.current) {
      const p = meshRef.current.position;
      updatePosition(selected.id, { x: p.x, y: p.y, z: p.z });
    }
  }, [selected.id]);

  return (
    <TransformControls
      object={meshRef}
      mode="translate"
      onChange={handleChange}
    >
      <mesh ref={meshRef} position={[selected.position.x, selected.position.y, selected.position.z]} visible={false}>
        <boxGeometry args={[0.1, 0.1, 0.1]} />
      </mesh>
    </TransformControls>
  );
}
```

- [ ] **Step 2: Add save mutation to PlantBuilder page**

Update `PlantBuilder.tsx` — add the save `useMutation`:

```typescript
const savePlant = useMutation({
  mutationFn: () => {
    const state = usePlantStore.getState();
    const body = {
      id: state.plantId || undefined,
      name: state.plantName || '新建制冷站',
      equipment: state.equipment.map(e => ({
        id: e.id,
        name: e.name,
        type_code: e.type_code,
        position: e.position,
      })),
      pipe_segments: state.pipeSegments,
    };
    const url = '/api/plants/';
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(r => r.json());
  },
  onSuccess: (data) => {
    usePlantStore.setState({ plantId: data.id, plantName: data.name });
  },
});
```

- [ ] **Step 3: Wire save button**

```typescript
<button
  onClick={() => savePlant.mutate()}
  disabled={savePlant.isPending}
  className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-500 disabled:opacity-50"
>
  {savePlant.isPending ? '保存中...' : '保存'}
</button>
```

- [ ] **Step 4: Run full test suite**

```bash
cd frontend && npx vitest run tests/plant/
```

Expected: All plant tests pass

- [ ] **Step 5: Manual integration test**

Start dev server, verify:
1. Open `/plant` → 3D canvas with grid
2. Click "添加设备" → equipment panel shows
3. Click equipment in panel → 3D model appears on canvas
4. Click equipment in canvas → property panel shows points
5. Click another equipment → both appear
6. Click "保存" → plant saved to API
7. Open `/plant/{id}` → canvas restores with saved equipment

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PlantBuilder.tsx frontend/src/plant/PlantCanvas.tsx
git commit -m "feat: integrate plant builder with save/load and transform controls"
```

---

### Task 12: Drag-to-Connect Pipe Interaction

**Files:**
- Create: `frontend/src/plant/interaction/usePipeConnection.ts`
- Modify: `frontend/src/plant/PlantCanvas.tsx`

Implement the drag-from-point-to-point pipe connection interaction.

- [ ] **Step 1: Write connection hook**

```typescript
// frontend/src/plant/interaction/usePipeConnection.ts
import { useState, useCallback } from 'react';
import { usePlantStore, type Position3D } from '../store';
import { computePipePath, computePipeLength } from '../pipePath';

interface ConnectionState {
  fromEquipmentId: string;
  fromPointCode: string;
  startPos: Position3D;
}

export function usePipeConnection() {
  const [activeConnection, setActiveConnection] = useState<ConnectionState | null>(null);
  const addPipeSegment = usePlantStore(s => s.addPipeSegment);
  const equipment = usePlantStore(s => s.equipment);

  const startConnection = useCallback((equipmentId: string, pointCode: string) => {
    const eq = equipment.find(e => e.id === equipmentId);
    if (!eq) return;
    setActiveConnection({
      fromEquipmentId: equipmentId,
      fromPointCode: pointCode,
      startPos: eq.position,
    });
  }, [equipment]);

  const completeConnection = useCallback((toEquipmentId: string, toPointCode: string) => {
    if (!activeConnection) return;
    if (activeConnection.fromEquipmentId === toEquipmentId) {
      setActiveConnection(null);
      return;
    }
    const toEq = equipment.find(e => e.id === toEquipmentId);
    if (!toEq) { setActiveConnection(null); return; }

    const waypoints = computePipePath(activeConnection.startPos, toEq.position);
    const length = computePipeLength(activeConnection.startPos, toEq.position, waypoints);

    addPipeSegment({
      id: `pipe-${Date.now()}`,
      from_equipment_id: activeConnection.fromEquipmentId,
      from_point_code: activeConnection.fromPointCode,
      to_equipment_id: toEquipmentId,
      to_point_code: toPointCode,
      diameter_mm: 200,
      length_m: length,
      waypoints,
    });
    setActiveConnection(null);
  }, [activeConnection, equipment, addPipeSegment]);

  const cancelConnection = useCallback(() => {
    setActiveConnection(null);
  }, []);

  return { activeConnection, startConnection, completeConnection, cancelConnection };
}
```

- [ ] **Step 2: Integrate connection into canvas**

Add click interaction to point badges that triggers connections. Points that are `input` (control) can receive connections; points that are `output` or `calc` (display) can start connections.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/plant/interaction/
git commit -m "feat: add drag-to-connect pipe interaction hook"
```

---

## Summary

| Task | Component | Tested |
|------|-----------|--------|
| 1 | Install deps | N/A |
| 2 | Equipment type definitions | Unit |
| 3 | Plant data store | Unit |
| 4 | Pipe path calculation | Unit |
| 5 | Auto-layout algorithm | Unit |
| 6 | PlantBuilder page shell | Component |
| 7 | 3D canvas + models | Manual |
| 8 | Equipment panel | Component |
| 9 | Property panel | Component |
| 10 | Pipe table | Component |
| 11 | Full integration | Component + Manual |
| 12 | Pipe connection interaction | Unit + Manual |

**Non-goals:** Real-time sensor data streaming, pipe fluid animation, multi-user collaboration, VR/AR, undo/redo history.
