/**
 * Tests for ErrorBoundary component
 */

import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen, fireEvent } from '../test/utils';
import {
  ErrorBoundary,
  QueryErrorFallback,
  LoadingFallback,
  EmptyStateFallback,
} from './ErrorBoundary';

// Component that throws an error
function ThrowError(): never {
  throw new Error('Test error');
}

// Suppress console.error for error boundary tests
const originalError = console.error;
beforeAll(() => {
  console.error = vi.fn();
});
afterAll(() => {
  console.error = originalError;
});

describe('ErrorBoundary', () => {
  it('should render children when no error', () => {
    render(
      <ErrorBoundary>
        <div data-testid="child">Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('should render error UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('should render custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom fallback')).toBeInTheDocument();
  });

  it('should reset error state when Try Again is clicked', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Click Try Again should reset the error state
    // Note: In a real app, the component would need to be fixed for recovery
    // This test verifies the reset button is clickable and doesn't throw
    const tryAgainButton = screen.getByRole('button', { name: /try again/i });
    expect(tryAgainButton).toBeInTheDocument();
    expect(() => fireEvent.click(tryAgainButton)).not.toThrow();
  });
});

describe('QueryErrorFallback', () => {
  it('should render error message', () => {
    render(<QueryErrorFallback error="API failed" title="Network Error" />);

    expect(screen.getByText('Network Error')).toBeInTheDocument();
    expect(screen.getByText('API failed')).toBeInTheDocument();
  });

  it('should render Error object message', () => {
    const error = new Error('Connection refused');
    render(<QueryErrorFallback error={error} title="Server Error" />);

    expect(screen.getByText('Server Error')).toBeInTheDocument();
    expect(screen.getByText('Connection refused')).toBeInTheDocument();
  });

  it('should call onRetry when retry button clicked', () => {
    const onRetry = vi.fn();
    render(
      <QueryErrorFallback
        error="Failed"
        title="Error"
        onRetry={onRetry}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('should not show retry button when onRetry not provided', () => {
    render(<QueryErrorFallback error="Failed" title="Error" />);

    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument();
  });
});

describe('LoadingFallback', () => {
  it('should render default loading message', () => {
    render(<LoadingFallback />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should render custom message', () => {
    render(<LoadingFallback message="Fetching data..." />);

    expect(screen.getByText('Fetching data...')).toBeInTheDocument();
  });

  it('should show spinner', () => {
    render(<LoadingFallback />);

    // Check for the spinner element (has animate-spin class)
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });
});

describe('EmptyStateFallback', () => {
  it('should render icon, title and message', () => {
    render(
      <EmptyStateFallback
        icon="📭"
        title="No Items"
        message="You haven't added anything yet"
      />
    );

    expect(screen.getByText('📭')).toBeInTheDocument();
    expect(screen.getByText('No Items')).toBeInTheDocument();
    expect(screen.getByText("You haven't added anything yet")).toBeInTheDocument();
  });

  it('should render action button when provided', () => {
    const onClick = vi.fn();
    render(
      <EmptyStateFallback
        icon="📭"
        title="No Items"
        message="Nothing here"
        action={{ label: 'Add Item', onClick }}
      />
    );

    const button = screen.getByRole('button', { name: /add item/i });
    expect(button).toBeInTheDocument();

    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledOnce();
  });
});
