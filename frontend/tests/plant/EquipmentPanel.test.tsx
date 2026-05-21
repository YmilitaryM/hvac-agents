import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
    screen.getByText('CH-1').click();
    const store = usePlantStore.getState();
    expect(store.equipment).toHaveLength(1);
    expect(store.equipment[0].name).toBe('CH-1');
  });
});
