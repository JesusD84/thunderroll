import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UnitsPage from '@/app/units/page';
import NewUnitPage from '@/app/units/new/page';

// --- Mocks ---
const mockPush = vi.fn();
let mockSearchParams = new URLSearchParams();
let mockSession: any = { user: { name: 'Admin' }, accessToken: 'fake-token' };
let mockStatus = 'authenticated';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => mockSearchParams,
  useParams: () => ({ id: '1' }),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: mockSession,
    status: mockStatus,
  }),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

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
    status: 'SOLD', current_location_id: 2,
    current_location: { name: 'Sucursal Norte', id: 2 },
    sold_date: '2025-02-01T00:00:00Z', created_at: '2025-01-15T00:00:00Z',
  },
  {
    id: 3, brand: 'Italika', model: 'FT150', color: 'negro',
    engine_number: null, chassis_number: null,
    status: 'WAREHOUSE_UNIDENTIFIED', current_location_id: 1,
    current_location: { name: 'Bodega Central', id: 1 },
    sold_date: null, created_at: '2025-03-01T00:00:00Z',
  },
];

const mockLocations = [
  { id: 1, name: 'Bodega Central' },
  { id: 2, name: 'Sucursal Norte' },
];

function mockOk(data: any) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockSearchParams = new URLSearchParams();
  mockSession = { user: { name: 'Admin' }, accessToken: 'fake-token' };
  mockStatus = 'authenticated';
  mockFetch.mockReset();
});

// ============================================================
// UnitsPage - List
// ============================================================
describe('UnitsPage', () => {
  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    render(<UnitsPage />);
    expect(screen.getByText('Cargando unidades...')).toBeInTheDocument();
  });

  it('renders units in table after loading', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Honda PCX')).toBeInTheDocument();
    });
    expect(screen.getByText('Yamaha NMAX')).toBeInTheDocument();
    expect(screen.getByText('Italika FT150')).toBeInTheDocument();
    expect(screen.getByText('Unidades (3)')).toBeInTheDocument();
  });

  it('renders status badges with correct labels', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Disponible')).toBeInTheDocument();
    });
    expect(screen.getByText('Vendida')).toBeInTheDocument();
    expect(screen.getByText('Sin Identificar')).toBeInTheDocument();
  });

  it('shows engine and chassis numbers', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('ENG001')).toBeInTheDocument();
    });
    expect(screen.getByText('CHS001')).toBeInTheDocument();
  });

  it('shows dash for missing engine/chassis numbers', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Italika FT150')).toBeInTheDocument();
    });
    const dashes = screen.getAllByText('-');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it('filters units by search term', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Honda PCX')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('Buscar por # motor, chasis, marca...');
    await userEvent.type(searchInput, 'Yamaha');
    await waitFor(() => {
      expect(screen.queryByText('Honda PCX')).not.toBeInTheDocument();
      expect(screen.getByText('Yamaha NMAX')).toBeInTheDocument();
    });
    expect(screen.getByText('Unidades (1)')).toBeInTheDocument();
  });

  it('filters units by engine number', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Honda PCX')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('Buscar por # motor, chasis, marca...');
    await userEvent.type(searchInput, 'ENG001');
    await waitFor(() => {
      expect(screen.getByText('Honda PCX')).toBeInTheDocument();
      expect(screen.queryByText('Yamaha NMAX')).not.toBeInTheDocument();
    });
  });

  it('clears all filters on clear button click', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Honda PCX')).toBeInTheDocument();
    });
    const searchInput = screen.getByPlaceholderText('Buscar por # motor, chasis, marca...');
    await userEvent.type(searchInput, 'nonexistent');
    await waitFor(() => {
      expect(screen.getByText('Unidades (0)')).toBeInTheDocument();
    });
    await userEvent.click(screen.getByText('Limpiar Filtros'));
    await waitFor(() => {
      expect(screen.getByText('Unidades (3)')).toBeInTheDocument();
    });
  });

  it('renders link to create new unit', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Agregar Unidad')).toBeInTheDocument();
    });
    const link = screen.getByText('Agregar Unidad').closest('a');
    expect(link).toHaveAttribute('href', '/units/new');
  });

  it('renders detail links for each unit', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      const detailButtons = screen.getAllByText('Ver Detalle');
      expect(detailButtons.length).toBe(3);
    });
  });

  it('handles fetch error gracefully', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidades (0)')).toBeInTheDocument();
    });
  });

  it('handles non-ok response gracefully', async () => {
    mockFetch
      .mockResolvedValueOnce(Promise.resolve({
        ok: false, status: 500,
        json: () => Promise.resolve({ detail: 'err' }),
      }))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidades (0)')).toBeInTheDocument();
    });
  });

  it('does not fetch when no session token', async () => {
    mockSession = null;
    mockStatus = 'unauthenticated';
    render(<UnitsPage />);
    expect(screen.getByText('Cargando unidades...')).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('pre-fills status filter from search params', async () => {
    mockSearchParams = new URLSearchParams({ status: 'SOLD' });
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getByText('Yamaha NMAX')).toBeInTheDocument();
      expect(screen.queryByText('Honda PCX')).not.toBeInTheDocument();
    });
  });

  it('shows location names in table', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockUnits))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<UnitsPage />);
    await waitFor(() => {
      expect(screen.getAllByText('Bodega Central').length).toBe(2);
    });
    expect(screen.getByText('Sucursal Norte')).toBeInTheDocument();
  });
});

// ============================================================
// NewUnitPage - Create Form
// ============================================================
describe('NewUnitPage', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  it('renders the form with all fields', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    render(<NewUnitPage />);
    await waitFor(() => {
      expect(screen.getByText('Agregar Nueva Unidad')).toBeInTheDocument();
    });
    expect(screen.getByLabelText('Marca')).toBeInTheDocument();
    expect(screen.getByLabelText('Modelo')).toBeInTheDocument();
    expect(screen.getByLabelText('Número de Motor')).toBeInTheDocument();
    expect(screen.getByLabelText('Número de Chasis')).toBeInTheDocument();
    expect(screen.getByLabelText('Notas')).toBeInTheDocument();
  });

  it('renders back button linking to units list', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    render(<NewUnitPage />);
    await waitFor(() => {
      expect(screen.getByText('Volver')).toBeInTheDocument();
    });
    const link = screen.getByText('Volver').closest('a');
    expect(link).toHaveAttribute('href', '/units');
  });

  it('submit button is disabled when required fields are empty', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    render(<NewUnitPage />);
    await waitFor(() => {
      expect(screen.getByText('Agregar Nueva Unidad')).toBeInTheDocument();
    });
    const submitBtn = screen.getByRole('button', { name: /Guardar Unidad/ });
    expect(submitBtn).toBeDisabled();
  });

  it('enables submit when all required fields are filled', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    render(<NewUnitPage />);
    await waitFor(() => {
      expect(screen.getByText('Agregar Nueva Unidad')).toBeInTheDocument();
    });
    await userEvent.type(screen.getByLabelText('Marca'), 'Honda');
    await userEvent.type(screen.getByLabelText('Modelo'), 'PCX');
    await user.click(screen.getByText('Selecciona el color'));
    await user.click(screen.getByRole('option', { name: 'Rojo' }));
    await user.click(screen.getByText('Selecciona ubicación'));
    await user.click(screen.getByRole('option', { name: 'Bodega Central' }));

    const submitBtn = screen.getByRole('button', { name: /Guardar Unidad/ });
    expect(submitBtn).not.toBeDisabled();
  });

  it('submits form and redirects on success', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockLocations))
      .mockResolvedValueOnce(mockOk({ id: 4 }));
    render(<NewUnitPage />);
    await waitFor(() => {
      expect(screen.getByText('Agregar Nueva Unidad')).toBeInTheDocument();
    });
    await userEvent.type(screen.getByLabelText('Marca'), 'Honda');
    await userEvent.type(screen.getByLabelText('Modelo'), 'PCX');
    await user.click(screen.getByText('Selecciona el color'));
    await user.click(screen.getByRole('option', { name: 'Rojo' }));
    await user.click(screen.getByText('Selecciona ubicación'));
    await user.click(screen.getByRole('option', { name: 'Bodega Central' }));
    await user.click(screen.getByRole('button', { name: /Guardar Unidad/ }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/units');
    });
  });

  it('shows error message on failed creation', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockLocations))
      .mockResolvedValueOnce(Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ detail: 'Motor ya existe' }),
      }));
    render(<NewUnitPage />);
    await waitFor(() => {
      expect(screen.getByText('Agregar Nueva Unidad')).toBeInTheDocument();
    });
    await userEvent.type(screen.getByLabelText('Marca'), 'Honda');
    await userEvent.type(screen.getByLabelText('Modelo'), 'PCX');
    await user.click(screen.getByText('Selecciona el color'));
    await user.click(screen.getByRole('option', { name: 'Rojo' }));
    await user.click(screen.getByText('Selecciona ubicación'));
    await user.click(screen.getByRole('option', { name: 'Bodega Central' }));
    await user.click(screen.getByRole('button', { name: /Guardar Unidad/ }));

    await waitFor(() => {
      expect(screen.getByText('Motor ya existe')).toBeInTheDocument();
    });
  });

  it('shows connection error on network failure', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockLocations))
      .mockRejectedValueOnce(new Error('Network error'));
    render(<NewUnitPage />);
    await waitFor(() => {
      expect(screen.getByText('Agregar Nueva Unidad')).toBeInTheDocument();
    });
    await userEvent.type(screen.getByLabelText('Marca'), 'Honda');
    await userEvent.type(screen.getByLabelText('Modelo'), 'PCX');
    await user.click(screen.getByText('Selecciona el color'));
    await user.click(screen.getByRole('option', { name: 'Rojo' }));
    await user.click(screen.getByText('Selecciona ubicación'));
    await user.click(screen.getByRole('option', { name: 'Bodega Central' }));
    await user.click(screen.getByRole('button', { name: /Guardar Unidad/ }));

    await waitFor(() => {
      expect(screen.getByText('Error de conexión')).toBeInTheDocument();
    });
  });

  it('cancel button navigates back to units', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockLocations));
    render(<NewUnitPage />);
    await waitFor(() => {
      expect(screen.getByText('Agregar Nueva Unidad')).toBeInTheDocument();
    });
    const cancelLink = screen.getByText('Cancelar').closest('a');
    expect(cancelLink).toHaveAttribute('href', '/units');
  });
});