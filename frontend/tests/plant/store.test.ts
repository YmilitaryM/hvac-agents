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
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().addEquipment({ id: 'eq-2', name: 'P-1', type_code: 'pump', position: { x: 2, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().addPipeSegment({
      id: 'pipe-1', from_equipment_id: 'eq-1', from_point_code: 'cw_leaving_temp',
      to_equipment_id: 'eq-2', to_point_code: 'inlet_pressure',
      diameter_mm: 200, length_m: 5, waypoints: [],
    });
    usePlantStore.getState().removeEquipment('eq-1');
    expect(usePlantStore.getState().equipment).toHaveLength(1);
    expect(usePlantStore.getState().pipeSegments).toHaveLength(0);
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
