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
    expect(screen.getByText('Edge Devices')).toBeDefined();
  });

  it('renders stats cards with counts', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockEdges),
    } as Response);
    renderPage();
    // Use getAllByText because labels also appear in <select> options and status badges
    await screen.findByText('Edge Devices');
    expect(screen.getAllByText('Online').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Offline').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Warning').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Total')).toBeDefined();
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
