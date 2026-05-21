import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PlantBuilder from '../../src/pages/PlantBuilder';
import { usePlantStore } from '../../src/plant/store';

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
  // Reset store state between tests to avoid state leakage
  usePlantStore.setState({
    plantId: null,
    plantName: '',
    equipment: [],
    pipeSegments: [],
    selectedId: null,
  });
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

  it('shows plant name when fetching by id', async () => {
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

  it('shows loading state while fetching plant', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            ok: true,
            json: () => Promise.resolve({
              id: 'plant-2', name: 'Loading Plant', equipment: [], pipe_segments: [],
            }),
          } as Response);
        }, 100);
      });
    });
    renderPage('/plant/plant-2');
    await waitFor(() => {
      expect(screen.getByText('加载制冷站...')).toBeDefined();
    });
  });

  it('shows equipment and pipe counts from store', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/plants/plant-3')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: 'plant-3',
            name: 'Count Plant',
            equipment: [
              { id: 'e1', name: 'Chiller', type_code: 'chiller', position: { x: 0, y: 0, z: 0 }, design_params: {} },
              { id: 'e2', name: 'Pump', type_code: 'pump', position: { x: 1, y: 1, z: 1 }, design_params: {} },
            ],
            pipe_segments: [
              { id: 'p1', from_equipment_id: 'e1', from_point_code: 'out', to_equipment_id: 'e2', to_point_code: 'in', diameter_mm: 100, length_m: 5, waypoints: [] },
            ],
          }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage('/plant/plant-3');
    await waitFor(() => {
      expect(screen.getByText('2 设备 | 1 管段')).toBeDefined();
    });
  });

  it('toggles equipment panel on button click', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ templates: [] }),
    } as Response);
    renderPage();
    // By default equipment panel should not be visible
    expect(screen.queryByText('设备库')).toBeNull();
    // Click add equipment button
    screen.getByText('添加设备').click();
    await waitFor(() => {
      expect(screen.getByText('设备库')).toBeDefined();
    });
  });

  it('renders all toolbar buttons', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ templates: [] }),
    } as Response);
    renderPage();
    expect(screen.getByText('添加设备')).toBeDefined();
    expect(screen.getByText('校验拓扑')).toBeDefined();
    expect(screen.getByText('保存')).toBeDefined();
  });

  it('renders property panel and pipe table sections', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ templates: [] }),
    } as Response);
    renderPage();
    expect(screen.getByText('属性')).toBeDefined();
    expect(screen.getByText('管段列表')).toBeDefined();
  });
});
