import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary from '../src/components/ErrorBoundary';

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('ErrorBoundary', () => {
  it('renders children normally when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Hello</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText('Hello')).toBeDefined();
  });

  it('catches error and shows fallback UI', () => {
    const BuggyComponent = () => {
      throw new Error('test crash');
    };

    render(
      <ErrorBoundary>
        <BuggyComponent />
      </ErrorBoundary>,
    );

    expect(screen.getByText('页面出现错误')).toBeDefined();
    expect(screen.getByText('应用程序遇到了意外错误，请尝试刷新页面')).toBeDefined();
    expect(screen.getByText(/test crash/)).toBeDefined();
  });

  it('retry button exists and is clickable', () => {
    const BuggyComponent = () => {
      throw new Error('test crash');
    };

    render(
      <ErrorBoundary>
        <BuggyComponent />
      </ErrorBoundary>,
    );

    const retryButton = screen.getByText('重新加载');
    expect(retryButton).toBeDefined();
    fireEvent.click(retryButton);
  });

  it('renders custom fallback when provided as element', () => {
    const BuggyComponent = () => {
      throw new Error('test crash');
    };

    render(
      <ErrorBoundary fallback={<div>Custom Error UI</div>}>
        <BuggyComponent />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Custom Error UI')).toBeDefined();
  });

  it('renders custom fallback when provided as function', () => {
    const BuggyComponent = () => {
      throw new Error('test crash');
    };

    render(
      <ErrorBoundary fallback={(error) => <div>Error: {error.message}</div>}>
        <BuggyComponent />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Error: test crash')).toBeDefined();
  });
});
