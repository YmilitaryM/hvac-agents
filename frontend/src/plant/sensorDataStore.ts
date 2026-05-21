import { create } from 'zustand';

export interface SensorReading {
  value: number | string;
  timestamp: number;
}

interface SensorDataState {
  readings: Record<string, SensorReading>; // key: "equipmentId:pointCode"
  updateReading: (equipmentId: string, pointCode: string, value: number | string) => void;
  clearReadings: () => void;
}

export const useSensorDataStore = create<SensorDataState>((set) => ({
  readings: {},
  updateReading: (equipmentId, pointCode, value) =>
    set(s => ({
      readings: {
        ...s.readings,
        [`${equipmentId}:${pointCode}`]: { value, timestamp: Date.now() },
      },
    })),
  clearReadings: () => set({ readings: {} }),
}));
