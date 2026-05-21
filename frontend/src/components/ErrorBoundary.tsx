import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error) => ReactNode);
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo.componentStack);
  }

  handleRetry = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        if (typeof this.props.fallback === 'function') {
          return (this.props.fallback as (error: Error) => ReactNode)(this.state.error!);
        }
        return this.props.fallback;
      }

      return (
        <div className="max-w-md mx-auto mt-20 p-6 rounded-lg bg-slate-800 border border-slate-700">
          <div className="text-4xl text-red-400 mb-4">{'⚠️'}</div>
          <h2 className="text-lg font-bold text-slate-200 mb-2">页面出现错误</h2>
          <p className="text-sm text-slate-400 mb-4">
            应用程序遇到了意外错误，请尝试刷新页面
          </p>
          {this.state.error && (
            <pre className="text-xs text-red-400 bg-slate-900 p-3 rounded overflow-auto max-h-40 mb-4">
              {this.state.error.message}
              {this.state.error.stack ? `\n\n${this.state.error.stack}` : ''}
            </pre>
          )}
          <button
            onClick={this.handleRetry}
            className="bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2 rounded"
          >
            重新加载
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
