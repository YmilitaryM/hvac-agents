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
    expect(screen.getByText('显示点位')).toBeDefined();
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
