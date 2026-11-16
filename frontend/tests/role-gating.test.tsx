import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/settings/page';
import UnitsPage from '@/app/units/page';
import UnitDetailPage from '@/app/units/[id]/page';
import TransfersPage from '@/app/transfers/page';

/**
 * Role gating: what each role may actually DO in the UI.
 *
 * The backend authorization matrix (backend/tests/test_authorization_matrix.py)
 * checks that the permission flags declared in lib/auth.ts match the
 * ``require_role`` rules of the API. It cannot check that the components
 * actually use those flags: a button gated with the wrong flag (or with none)
 * still looks fine to that test but answers 403 in production.
 *
 * These tests render the real pages with a session of each role and assert
 * which actions are offered.
 */

// --- Mocks ---
let mockSession: any = { user: { name: 'Admin', role: 'admin' }, accessToken: 'fake-token' };

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: '1' }),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: mockSession,
    status: 'authenticated',
  }),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockOk(data: any, totalCount?: number) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(data),
    headers: {
      get: (name: string) =>
        name === 'X-Total-Count' ? String(totalCount ?? (Array.isArray(data) ? data.length : 0)) : null,
    },
  });
}

const mockLocations = [
  { id: 1, name: 'Bodega Central', address: 'Calle 1', created_at: '2025-01-01T00:00:00Z' },
  { id: 2, name: 'Sucursal Norte', address: null, created_at: '2025-02-01T00:00:00Z' },
];

const mockUsers = [
  { id: 1, email: 'admin@test.com', username: 'admin', first_name: 'Admin', last_name: 'User', role: 'admin', is_active: true, created_at: '2025-01-01T00:00:00Z', updated_at: null },
  { id: 2, email: 'op@test.com', username: 'operator', first_name: 'Op', last_name: 'User', role: 'operator', is_active: true, created_at: '2025-02-01T00:00:00Z', updated_at: null },
];

const mockUnits = [
  {
    id: 1, brand: 'Honda', model: 'PCX', color: 'rojo',
    engine_number: 'ENG001', chassis_number: 'CHS001',
    status: 'AVAILABLE', current_location_id: 1,
    current_location: { name: 'Bodega Central', id: 1 },
    sold_date: null, created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 2, brand: 'Yamaha', model: 'NMAX', color: 'azul',
    engine_number: 'ENG002', chassis_number: 'CHS002',
    status: 'IN_TRANSIT', current_location_id: 2,
    current_location: { name: 'Sucursal Norte', id: 2 },
    sold_date: null, created_at: '2025-01-15T00:00:00Z',
  },
];

const mockTransfers = [
  {
    id: 1, unit_id: 2, dispatched_by_id: 1, dispatched_by_name: 'Test Admin', received_by_id: null,
    origin_location_id: 1, destination_location_id: 2,
    status: 'IN_TRANSIT', dispatched_at: '2025-05-01T00:00:00Z', received_at: null,
  },
];

/**
 * Route the mocked fetch by URL instead of by call order, so every page
 * gets its data no matter how many requests it fires.
 */
function routeFetch(url: string) {
  const path = url.split('?')[0];

  if (path.endsWith('/api/v1/units/')) return mockOk(mockUnits, mockUnits.length);
  if (path.endsWith('/api/v1/units/1/transfers')) return mockOk(mockTransfers);
  if (path.endsWith('/api/v1/transfers/unit/1/active')) return mockOk(mockTransfers[0]);
  if (path.endsWith('/api/v1/units/1')) return mockOk(mockUnits[0]);
  if (path.endsWith('/api/v1/locations/')) return mockOk(mockLocations);
  if (path.endsWith('/api/v1/locations/1')) return mockOk(mockLocations[0]);
  if (path.endsWith('/api/v1/user/')) return mockOk(mockUsers);
  if (path.endsWith('/api/v1/transfers/')) return mockOk(mockTransfers);
  return mockOk([]);
}

function asRole(role: 'admin' | 'manager' | 'operator') {
  mockSession = { user: { name: role, role }, accessToken: 'fake-token' };
}

beforeEach(() => {
  vi.clearAllMocks();
  asRole('admin');
  mockFetch.mockReset();
  mockFetch.mockImplementation((input: any) => routeFetch(String(input)));
});

// ============================================================
// SettingsPage
// ============================================================
describe('SettingsPage — gating por rol', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  it('un ADMIN ve las pestañas de ubicaciones y usuarios', async () => {
    asRole('admin');
    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Ubicaciones' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Usuarios' })).toBeInTheDocument();
  });

  it('un MANAGER ve las pestañas de ubicaciones y usuarios', async () => {
    asRole('manager');
    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Ubicaciones' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Usuarios' })).toBeInTheDocument();
  });

  it('un OPERATOR solo ve la pestaña "Mi cuenta"', async () => {
    asRole('operator');
    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Cambiar contraseña', { selector: 'button' })).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: 'Ubicaciones' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Usuarios' })).not.toBeInTheDocument();
  });

  it('solo un ADMIN puede eliminar una ubicación', async () => {
    asRole('admin');
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });

    const deleteButton = screen.getByLabelText('Eliminar Bodega Central');
    expect(deleteButton).toBeEnabled();
  });

  it('un MANAGER no puede eliminar una ubicación (el botón va deshabilitado)', async () => {
    asRole('manager');
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });

    // The button is still there, but disabled: clicking it would answer 403.
    const deleteButton = screen.getByLabelText('Eliminar Bodega Central');
    expect(deleteButton).toBeDisabled();
  });

  it('solo un ADMIN ve las acciones de editar y eliminar usuarios', async () => {
    asRole('admin');
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: 'Usuarios' }));

    expect(screen.getByLabelText('Editar Admin User')).toBeInTheDocument();
    expect(screen.getByLabelText('Eliminar Admin User')).toBeInTheDocument();
  });

  it('un MANAGER no ve las acciones de editar y eliminar usuarios', async () => {
    asRole('manager');
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: 'Usuarios' }));

    expect(screen.queryByLabelText('Editar Admin User')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Eliminar Admin User')).not.toBeInTheDocument();
  });
});

// ============================================================
// UnitsPage
// ============================================================
describe('UnitsPage — gating por rol', () => {
  it('un ADMIN puede agregar y eliminar unidades', async () => {
    asRole('admin');
    render(<UnitsPage />);

    await waitFor(() => {
      expect(screen.getByText('Honda')).toBeInTheDocument();
    });
    expect(screen.getByText('Agregar Unidad')).toBeInTheDocument();
    expect(screen.getByLabelText('Eliminar unidad 1')).toBeInTheDocument();
  });

  it('un MANAGER puede agregar unidades pero no eliminarlas', async () => {
    asRole('manager');
    render(<UnitsPage />);

    await waitFor(() => {
      expect(screen.getByText('Honda')).toBeInTheDocument();
    });
    expect(screen.getByText('Agregar Unidad')).toBeInTheDocument();
    // DELETE /units/{id} is admin-only: a manager must not see the button.
    expect(screen.queryByLabelText('Eliminar unidad 1')).not.toBeInTheDocument();
  });

  it('un OPERATOR no puede agregar ni eliminar unidades', async () => {
    asRole('operator');
    render(<UnitsPage />);

    await waitFor(() => {
      expect(screen.getByText('Honda')).toBeInTheDocument();
    });
    expect(screen.queryByText('Agregar Unidad')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Eliminar unidad 1')).not.toBeInTheDocument();
  });
});

// ============================================================
// UnitDetailPage
// ============================================================
describe('UnitDetailPage — gating por rol', () => {
  it('un ADMIN y un MANAGER ven el botón Editar', async () => {
    asRole('admin');
    render(<UnitDetailPage />);
    await waitFor(() => {
      expect(screen.getByText('Editar')).toBeInTheDocument();
    });

    asRole('manager');
    render(<UnitDetailPage />);
    await waitFor(() => {
      expect(screen.getByText('Editar')).toBeInTheDocument();
    });
  });

  it('un OPERATOR no ve el botón Editar', async () => {
    asRole('operator');
    render(<UnitDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Transferir')).toBeInTheDocument();
    });
    expect(screen.queryByText('Editar')).not.toBeInTheDocument();
  });

  it('un OPERATOR sí puede despachar y vender (su poder real)', async () => {
    asRole('operator');
    render(<UnitDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Transferir')).toBeInTheDocument();
    });
    expect(screen.getByText('Vender')).toBeInTheDocument();
  });
});

// ============================================================
// TransfersPage
// ============================================================
describe('TransfersPage — gating por rol', () => {
  it('un ADMIN puede eliminar una transferencia', async () => {
    asRole('admin');
    render(<TransfersPage />);

    await waitFor(() => {
      expect(screen.getByLabelText('Eliminar transferencia 1')).toBeInTheDocument();
    });
  });

  it('un MANAGER no puede eliminar una transferencia', async () => {
    asRole('manager');
    render(<TransfersPage />);

    await waitFor(() => {
      expect(screen.getByText('Confirmar Llegada')).toBeInTheDocument();
    });
    expect(screen.queryByLabelText('Eliminar transferencia 1')).not.toBeInTheDocument();
  });

  it('un OPERATOR no puede eliminar una transferencia', async () => {
    asRole('operator');
    render(<TransfersPage />);

    await waitFor(() => {
      expect(screen.getByText('Confirmar Llegada')).toBeInTheDocument();
    });
    expect(screen.queryByLabelText('Eliminar transferencia 1')).not.toBeInTheDocument();
  });

  it('un OPERATOR sí puede confirmar la llegada de una transferencia', async () => {
    asRole('operator');
    render(<TransfersPage />);

    await waitFor(() => {
      expect(screen.getByText('Confirmar Llegada')).toBeInTheDocument();
    });
  });
});
