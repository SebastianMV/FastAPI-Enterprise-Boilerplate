/**
 * Unit tests for ErrorBoundary component.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';

// Suppress console.error from intentional error throws
const originalConsoleError = console.error;

describe('ErrorBoundary', () => {
  beforeEach(() => {
    console.error = vi.fn();
  });

  afterAll(() => {
    console.error = originalConsoleError;
  });

  // A component that throws an error
  function ThrowError({ shouldThrow = true }: { shouldThrow?: boolean }) {
    if (shouldThrow) throw new Error('Test error');
    return <div>No error</div>;
  }

  it('should render children when no error', () => {
    render(
      <ErrorBoundary>
        <div>All good</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('All good')).toBeInTheDocument();
  });

  it('should render error UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/unexpected error/i)).toBeInTheDocument();
  });

  it('should show reload and go home buttons', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    expect(screen.getByText('Reload page')).toBeInTheDocument();
    expect(screen.getByText('Go home')).toBeInTheDocument();
  });

  it('should call window.location.reload on reload button click', () => {
    const originalLocation = window.location;
    const reloadMock = vi.fn();
    const mockLocation = { ...originalLocation, reload: reloadMock } as unknown as Location;
    Object.defineProperty(window, 'location', { value: mockLocation, writable: true });

    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    fireEvent.click(screen.getByText('Reload page'));
    expect(reloadMock).toHaveBeenCalled();
    Object.defineProperty(window, 'location', { value: originalLocation, writable: true });
  });

  it('should redirect to home on go home button click', () => {
    const originalLocation = window.location;
    const mockLocation = { ...originalLocation, href: '' } as Location;
    Object.defineProperty(window, 'location', { value: mockLocation, writable: true });

    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    fireEvent.click(screen.getByText('Go home'));
    expect(mockLocation.href).toBe('/');
    Object.defineProperty(window, 'location', { value: originalLocation, writable: true });
  });

  it('should render custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowError />
      </ErrorBoundary>
    );
    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
  });

  it('should log error to console', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );
    expect(console.error).toHaveBeenCalled();
  });
});
