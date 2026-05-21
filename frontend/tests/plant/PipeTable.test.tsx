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
    expect(screen.getByText(/暂无管段/)).toBeDefined();
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
