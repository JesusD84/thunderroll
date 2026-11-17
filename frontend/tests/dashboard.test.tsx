import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from '@/app/page';
import { API_BASE } from '@/lib/api';
import { mockResponse } from './mocks/response';

const mockFetch = vi.fn();
// The session no longer carries an access token: the credential lives in the
// encrypted cookie and the server-side proxy adds the Authorization header.
let mockSession: any = { user: { name: 'Admin' } };

vi.stubGlobal('fetch', mockFetch);

vi.mock('next-auth/react', () => ({
  useSession: () => ({ data: mockSession }),
  getSession: () => Promise.resolve(null),
  signOut: vi.fn(),
}));

const mockReplace = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockSession = { user: { name: 'Admin' } };
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
  it('redirects operator to /units without fetching the dashboard', () => {
    mockSession = { user: { name: 'Op', role: 'operator' } };
    mockFetch.mockResolvedValue(mockResponse(mockDashboardData));
    render(<DashboardPage />);
    expect(mockReplace).toHaveBeenCalledWith('/units');
    expect(mockFetch).not.toHaveBeenCalled();
    expect(screen.queryByText('Cargando dashboard...')).not.toBeInTheDocument();
  });

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

  it('does not fetch when there is no session', () => {
    mockSession = null;
    render(<DashboardPage />);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('fetches the dashboard with a session that has no accessToken', async () => {
    mockSession = { user: { name: 'Admin' } };
    mockFetch.mockResolvedValue(mockResponse(mockDashboardData));
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Total de Unidades')).toBeInTheDocument();
    });
    // The call goes to the server-side proxy and carries no credential.
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch.mock.calls[0][0]).toBe(`${API_BASE}/api/v1/reports/dashboard`);
    expect(new Headers(mockFetch.mock.calls[0][1]?.headers).get('Authorization')).toBeNull();
  });

  it('renders KPI stats cards', async () => {
    mockFetch.mockResolvedValue(mockResponse(mockDashboardData));
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
    mockFetch.mockResolvedValue(mockResponse(mockDashboardData));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Distribución por Ubicación')).toBeInTheDocument();
    });
    expect(screen.getByText('Almacén Central')).toBeInTheDocument();
    expect(screen.getByText('Taller Norte')).toBeInTheDocument();
    expect(screen.getByText('Sucursal Sur')).toBeInTheDocument();
  });

  it('renders inventory by brand', async () => {
    mockFetch.mockResolvedValue(mockResponse(mockDashboardData));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Inventario por Marca')).toBeInTheDocument();
    });
    expect(screen.getByText('Toyota')).toBeInTheDocument();
    expect(screen.getByText('Honda')).toBeInTheDocument();
  });

  it('renders alerts section', async () => {
    mockFetch.mockResolvedValue(mockResponse(mockDashboardData));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Alertas')).toBeInTheDocument();
    });
    expect(screen.getByText('Unidades en Tránsito')).toBeInTheDocument();
    expect(screen.getByText('Transferencias Activas')).toBeInTheDocument();
  });

  it('renders recent activity', async () => {
    mockFetch.mockResolvedValue(mockResponse(mockDashboardData));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Actividad Reciente')).toBeInTheDocument();
    });
    expect(screen.getByText(/ENG001/)).toBeInTheDocument();
  });

  it('renders quick action buttons', async () => {
    mockFetch.mockResolvedValue(mockResponse(mockDashboardData));
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
    mockFetch.mockResolvedValue(mockResponse(noAlertsData));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Todo en orden — sin alertas pendientes')).toBeInTheDocument();
    });
  });
});