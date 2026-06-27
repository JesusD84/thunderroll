import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Inbox } from 'lucide-react';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';

describe('ErrorState', () => {
  it('renders the message with an alert role', () => {
    render(<ErrorState message="Algo salió mal" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Algo salió mal')).toBeInTheDocument();
  });

  it('renders a retry button when onRetry is provided', async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="boom" onRetry={onRetry} />);
    await userEvent.click(screen.getByRole('button', { name: /Reintentar/ }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('omits the retry button when onRetry is not provided', () => {
    render(<ErrorState message="boom" />);
    expect(screen.queryByRole('button', { name: /Reintentar/ })).not.toBeInTheDocument();
  });
});

describe('EmptyState', () => {
  it('renders title, description and action', () => {
    render(
      <EmptyState
        icon={Inbox}
        title="Sin datos"
        description="Aún no hay nada aquí"
        action={<button>Crear</button>}
      />,
    );
    expect(screen.getByText('Sin datos')).toBeInTheDocument();
    expect(screen.getByText('Aún no hay nada aquí')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Crear' })).toBeInTheDocument();
  });
});

describe('LoadingState', () => {
  it('exposes a status role with an accessible label', () => {
    render(<LoadingState rows={2} label="Cargando datos..." />);
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('Cargando datos...')).toBeInTheDocument();
  });
});
