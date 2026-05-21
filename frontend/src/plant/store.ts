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
