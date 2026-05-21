import { describe, it, expect, beforeEach } from 'vitest';
import { usePlantStore } from '../../src/plant/store';

function reset() {
  usePlantStore.setState({
    equipment: [],
    pipeSegments: [],
    selectedId: null,
    plantId: null,
    plantName: '',
    past: [],
    future: [],
    _dragSnapshotTaken: false,
  });
}

describe('PlantStore', () => {
  beforeEach(reset);

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
    usePlantStore.getState().setSelection('eq-1');
    usePlantStore.getState().removeEquipment('eq-1');
    expect(usePlantStore.getState().equipment).toHaveLength(1);
    expect(usePlantStore.getState().pipeSegments).toHaveLength(0);
    expect(usePlantStore.getState().selectedId).toBeNull();
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
        { id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} },
      ],
      pipe_segments: [],
    });
    expect(usePlantStore.getState().plantId).toBe('plant-1');
    expect(usePlantStore.getState().plantName).toBe('Test Plant');
    expect(usePlantStore.getState().equipment).toHaveLength(1);
    expect(usePlantStore.getState().selectedId).toBeNull();
  });
});

describe('Undo/Redo', () => {
  beforeEach(reset);

  it('undo reverts addEquipment', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    expect(usePlantStore.getState().equipment).toHaveLength(1);
    expect(usePlantStore.getState().past).toHaveLength(1); // snapshot of empty + the empty push

    usePlantStore.getState().undo();
    expect(usePlantStore.getState().equipment).toHaveLength(0);
    expect(usePlantStore.getState().past).toHaveLength(0);
  });

  it('redo restores undone addEquipment', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().undo();
    usePlantStore.getState().redo();
    expect(usePlantStore.getState().equipment).toHaveLength(1);
    expect(usePlantStore.getState().equipment[0].name).toBe('CH-1');
  });

  it('undo reverts removeEquipment', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    // Manually clear history but keep equipment
    usePlantStore.setState({ past: [], future: [] });
    usePlantStore.getState().removeEquipment('eq-1');
    expect(usePlantStore.getState().equipment).toHaveLength(0);

    usePlantStore.getState().undo();
    expect(usePlantStore.getState().equipment).toHaveLength(1);
  });

  it('undo reverts addPipeSegment', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().addEquipment({ id: 'eq-2', name: 'CT-1', type_code: 'cooling_tower', position: { x: 3, y: 0, z: 0 }, design_params: {} });
    reset();

    usePlantStore.getState().addPipeSegment({
      id: 'pipe-1', from_equipment_id: 'eq-1', from_point_code: 'cw_leaving_temp',
      to_equipment_id: 'eq-2', to_point_code: 'water_in_temp',
      diameter_mm: 200, length_m: 5, waypoints: [],
    });
    expect(usePlantStore.getState().pipeSegments).toHaveLength(1);

    usePlantStore.getState().undo();
    expect(usePlantStore.getState().pipeSegments).toHaveLength(0);
  });

  it('multiple undos work', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    reset();

    usePlantStore.getState().addEquipment({ id: 'eq-2', name: 'P-1', type_code: 'pump', position: { x: 2, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().addEquipment({ id: 'eq-3', name: 'CT-1', type_code: 'cooling_tower', position: { x: 4, y: 0, z: 0 }, design_params: {} });

    usePlantStore.getState().undo();
    expect(usePlantStore.getState().equipment).toHaveLength(1);
    expect(usePlantStore.getState().past).toHaveLength(1);

    usePlantStore.getState().undo();
    expect(usePlantStore.getState().equipment).toHaveLength(0);
    expect(usePlantStore.getState().past).toHaveLength(0);
  });

  it('new action after undo clears future', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    reset();

    usePlantStore.getState().addEquipment({ id: 'eq-2', name: 'P-1', type_code: 'pump', position: { x: 2, y: 0, z: 0 }, design_params: {} });
    usePlantStore.getState().undo();
    expect(usePlantStore.getState().future).toHaveLength(1);

    usePlantStore.getState().addEquipment({ id: 'eq-3', name: 'CT-1', type_code: 'cooling_tower', position: { x: 4, y: 0, z: 0 }, design_params: {} });
    expect(usePlantStore.getState().future).toHaveLength(0);
  });

  it('loadPlantData clears history', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    expect(usePlantStore.getState().past).toHaveLength(1);

    usePlantStore.getState().loadPlantData({ id: 'p1', name: 'P', equipment: [], pipe_segments: [] });
    expect(usePlantStore.getState().past).toHaveLength(0);
    expect(usePlantStore.getState().future).toHaveLength(0);
  });

  it('position update only creates one history entry per drag session', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} });
    reset();

    // Simulate a drag session: multiple position updates
    usePlantStore.getState().updateEquipmentPosition('eq-1', { x: 1, y: 0, z: 0 });
    usePlantStore.getState().updateEquipmentPosition('eq-1', { x: 2, y: 0, z: 0 });
    usePlantStore.getState().updateEquipmentPosition('eq-1', { x: 3, y: 1, z: 0 });

    // Only one history entry for the entire drag
    expect(usePlantStore.getState().past).toHaveLength(1);

    // Selection change resets the drag flag
    usePlantStore.getState().setSelection(null);
    usePlantStore.getState().addEquipment({ id: 'eq-2', name: 'P-1', type_code: 'pump', position: { x: 0, y: 0, z: 2 }, design_params: {} });

    // Now a new drag should create another history entry
    usePlantStore.getState().setSelection('eq-2');
    usePlantStore.getState().updateEquipmentPosition('eq-2', { x: 0, y: 0, z: 4 });
    expect(usePlantStore.getState().past).toHaveLength(3);
  });

  it('undo with no history is no-op', () => {
    usePlantStore.getState().undo();
    expect(usePlantStore.getState().equipment).toHaveLength(0);
    expect(usePlantStore.getState().past).toHaveLength(0);
  });

  it('redo with no future is no-op', () => {
    usePlantStore.getState().redo();
    expect(usePlantStore.getState().equipment).toHaveLength(0);
    expect(usePlantStore.getState().future).toHaveLength(0);
  });

  it('remote source does not push history', () => {
    usePlantStore.getState().addEquipment({ id: 'eq-1', name: 'CH-1', type_code: 'centrifugal_chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} }, { _source: 'remote' });
    expect(usePlantStore.getState().past).toHaveLength(0);
    expect(usePlantStore.getState().equipment).toHaveLength(1);
  });
});
