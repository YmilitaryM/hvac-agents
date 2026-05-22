import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../src/pages/Dashboard';

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('Dashboard page', () => {
  it('renders page title', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    } as Response);
    renderPage();
    expect(screen.getByText('系统总览')).toBeDefined();
  });

  it('renders 4 KPI cards with values from KPI data', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            kpi: { system_cop: 4.5, total_cooling_load_rt: 350, total_power_kw: 280, outdoor_wb_temp: 26.5 },
          }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ cop_history: [], chillers: {}, chw_pumps: {}, cooling_towers: {} }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ alerts: [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('4.50')).toBeDefined();
    });
    expect(screen.getByText('350')).toBeDefined();
    expect(screen.getByText('280')).toBeDefined();
    expect(screen.getByText('26.5')).toBeDefined();
    expect(screen.getByText('系统 COP')).toBeDefined();
    expect(screen.getByText('冷负荷 (RT)')).toBeDefined();
    expect(screen.getByText('总功率 (kW)')).toBeDefined();
    expect(screen.getByText('室外湿球温度 (°C)')).toBeDefined();
  });

  it('shows KPI fallback values -- when KPI data is missing', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ cop_history: [], chillers: {}, chw_pumps: {}, cooling_towers: {} }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ alerts: [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      const dashes = screen.getAllByText('--');
      expect(dashes.length).toBeGreaterThanOrEqual(4);
    });
  });

  it('renders chart container heading', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ kpi: { system_cop: 4.5, total_cooling_load_rt: 350, total_power_kw: 280, outdoor_wb_temp: 26.5 } }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            cop_history: [{ time: '00:00', cop: 4.2, load: 280, power: 230 }],
            chillers: {}, chw_pumps: {}, cooling_towers: {},
          }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ alerts: [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('COP / 负荷 / 功率 趋势')).toBeDefined();
    });
  });

  it('renders equipment status section with chiller data', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ kpi: { system_cop: 4.5, total_cooling_load_rt: 350, total_power_kw: 280, outdoor_wb_temp: 26.5 } }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            cop_history: [],
            chillers: { 'ch-1': { name: '冷机A', plr: 0.75, cop: 4.8, power_kw: 250, status: 'running' } },
            chw_pumps: {},
            cooling_towers: {},
          }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ alerts: [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('冷机A')).toBeDefined();
    });
    expect(screen.getByText(/PLR: 75%/)).toBeDefined();
    expect(screen.getByText(/COP: 4.8/)).toBeDefined();
    expect(screen.getByText(/功率: 250/)).toBeDefined();
  });

  it('shows equipment empty state when no equipment', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ kpi: { system_cop: 4.5, total_cooling_load_rt: 350, total_power_kw: 280, outdoor_wb_temp: 26.5 } }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            cop_history: [],
            chillers: {},
            chw_pumps: {},
            cooling_towers: {},
          }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ alerts: [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('等待仿真数据...')).toBeDefined();
    });
  });

  it('renders recent alerts with severity badge and message', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ kpi: { system_cop: 4.5, total_cooling_load_rt: 350, total_power_kw: 280, outdoor_wb_temp: 26.5 } }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ cop_history: [], chillers: {}, chw_pumps: {}, cooling_towers: {} }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            alerts: [
              { id: 'a1', severity: 'critical', message: '冷机故障', rule_name: 'chiller_fault', timestamp: '2026-01-01T00:00:00Z' },
              { id: 'a2', severity: 'warning', message: '水泵异常振动', rule_name: 'pump_vibration', timestamp: '2026-01-01T01:00:00Z' },
            ],
          }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('冷机故障')).toBeDefined();
    });
    expect(screen.getByText('critical')).toBeDefined();
    expect(screen.getByText('水泵异常振动')).toBeDefined();
    expect(screen.getByText('warning')).toBeDefined();
  });

  it('shows alerts empty state', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ kpi: { system_cop: 4.5, total_cooling_load_rt: 350, total_power_kw: 280, outdoor_wb_temp: 26.5 } }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ cop_history: [], chillers: {}, chw_pumps: {}, cooling_towers: {} }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ alerts: [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('无未确认告警')).toBeDefined();
    });
  });

  it('shows error banner when KPI query fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.reject(new Error('KPI fetch failed'));
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ cop_history: [], chillers: {}, chw_pumps: {}, cooling_towers: {} }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ alerts: [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/部分数据加载失败/)).toBeDefined();
    });
  });

  it('shows error banner when snapshot query fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url: RequestInfo | URL) => {
      const urlStr = typeof url === 'string' ? url : url.toString();
      if (urlStr.includes('/api/monitoring/kpi')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ kpi: { system_cop: 4.5, total_cooling_load_rt: 350, total_power_kw: 280, outdoor_wb_temp: 26.5 } }),
        } as Response);
      }
      if (urlStr.includes('/api/monitoring/snapshot')) {
        return Promise.reject(new Error('Snapshot fetch failed'));
      }
      if (urlStr.includes('/api/monitoring/alerts')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ alerts: [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/部分数据加载失败/)).toBeDefined();
    });
  });
});
