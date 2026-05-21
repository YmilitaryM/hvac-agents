import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePipeConnection } from '../../src/plant/interaction/usePipeConnection';
import { usePlantStore } from '../../src/plant/store';

beforeEach(() => {
  usePlantStore.setState({
    equipment: [
      {
        id: 'eq-a',
        name: '冷水机组',
        type_code: 'centrifugal_chiller',
        position: { x: 0, y: 0, z: 0 },
        design_params: {},
      },
      {
        id: 'eq-b',
        name: '水泵',
        type_code: 'pump',
        position: { x: 6, y: 0, z: 0 },
        design_params: {},
      },
    ],
    pipeSegments: [],
    selectedId: null,
    plantId: null,
    plantName: '',
  });
});

describe('usePipeConnection', () => {
  it('starts a connection when startConnection is called with valid equipment', () => {
    const { result } = renderHook(() => usePipeConnection());

    act(() => {
      result.current.startConnection('eq-a', 'chw_supply_temp');
    });

    expect(result.current.activeConnection).toEqual({
      fromEquipmentId: 'eq-a',
      fromPointCode: 'chw_supply_temp',
      startPos: { x: 0, y: 0, z: 0 },
    });
  });

  it('does not start connection for non-existent equipment', () => {
    const { result } = renderHook(() => usePipeConnection());

    act(() => {
      result.current.startConnection('ghost', 'point');
    });

    expect(result.current.activeConnection).toBeNull();
  });

  it('completes connection and adds pipe segment to store', () => {
    const { result } = renderHook(() => usePipeConnection());

    act(() => {
      result.current.startConnection('eq-a', 'chw_supply_temp');
    });
    act(() => {
      result.current.completeConnection('eq-b', 'outlet_pressure');
    });

    expect(result.current.activeConnection).toBeNull();
    const pipes = usePlantStore.getState().pipeSegments;
    expect(pipes).toHaveLength(1);
    expect(pipes[0].from_equipment_id).toBe('eq-a');
    expect(pipes[0].from_point_code).toBe('chw_supply_temp');
    expect(pipes[0].to_equipment_id).toBe('eq-b');
    expect(pipes[0].to_point_code).toBe('outlet_pressure');
    expect(pipes[0].diameter_mm).toBe(200);
    expect(pipes[0].length_m).toBeGreaterThan(0);
  });

  it('cancels connection when same equipment is clicked twice', () => {
    const { result } = renderHook(() => usePipeConnection());

    act(() => {
      result.current.startConnection('eq-a', 'point-1');
    });
    act(() => {
      result.current.completeConnection('eq-a', 'point-2');
    });

    expect(result.current.activeConnection).toBeNull();
    expect(usePlantStore.getState().pipeSegments).toHaveLength(0);
  });

  it('cancels connection via cancelConnection', () => {
    const { result } = renderHook(() => usePipeConnection());

    act(() => {
      result.current.startConnection('eq-a', 'chw_supply_temp');
    });
    act(() => {
      result.current.cancelConnection();
    });

    expect(result.current.activeConnection).toBeNull();
    expect(usePlantStore.getState().pipeSegments).toHaveLength(0);
  });

  it('does nothing when completeConnection called without active connection', () => {
    const { result } = renderHook(() => usePipeConnection());

    act(() => {
      result.current.completeConnection('eq-b', 'point');
    });

    expect(usePlantStore.getState().pipeSegments).toHaveLength(0);
  });

  it('clears connection when target equipment does not exist', () => {
    const { result } = renderHook(() => usePipeConnection());

    act(() => {
      result.current.startConnection('eq-a', 'point');
    });
    act(() => {
      result.current.completeConnection('ghost', 'point');
    });

    expect(result.current.activeConnection).toBeNull();
    expect(usePlantStore.getState().pipeSegments).toHaveLength(0);
  });
});
