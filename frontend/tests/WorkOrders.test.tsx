import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import WorkOrders from '../src/pages/WorkOrders';

const mockOrders = {
  work_orders: [
    { id: 'wo-001', edge_id: 'edge-01', equipment_id: 'chiller-1', severity: 'critical', title: 'Compressor failure', description: 'Noise detected', status: 'open', assigned_to: null, source: 'auto', created_at: '2026-05-20T08:00:00Z', updated_at: '2026-05-20T08:00:00Z', resolved_at: null },
    { id: 'wo-002', edge_id: 'edge-02', equipment_id: 'pump-3', severity: 'warning', title: 'Bearing wear', description: 'Vibration high', status: 'acknowledged', assigned_to: 'tech-1', source: 'manual', created_at: '2026-05-20T07:00:00Z', updated_at: '2026-05-20T09:00:00Z', resolved_at: null },
    { id: 'wo-003', edge_id: 'edge-01', equipment_id: 'tower-2', severity: 'info', title: 'Routine check', description: '', status: 'resolved', assigned_to: null, source: 'auto', created_at: '2026-05-19T12:00:00Z', updated_at: '2026-05-20T10:00:00Z', resolved_at: '2026-05-20T10:00:00Z' },
  ],
};

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <WorkOrders />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('WorkOrders page', () => {
  it('renders the page title', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    } as Response);
    renderPage();
    expect(screen.getByText('Work Orders')).toBeDefined();
  });

  it('renders status count cards', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    } as Response);
    renderPage();
    // Use getAllByText since labels also appear in the filter <select> options
    await screen.findByText('Work Orders');
    expect(screen.getAllByText('Open').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Acknowledged').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Resolved').length).toBeGreaterThanOrEqual(1);
  });

  it('renders work order titles in table', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    } as Response);
    renderPage();
    expect(await screen.findByText('Compressor failure')).toBeDefined();
    expect(screen.getByText('Bearing wear')).toBeDefined();
    expect(screen.getByText('Routine check')).toBeDefined();
  });
});
