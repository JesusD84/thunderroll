import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TransfersPage from '@/app/transfers/page';

// --- Mocks ---
let mockSession: any = { user: { name: 'Admin' }, accessToken: 'fake-token' };
let mockStatus = 'authenticated';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
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

const mockTransfers = [
  {
    id: 1, unit_id: 10, dispatched_by_id: 1, received_by_id: null,
    origin_location_id: 1, destination_location_id: 2,
    status: 'IN_TRANSIT', dispatched_at: '2025-05-01T00:00:00Z', received_at: null,
  },
  {
    id: 2, unit_id: 11, dispatched_by_id: 1, received_by_id: 2,
    origin_location_id: 2, destination_location_id: 3,
    status: 'RECEIVED', dispatched_at: '2025-04-15T00:00:00Z', received_at: '2025-04-16T00:00:00Z',
  },
  {
    id: 3, unit_id: 12, dispatched_by_id: null, received_by_id: null,
    origin_location_id: 1, destination_location_id: 2,
    status: 'PENDING', dispatched_at: null, received_at: null,
  },
];

const mockLocations = [
  { id: 1, name: 'Bodega Central' },
  { id: 2, name: 'Sucursal Norte' },
  { id: 3, name: 'Sucursal Sur' },
];

function mockOk(data: any) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockSession = { user: { name: 'Admin' }, accessToken: 'fake-token' };
  mockStatus = 'authenticated';
  mockFetch.mockReset();
});

// ============================================================
// TransfersPage - List
// ============================================================
describe('TransfersPage', () => {
  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}));
    render(<TransfersPage />);
    expect(screen.getByText('Cargando transferencias...')).toBeInTheDocument();
  });

  it('renders transfers in table after loading', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #10')).toBeInTheDocument();
    });
    expect(screen.getByText('Unidad #11')).toBeInTheDocument();
    expect(screen.getByText('Unidad #12')).toBeInTheDocument();
  });

  it('renders status badges with correct labels', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('En Tránsito')).toBeInTheDocument();
    });
    expect(screen.getByText('Pendiente')).toBeInTheDocument();
    const completadaBadges = screen.getAllByText('Completada');
    expect(completadaBadges.length).toBeGreaterThanOrEqual(1);
  });

  it('shows route with origin and destination', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #10')).toBeInTheDocument();
    });
    expect(screen.getAllByText('Bodega Central').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Sucursal Norte').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Sucursal Sur')).toBeInTheDocument();
  });

  it('filters transfers by status', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #10')).toBeInTheDocument();
    });
    // Open status filter and select "En Tránsito"
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const filterCombo = screen.getAllByRole('combobox')[0];
    await user.click(filterCombo);
    await user.click(screen.getByRole('option', { name: 'En Tránsito' }));
    await waitFor(() => {
      expect(screen.queryByText('Unidad #11')).not.toBeInTheDocument();
      expect(screen.getByText('Unidad #10')).toBeInTheDocument();
    });
  });

  it('shows empty state when no transfers', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk([]))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('No hay transferencias registradas')).toBeInTheDocument();
    });
  });

  it('shows empty state with filter label when filtered', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #10')).toBeInTheDocument();
    });
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const filterCombo = screen.getAllByRole('combobox')[0];
    await user.click(filterCombo);
    await user.click(screen.getByRole('option', { name: 'Cancelada' }));
    await waitFor(() => {
      expect(screen.getByText(/No hay transferencias con estado/)).toBeInTheDocument();
    });
  });

  it('shows pending count badge when there are active transfers', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('2 en tránsito')).toBeInTheDocument();
    });
  });

  it('does not show pending badge when no active transfers', async () => {
    const completedOnly = mockTransfers.filter(t => t.status === 'RECEIVED');
    mockFetch
      .mockResolvedValueOnce(mockOk(completedOnly))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #11')).toBeInTheDocument();
    });
    expect(screen.queryByText(/en tránsito/)).not.toBeInTheDocument();
  });

  it('shows confirm arrival button for PENDING and IN_TRANSIT', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      const confirmButtons = screen.getAllByText('Confirmar Llegada');
      expect(confirmButtons.length).toBe(2); // IN_TRANSIT + PENDING
    });
  });

  it('shows completed badge for RECEIVED transfers', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #11')).toBeInTheDocument();
    });
    // The RECEIVED transfer shows a "Completada" badge in actions column
    const completedBadges = screen.getAllByText('Completada');
    expect(completedBadges.length).toBeGreaterThanOrEqual(1);
  });

  it('handles fetch error gracefully', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('No hay transferencias registradas')).toBeInTheDocument();
    });
  });

  it('does not fetch when no session token', async () => {
    mockSession = null;
    mockStatus = 'unauthenticated';
    render(<TransfersPage />);
    expect(screen.getByText('Cargando transferencias...')).toBeInTheDocument();
    expect(mockFetch).not.toHaveBeenCalled();
  });
});

// ============================================================
// TransfersPage - New Transfer Form
// ============================================================
describe('TransfersPage - New Transfer', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  it('opens new transfer form on button click', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #10')).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /Nueva Transferencia/ }));
    expect(screen.getByText('¿De dónde sale?')).toBeInTheDocument();
    expect(screen.getByText('¿A dónde va?')).toBeInTheDocument();
  });

  it('cancel button closes the form', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #10')).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /Nueva Transferencia/ }));
    expect(screen.getByText('¿De dónde sale?')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => {
      expect(screen.queryByText('¿De dónde sale?')).not.toBeInTheDocument();
    });
  });

  it('submit button is disabled when fields are empty', async () => {
    mockFetch
      .mockResolvedValueOnce(mockOk(mockTransfers))
      .mockResolvedValueOnce(mockOk(mockLocations));
    render(<TransfersPage />);
    await waitFor(() => {
      expect(screen.getByText('Unidad #10')).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /Nueva Transferencia/ }));
    const submitBtn = screen.getByRole('button', { name: /Crear Transferencia/ });
    expect(submitBtn).toBeDisabled();
  });
});