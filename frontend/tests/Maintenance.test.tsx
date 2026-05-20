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
    expect(screen.getByText('Predictive Maintenance')).toBeDefined();
  });

  it('renders health overview cards', () => {
    renderPage();
    expect(screen.getByText('Healthy')).toBeDefined();
    expect(screen.getByText('Degrading')).toBeDefined();
    expect(screen.getByText('Critical')).toBeDefined();
  });

  it('renders evaluation and prediction panels', () => {
    renderPage();
    expect(screen.getByText('Degradation Evaluation')).toBeDefined();
    expect(screen.getByText('Failure Prediction')).toBeDefined();
  });

  it('renders Run Evaluation and Predict Failure buttons', () => {
    renderPage();
    expect(screen.getByText('Run Evaluation')).toBeDefined();
    expect(screen.getByText('Predict Failure')).toBeDefined();
  });
});
