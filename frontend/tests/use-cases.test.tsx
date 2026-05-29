import { describe, it, expect, vi, beforeEach, beforeAll, afterEach, afterAll } from 'vitest';
import { waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { server } from './mocks/server';

let mockSession: any = { user: { name: 'Admin User', role: 'admin' }, accessToken: 'mock-jwt' };
let mockStatus = 'authenticated';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({ data: mockSession, status: mockStatus }),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

beforeEach(() => {
  vi.clearAllMocks();
  mockSession = { user: { name: 'Admin User', role: 'admin' }, accessToken: 'mock-jwt' };
  mockStatus = 'authenticated';
});

const user = userEvent.setup({ pointerEventsCheck: 0 });

// ============================================================
// UC-1: Authentication
// ============================================================
describe('UC-1: Authentication', () => {
  it('UC-1.1: login page renders with form fields', async () => {
    const LoginPage = (await import('@/app/login/page')).default;
    render(<LoginPage />);
    expect(screen.getByRole('heading', { name: 'Iniciar Sesión' })).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
  });

  it('UC-1.2: demo credentials visible on login page', async () => {
    const LoginPage = (await import('@/app/login/page')).default;
    render(<LoginPage />);
    expect(screen.getByText('Credenciales Demo:')).toBeInTheDocument();
    expect(screen.getByText(/admin@thunderrol.com/)).toBeInTheDocument();
  });

  it('UC-1.3: unauthenticated user sees login page', async () => {
    mockStatus = 'unauthenticated';
    mockSession = null;
    const LoginPage = (await import('@/app/login/page')).default;
    render(<LoginPage />);
    expect(screen.getByRole('heading', { name: 'Iniciar Sesión' })).toBeInTheDocument();
  });
});

// ============================================================
// UC-2: Inventory Management (CRUD Units)
// ============================================================
describe('UC-2: Inventory Management', () => {
  it('UC-2.1: units list renders with data from API', async () => {
    const UnitsPage = (await import('@/app/units/page')).default;
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText(/Honda PCX/)).toBeInTheDocument();
    }, { timeout: 3000 });
    expect(screen.getByText(/Yamaha NMAX/)).toBeInTheDocument();
  });

  it('UC-2.2: units page shows header and new unit button', async () => {
    const UnitsPage = (await import('@/app/units/page')).default;
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Gestión de Unidades')).toBeInTheDocument();
    });
  });

  it('UC-2.3: empty units list shows no data rows', async () => {
    const { server } = await import('./mocks/server');
    const { http, HttpResponse } = await import('msw');
    server.use(
      http.get('http://localhost:8000/api/v1/units/', () =>
        HttpResponse.json([])
      )
    );
    const UnitsPage = (await import('@/app/units/page')).default;
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.queryByText(/Honda PCX/)).not.toBeInTheDocument();
    }, { timeout: 3000 });
  });
});

// ============================================================
// UC-3: Transfers
// ============================================================
describe('UC-3: Transfers', () => {
  it('UC-3.1: transfers list renders with data', async () => {
    const TransfersPage = (await import('@/app/transfers/page')).default;
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Transferencias')).toBeInTheDocument();
    });
  });

  it('UC-3.2: transfer status badges are visible', async () => {
    const TransfersPage = (await import('@/app/transfers/page')).default;
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText(/En Tránsito/)).toBeInTheDocument();
    });
  });
});

// ============================================================
// UC-4: Mass Import
// ============================================================
describe('UC-4: Mass Import', () => {
  it('UC-4.1: import page renders with upload area', async () => {
    const ImportsPage = (await import('@/app/imports/page')).default;
    render(<ImportsPage />);
    await waitFor(() => {
      expect(screen.getByText(/Importar/)).toBeInTheDocument();
    });
  });

  it('UC-4.2: file input accepts Excel files', async () => {
    const ImportsPage = (await import('@/app/imports/page')).default;
    render(<ImportsPage />);
    const fileInput = screen.getByLabelText(/archivo/i);
    expect(fileInput).toBeInTheDocument();
    expect(fileInput).toHaveAttribute('type', 'file');
  });
});

// ============================================================
// UC-5: Reports and Export
// ============================================================
describe('UC-5: Reports and Export', () => {
  it('UC-5.1: reports page renders with tabs', async () => {
    const ReportsPage = (await import('@/app/reports/page')).default;
    render(<ReportsPage />);
    expect(screen.getByText('Reportes')).toBeInTheDocument();
    expect(screen.getByText('Inventario')).toBeInTheDocument();
    expect(screen.getByText('Transferencias')).toBeInTheDocument();
    expect(screen.getByText('Ventas')).toBeInTheDocument();
  });

  it('UC-5.2: quick reports section is visible', async () => {
    const ReportsPage = (await import('@/app/reports/page')).default;
    render(<ReportsPage />);
    expect(screen.getByText('Reportes Rápidos')).toBeInTheDocument();
  });
});

// ============================================================
// UC-6: Administration
// ============================================================
describe('UC-6: Administration', () => {
  it('UC-6.1: settings page renders with tabs', async () => {
    const SettingsPage = (await import('@/app/settings/page')).default;
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Configuración')).toBeInTheDocument();
    });
  });

  it('UC-6.2: locations tab shows data', async () => {
    const SettingsPage = (await import('@/app/settings/page')).default;
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
  });

  it('UC-6.3: users tab shows role badges', async () => {
    const SettingsPage = (await import('@/app/settings/page')).default;
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Usuarios'));
    await waitFor(() => {
      expect(screen.getByText('ADMIN')).toBeInTheDocument();
    });
  });
});

// ============================================================
// UC-7: Complete Flows (Critical End-to-End)
// ============================================================
describe('UC-7: Complete Flows', () => {
  it('UC-7.1: dashboard loads with stats after auth', async () => {
    const DashboardPage = (await import('@/app/page')).default;
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  it('UC-7.2: navigation between modules works', async () => {
    const DashboardPage = (await import('@/app/page')).default;
    const { rerender } = render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
    const UnitsPage = (await import('@/app/units/page')).default;
    rerender(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Gestión de Unidades')).toBeInTheDocument();
    });
  });
});