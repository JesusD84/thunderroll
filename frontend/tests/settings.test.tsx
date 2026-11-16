import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '@/app/settings/page';
import { API_BASE } from '@/lib/api';
import { mockResponse } from './mocks/response';

// --- Mocks ---
// The session no longer carries an access token: the credential lives in the
// encrypted cookie and the server-side proxy adds the Authorization header.
let mockSession: any = { user: { name: 'Admin', role: 'admin' } };
let mockStatus = 'authenticated';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: mockSession,
    status: mockStatus,
  }),
  getSession: () => Promise.resolve(null),
  signOut: vi.fn(),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockOk(data: any) {
  return Promise.resolve(mockResponse(data));
}

const mockLocations = [
  { id: 1, name: 'Bodega Central', address: 'Calle 1 #123', created_at: '2025-01-15T00:00:00Z' },
  { id: 2, name: 'Sucursal Norte', address: null, created_at: '2025-03-20T00:00:00Z' },
];

const mockUsers = [
  { id: 1, email: 'admin@test.com', username: 'admin', first_name: 'Admin', last_name: 'User', role: 'admin', is_active: true, created_at: '2025-01-01T00:00:00Z', updated_at: null },
  { id: 2, email: 'op@test.com', username: 'operator', first_name: 'Op', last_name: 'User', role: 'operator', is_active: true, created_at: '2025-02-01T00:00:00Z', updated_at: null },
  { id: 3, email: 'mgr@test.com', username: 'manager', first_name: 'Mgr', last_name: 'User', role: 'manager', is_active: false, created_at: '2025-03-01T00:00:00Z', updated_at: null },
];

beforeEach(() => {
  vi.clearAllMocks();
  // The role drives the permissions: without it the page would only offer the
  // "Mi cuenta" tab and the locations/users tabs would not render.
  mockSession = { user: { name: 'Admin', role: 'admin' } };
  mockStatus = 'authenticated';
  mockFetch.mockReset();
});

// ============================================================
// SettingsPage
// ============================================================
describe('SettingsPage', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  it('renders page with header and tab buttons', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    expect(screen.getByText('Configuración')).toBeInTheDocument();
    expect(screen.getByText('Gestiona ubicaciones y usuarios del sistema')).toBeInTheDocument();
    expect(screen.getAllByText('Ubicaciones').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Usuarios')).toBeInTheDocument();
  });

  it('shows locations tab by default with data', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    expect(screen.getByText('Sucursal Norte')).toBeInTheDocument();
    expect(screen.getByText('Calle 1 #123')).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<SettingsPage />);
    expect(screen.getByText('Cargando ubicaciones...')).toBeInTheDocument();
  });

  it('switches to users tab and shows data', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Usuarios'));
    expect(screen.getByText('Admin User')).toBeInTheDocument();
    expect(screen.getByText('admin@test.com')).toBeInTheDocument();
  });

  it('shows role badges with correct labels in users tab', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Usuarios'));
    expect(screen.getByText('ADMIN')).toBeInTheDocument();
    expect(screen.getByText('OPERATIVO')).toBeInTheDocument();
    expect(screen.getByText('MANAGER')).toBeInTheDocument();
  });

  it('shows active/inactive badges in users tab', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Usuarios'));
    expect(screen.getAllByText('Activo').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Inactivo')).toBeInTheDocument();
  });

  it('shows empty users message when no users', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk([]));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Usuarios'));
    await waitFor(() => {
      expect(screen.getByText('No hay usuarios o no tienes permisos para verlos')).toBeInTheDocument();
    });
  });

  it('opens new location form on button click', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /Nueva Ubicación/ }));
    expect(screen.getByText('Agregar una nueva ubicación al sistema')).toBeInTheDocument();
    expect(screen.getByLabelText('Nombre *')).toBeInTheDocument();
    expect(screen.getByLabelText('Dirección')).toBeInTheDocument();
  });

  it('creates a new location', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    const newLoc = { id: 3, name: 'Sucursal Sur', address: 'Av. Sur 456', created_at: '2025-05-01T00:00:00Z' };
    mockFetch.mockResolvedValueOnce(mockOk(newLoc));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Nueva Ubicación'));
    await user.type(screen.getByLabelText('Nombre *'), 'Sucursal Sur');
    await user.type(screen.getByLabelText('Dirección'), 'Av. Sur 456');
    await user.click(screen.getByText('Crear Ubicación'));
    await waitFor(() => {
      expect(screen.getByText('Sucursal Sur')).toBeInTheDocument();
    });
  });

  it('enters inline edit mode for a location', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    // Click the edit button (pencil icon) in the first row
    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1]; // skip header
    const editBtn = firstDataRow.querySelector('button');
    if (editBtn) await user.click(editBtn);
    await waitFor(() => {
      expect(screen.getByText('Guardar')).toBeInTheDocument();
    });
  });

  it('shows empty locations message when no locations', async () => {
    mockFetch.mockResolvedValueOnce(mockOk([]));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('No hay ubicaciones registradas')).toBeInTheDocument();
    });
  });

  it('does not render demo credentials', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    expect(screen.queryByText('Credenciales Demo')).not.toBeInTheDocument();
    expect(screen.queryByText('admin123')).not.toBeInTheDocument();
    expect(screen.queryByText('manager123')).not.toBeInTheDocument();
    expect(screen.queryByText('operator123')).not.toBeInTheDocument();
  });

  it('shows location error message on delete failure', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    // The page shows the detail of the failed call: the stubbed body is the
    // envelope FastAPI really sends.
    mockFetch.mockResolvedValueOnce(
      mockResponse(
        { detail: 'Cannot delete: there are 5 units at this location' },
        { status: 400 },
      ),
    );
    window.confirm = vi.fn(() => true);
    render(<SettingsPage />);
    await waitFor(() => {
      expect(screen.getByText('Bodega Central')).toBeInTheDocument();
    });
    // Click the delete button (trash icon) in the first row
    const rows = screen.getAllByRole('row');
    const firstDataRow = rows[1];
    const buttons = firstDataRow.querySelectorAll('button');
    const deleteBtn = buttons[buttons.length - 1]; // last button is delete
    await user.click(deleteBtn);
    await waitFor(() => {
      expect(screen.getByText('No se puede eliminar: hay 5 unidades en esta ubicación')).toBeInTheDocument();
    });
  });
});
// ============================================================
// Mi cuenta — cambio de contraseña
// ============================================================
describe('SettingsPage — Mi cuenta', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  it('lets the user change their own password', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);

    await user.click(screen.getByText('Mi cuenta'));

    await user.type(screen.getByLabelText('Contraseña actual *'), 'vieja123');
    await user.type(screen.getByLabelText('Nueva contraseña *'), 'nueva12345');
    await user.type(screen.getByLabelText('Confirmar nueva contraseña *'), 'nueva12345');
    // Third call: the PUT to /user/me/password.
    mockFetch.mockResolvedValueOnce(mockResponse('', { status: 204 }));
    await user.click(screen.getByText('Cambiar contraseña', { selector: 'button' }));

    await waitFor(() => {
      expect(screen.getByText('Contraseña actualizada correctamente.')).toBeInTheDocument();
    });

    const call = mockFetch.mock.calls.find((c) => c[0].includes(`${API_BASE}/api/v1/user/me/password`));
    expect(call).toBeDefined();
    expect(call![1].method).toBe('PUT');
    const body = JSON.parse(call![1].body);
    expect(body.current_password).toBe('vieja123');
    expect(body.new_password).toBe('nueva12345');
  });

  it('rejects a confirmation that does not match', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);

    await user.click(screen.getByText('Mi cuenta'));
    await user.type(screen.getByLabelText('Contraseña actual *'), 'vieja123');
    await user.type(screen.getByLabelText('Nueva contraseña *'), 'nueva12345');
    await user.type(screen.getByLabelText('Confirmar nueva contraseña *'), 'otra99999');
    await user.click(screen.getByText('Cambiar contraseña', { selector: 'button' }));

    await waitFor(() => {
      expect(screen.getByText('La nueva contraseña y su confirmación no coinciden')).toBeInTheDocument();
    });
    expect(mockFetch.mock.calls.some((c) => c[0].includes(`${API_BASE}/api/v1/user/me/password`))).toBe(false);
  });

  it('shows only the account tab for an operator', async () => {
    mockSession = { user: { name: 'Op', role: 'operator' } };
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    mockFetch.mockResolvedValueOnce(mockOk(mockUsers));
    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('Cambiar contraseña', { selector: 'button' })).toBeInTheDocument();
    });
    expect(screen.queryByText('Ubicaciones')).not.toBeInTheDocument();
    expect(screen.queryByText('Usuarios')).not.toBeInTheDocument();
  });
});
