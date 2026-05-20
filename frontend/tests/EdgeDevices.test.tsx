import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import EdgeDevices from '../src/pages/EdgeDevices';

const mockEdges = {
  edges: [
    { edge_id: 'edge-01', plant_id: 'plant-a', mode: 'full', status: 'online', last_heartbeat: new Date().toISOString(), version: '1.0.0', registered_at: '2026-01-01T00:00:00Z' },
    { edge_id: 'edge-02', plant_id: 'plant-b', mode: 'acquisition', status: 'offline', last_heartbeat: null, version: '0.9.0', registered_at: '2026-01-02T00:00:00Z' },
    { edge_id: 'edge-03', plant_id: 'plant-a', mode: 'control', status: 'warning', last_heartbeat: new Date(Date.now() - 120000).toISOString(), version: '1.1.0', registered_at: '2026-01-03T00:00:00Z' },
  ],
};

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EdgeDevices />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('EdgeDevices page', () => {
  it('renders the page title', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEdges),
    } as Response);
    renderPage();
    expect(screen.getByText('边缘设备')).toBeDefined();
  });

  it('renders stats cards with counts', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEdges),
    } as Response);
    renderPage();
    await screen.findByText('边缘设备');
    expect(screen.getAllByText('在线').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('离线').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('告警').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('总计')).toBeDefined();
  });

  it('renders device table with edge IDs', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEdges),
    } as Response);
    renderPage();
    expect(await screen.findByText('edge-01')).toBeDefined();
    expect(screen.getByText('edge-02')).toBeDefined();
    expect(screen.getByText('edge-03')).toBeDefined();
  });
});
