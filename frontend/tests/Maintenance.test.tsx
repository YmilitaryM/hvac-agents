import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Maintenance from '../src/pages/Maintenance';

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Maintenance />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('Maintenance page', () => {
  it('renders the page title', () => {
    renderPage();
    expect(screen.getByText('预测维护')).toBeDefined();
  });

  it('renders health overview cards', () => {
    renderPage();
    expect(screen.getByText('健康')).toBeDefined();
    expect(screen.getByText('退化中')).toBeDefined();
    expect(screen.getByText('严重')).toBeDefined();
  });

  it('renders evaluation and prediction panels', () => {
    renderPage();
    expect(screen.getByText('退化评估')).toBeDefined();
    expect(screen.getByText('故障预测')).toBeDefined();
  });

  it('renders evaluation and predict buttons', () => {
    renderPage();
    expect(screen.getByText('运行评估')).toBeDefined();
    expect(screen.getByText('预测故障')).toBeDefined();
  });
});
