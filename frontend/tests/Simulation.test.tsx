import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Simulation from '../src/pages/Simulation';

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Simulation />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function setupDefaultMock() {
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
        json: () => Promise.resolve({ cop_history: [] }),
      } as Response);
    }
    if (urlStr.includes('/api/faults')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ active_faults: [] }),
      } as Response);
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('Simulation page', () => {
  it('renders page title "仿真控制"', async () => {
    setupDefaultMock();
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('仿真控制')).toBeDefined();
    });
  });

  it('renders plant ID input with default value "plant-1"', async () => {
    setupDefaultMock();
    renderPage();
    await waitFor(() => {
      expect(screen.getByDisplayValue('plant-1')).toBeDefined();
    });
  });

  it('renders "运行仿真" button (not disabled initially)', async () => {
    setupDefaultMock();
    renderPage();
    await waitFor(() => {
      const btn = screen.getByText('运行仿真');
      expect(btn).toBeDefined();
      expect((btn as HTMLButtonElement).disabled).toBe(false);
    });
  });

  it('shows "运行中..." when run button clicked', async () => {
    let resolveRun: (v: unknown) => void;
    const runPromise = new Promise(resolve => {
      resolveRun = resolve;
    });

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
          json: () => Promise.resolve({ cop_history: [] }),
        } as Response);
      }
      if (urlStr.includes('/api/faults')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ active_faults: [] }),
        } as Response);
      }
      if (urlStr.includes('/api/simulation/run')) {
        return runPromise.then(() => ({ ok: true, json: () => Promise.resolve({}) } as Response));
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('运行仿真')).toBeDefined();
    });

    fireEvent.click(screen.getByText('运行仿真'));

    await waitFor(() => {
      expect(screen.getByText('运行中...')).toBeDefined();
    });

    resolveRun!({});

    await waitFor(() => {
      expect(screen.getByText('运行仿真')).toBeDefined();
    });
  });

  it('renders 4 KPI cards with values', async () => {
    setupDefaultMock();
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
    expect(screen.getByText('室外温度 (°C)')).toBeDefined();
  });

  it('renders COP chart section heading "COP 趋势"', async () => {
    setupDefaultMock();
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('COP 趋势')).toBeDefined();
    });
  });

  it('renders fault injection panel with fault type select options', async () => {
    setupDefaultMock();
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('故障注入')).toBeDefined();
    });
    expect(screen.getByText('设备 ID')).toBeDefined();
    expect(screen.getByText('故障类型')).toBeDefined();
    const select = screen.getByRole('combobox');
    expect(select).toBeDefined();
    expect(screen.getByText('结垢')).toBeDefined();
    expect(screen.getByText('喘振')).toBeDefined();
    expect(screen.getByText('传感器故障')).toBeDefined();
    expect(screen.getByText('制冷剂泄漏')).toBeDefined();
    expect(screen.getByText('阀门卡涩')).toBeDefined();
  });

  it('renders severity slider', async () => {
    setupDefaultMock();
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/严重程度/)).toBeDefined();
    });
    const slider = screen.getByRole('slider');
    expect(slider).toBeDefined();
    expect((slider as HTMLInputElement).type).toBe('range');
  });

  it('renders "注入故障" button', async () => {
    setupDefaultMock();
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('注入故障')).toBeDefined();
    });
  });

  it('renders What-if scenario builder with default scenarios', async () => {
    setupDefaultMock();
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('What-if 场景对比')).toBeDefined();
    });
    expect(screen.getByText(/baseline/)).toBeDefined();
    expect(screen.getByText(/optimized/)).toBeDefined();
    expect(screen.getByText(/offset: 0/)).toBeDefined();
    expect(screen.getByText(/offset: 1/)).toBeDefined();
  });

  it('shows "活跃故障" when faults are returned from API', async () => {
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
          json: () => Promise.resolve({ cop_history: [] }),
        } as Response);
      }
      if (urlStr.includes('/api/faults')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ active_faults: [{ fault_type: 'fouling' }] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/活跃故障/)).toBeDefined();
    });
    expect(screen.getByText(/fouling/)).toBeDefined();
  });

  it('can add a new what-if scenario (type name, click 添加)', async () => {
    setupDefaultMock();
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('What-if 场景对比')).toBeDefined();
    });

    const nameInput = screen.getByPlaceholderText('场景名称');
    expect(nameInput).toBeDefined();

    fireEvent.change(nameInput, { target: { value: 'summer-peak' } });

    const addButton = screen.getByText('添加');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText(/summer-peak/)).toBeDefined();
    });
  });
});
