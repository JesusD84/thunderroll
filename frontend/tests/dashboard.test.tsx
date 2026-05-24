import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from '@/app/page';

const mockFetch = vi.fn();
let mockSession: any = { user: { name: 'Admin' }, accessToken: 'token123' };

vi.stubGlobal('fetch', mockFetch);

vi.mock('next-auth/react', () => ({
  useSession: () => ({ data: mockSession }),
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockSession = { user: { name: 'Admin' }, accessToken: 'token123' };
  mockFetch.mockReset();
});

const mockDashboardData = {
  units: { total: 50, available: 30, sold: 12, in_transit: 5 },
  locations: { total: 3 },
  transfers: { active: 2 },
  recent_transfers: [
    {
      id: 1,
      unit_engine: 'ENG001',
      origin_location: 'Almacén Central',
      destination_location: 'Taller Norte',
      dispatched_by: 'Admin',
      received_by: null,
      status: 'IN_TRANSIT',
      dispatched_at: '2025-01-15T10:00:00Z',
      received_at: null,
    },
  ],
  inventory_by_location: [
    { location: 'Almacén Central', count: 25 },
    { location: 'Taller Norte', count: 15 },
    { location: 'Sucursal Sur', count: 10 },
  ],
  inventory_by_brand: [
    { brand: 'Toyota', count: 20 },
    { brand: 'Honda', count: 15 },
  ],
  sales_by_month: [],
  recent_imports: [],
};

describe('DashboardPage', () => {
  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    render(<DashboardPage />);
    expect(screen.getByText('Cargando dashboard...')).toBeInTheDocument();
  });

  it('shows error state on fetch failure', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    render(<DashboardPage />);
    expect(await screen.findByText(/Error cargando dashboard/)).toBeInTheDocument();
  });

  it('does not fetch without accessToken', () => {
    mockSession = { user: { name: 'Admin' } };
    render(<DashboardPage />);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('renders KPI stats cards', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => mockDashboardData });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('50')).toBeInTheDocument();
    });
    expect(screen.getByText('Total de Unidades')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('Disponibles')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('En Tránsito')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Vendidas')).toBeInTheDocument();
  });

  it('renders inventory by location', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => mockDashboardData });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Distribución por Ubicación')).toBeInTheDocument();
    });
    expect(screen.getByText('Almacén Central')).toBeInTheDocument();
    expect(screen.getByText('Taller Norte')).toBeInTheDocument();
    expect(screen.getByText('Sucursal Sur')).toBeInTheDocument();
  });

  it('renders inventory by brand', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => mockDashboardData });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Inventario por Marca')).toBeInTheDocument();
    });
    expect(screen.getByText('Toyota')).toBeInTheDocument();
    expect(screen.getByText('Honda')).toBeInTheDocument();
  });

  it('renders alerts section', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => mockDashboardData });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Alertas')).toBeInTheDocument();
    });
    expect(screen.getByText('Unidades en Tránsito')).toBeInTheDocument();
    expect(screen.getByText('Transferencias Activas')).toBeInTheDocument();
  });

  it('renders recent activity', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => mockDashboardData });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Actividad Reciente')).toBeInTheDocument();
    });
    expect(screen.getByText(/ENG001/)).toBeInTheDocument();
  });

  it('renders quick action buttons', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => mockDashboardData });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Acciones Rápidas')).toBeInTheDocument();
    });
    expect(screen.getByText('Agregar Unidad')).toBeInTheDocument();
    expect(screen.getByText('Importar Excel')).toBeInTheDocument();
    expect(screen.getByText('Nueva Transferencia')).toBeInTheDocument();
    expect(screen.getByText('Generar Reporte')).toBeInTheDocument();
  });

  it('shows empty state when no alerts', async () => {
    const noAlertsData = {
      ...mockDashboardData,
      units: { total: 10, available: 10, sold: 0, in_transit: 0 },
      transfers: { active: 0 },
    };
    mockFetch.mockResolvedValue({ ok: true, json: () => noAlertsData });
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Todo en orden — sin alertas pendientes')).toBeInTheDocument();
    });
  });
});