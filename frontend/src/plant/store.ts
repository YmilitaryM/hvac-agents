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

interface HistorySnapshot {
  equipment: PlantEquipment[];
  pipeSegments: PipeSegment[];
}

const MAX_HISTORY = 50;

interface PlantState {
  plantId: string | null;
  plantName: string;
  equipment: PlantEquipment[];
  pipeSegments: PipeSegment[];
  selectedId: string | null;

  past: HistorySnapshot[];
  future: HistorySnapshot[];

  loadPlantData: (data: { id: string; name: string; equipment: PlantEquipment[]; pipe_segments: PipeSegment[] }) => void;
  addEquipment: (eq: PlantEquipment, opts?: { _source?: 'local' | 'remote' }) => void;
  removeEquipment: (id: string, opts?: { _source?: 'local' | 'remote' }) => void;
  updateEquipmentPosition: (id: string, pos: Position3D) => void;
  addPipeSegment: (ps: PipeSegment, opts?: { _source?: 'local' | 'remote' }) => void;
  removePipeSegment: (id: string, opts?: { _source?: 'local' | 'remote' }) => void;
  setSelection: (id: string | null) => void;
  undo: () => void;
  redo: () => void;
  _pushHistory: () => void;
  _dragSnapshotTaken: boolean;
  _setDragSnapshotTaken: (v: boolean) => void;
}

function snapshot(state: PlantState): HistorySnapshot {
  return {
    equipment: state.equipment,
    pipeSegments: state.pipeSegments,
  };
}

export const usePlantStore = create<PlantState>((set, get) => ({
  plantId: null,
  plantName: '',
  equipment: [],
  pipeSegments: [],
  selectedId: null,
  past: [],
  future: [],
  _dragSnapshotTaken: false,

  _pushHistory: () => {
    const s = get();
    set({
      past: [...s.past.slice(-(MAX_HISTORY - 1)), snapshot(s)],
      future: [],
    });
  },

  _setDragSnapshotTaken: (v) => set({ _dragSnapshotTaken: v }),

  undo: () => {
    const s = get();
    if (s.past.length === 0) return;
    const prev = s.past[s.past.length - 1];
    set({
      past: s.past.slice(0, -1),
      future: [snapshot(s), ...s.future],
      equipment: prev.equipment,
      pipeSegments: prev.pipeSegments,
      selectedId: null,
    });
  },

  redo: () => {
    const s = get();
    if (s.future.length === 0) return;
    const next = s.future[0];
    set({
      future: s.future.slice(1),
      past: [...s.past, snapshot(s)],
      equipment: next.equipment,
      pipeSegments: next.pipeSegments,
      selectedId: null,
    });
  },

  loadPlantData: (data) => set({
    plantId: data.id,
    plantName: data.name,
    equipment: Array.isArray(data.equipment)
      ? data.equipment.map((e: Record<string, unknown>) => ({ ...e, design_params: e.design_params || {} }))
      : [],
    pipeSegments: Array.isArray(data.pipe_segments) ? data.pipe_segments : [],
    selectedId: null,
    past: [],
    future: [],
  }),

  addEquipment: (eq, opts) => {
    if (opts?._source !== 'remote') get()._pushHistory();
    set((s) => ({ equipment: [...s.equipment, eq] }));
  },

  removeEquipment: (id, opts) => {
    if (opts?._source !== 'remote') get()._pushHistory();
    set((s) => ({
      equipment: s.equipment.filter(e => e.id !== id),
      pipeSegments: s.pipeSegments.filter(p => p.from_equipment_id !== id && p.to_equipment_id !== id),
      selectedId: s.selectedId === id ? null : s.selectedId,
    }));
  },

  updateEquipmentPosition: (id, pos) => {
    const s = get();
    if (!s._dragSnapshotTaken) {
      s._pushHistory();
      set({ _dragSnapshotTaken: true });
    }
    set((s2) => ({
      equipment: s2.equipment.map(e => e.id === id ? { ...e, position: pos } : e),
    }));
  },

  addPipeSegment: (ps, opts) => {
    if (opts?._source !== 'remote') get()._pushHistory();
    set((s) => ({ pipeSegments: [...s.pipeSegments, ps] }));
  },

  removePipeSegment: (id, opts) => {
    if (opts?._source !== 'remote') get()._pushHistory();
    set((s) => ({
      pipeSegments: s.pipeSegments.filter(p => p.id !== id),
      selectedId: s.selectedId === id ? null : s.selectedId,
    }));
  },

  setSelection: (id) => set({ selectedId: id, _dragSnapshotTaken: false }),
}));
