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
    expect(screen.getByText('工单管理')).toBeDefined();
  });

  it('renders status count cards', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    } as Response);
    renderPage();
    await screen.findByText('工单管理');
    expect(screen.getAllByText('待处理').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('已确认').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('已解决').length).toBeGreaterThanOrEqual(1);
  });

  it('renders work order titles in table', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    } as Response);
    renderPage();
    const compressor = await screen.findAllByText('Compressor failure');
    expect(compressor.length).toBeGreaterThan(0);
    expect(screen.getAllByText('Bearing wear').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Routine check').length).toBeGreaterThan(0);
  });
});
