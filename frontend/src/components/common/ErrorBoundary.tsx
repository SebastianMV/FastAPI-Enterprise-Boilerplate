import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import i18n from '../../i18n';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional fallback UI. If not provided, the default error page is shown. */
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * React Error Boundary — catches unhandled errors in the component tree.
 *
 * Wraps routes so that a single broken page never crashes the entire app.
 * Provides user-friendly recovery options (reload / go home).
 */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Log to console in development only; in production this should report
    // to Sentry, LogRocket, etc.
    if (import.meta.env.DEV) {
      console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
    }
  }

  private handleReload = (): void => {
    window.location.reload();
  };

  private handleGoHome = (): void => {
    window.location.href = '/';
  };

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    const isDev = import.meta.env.DEV && import.meta.env.MODE !== 'production';

    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-900 px-4">
        <div className="max-w-lg w-full text-center space-y-6">
          {/* Icon */}
          <div className="flex justify-center">
            <div className="rounded-full bg-red-100 dark:bg-red-900/30 p-4">
              <AlertTriangle className="w-10 h-10 text-red-600 dark:text-red-400" />
            </div>
          </div>

          {/* Message */}
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
              {i18n.t('errorBoundary.title', 'Something went wrong')}
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              {i18n.t('errorBoundary.description', 'An unexpected error occurred. You can try reloading the page or going back to the home page.')}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={this.handleReload}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              {i18n.t('errorBoundary.reload', 'Reload page')}
            </button>
            <button
              onClick={this.handleGoHome}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            >
              <Home className="w-4 h-4" />
              {i18n.t('errorBoundary.goHome', 'Go home')}
            </button>
          </div>

          {/* Dev-only error details */}
          {isDev && this.state.error && (
            <details className="mt-6 text-left rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
              <summary className="cursor-pointer text-sm font-medium text-slate-700 dark:text-slate-300">
                {i18n.t('errorBoundary.details', 'Error details (dev only)')}
              </summary>
              <pre className="mt-3 overflow-auto rounded bg-slate-100 dark:bg-slate-900 p-3 text-xs text-red-700 dark:text-red-400 whitespace-pre-wrap">
                {this.state.error.toString()}
                {this.state.errorInfo?.componentStack}
              </pre>
              <button
                onClick={this.handleReset}
                className="mt-3 text-xs text-primary-600 hover:underline"
              >
                {i18n.t('errorBoundary.recover', 'Try to recover (reset boundary)')}
              </button>
            </details>
          )}
        </div>
      </div>
    );
  }
}
