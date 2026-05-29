import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReportsPage from '@/app/reports/page';

// --- Mocks ---
let mockSession: any = { user: { name: 'Admin' }, accessToken: 'fake-token' };
let mockStatus = 'authenticated';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: mockSession,
    status: mockStatus,
  }),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockOk(data: any) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
}

const mockInventoryData = {
  total_units: 42,
  units: [
    { id: 1, brand: 'Honda', model: 'PCX', engine_number: 'ENG001', color: 'rojo', status: 'AVAILABLE' },
    { id: 2, brand: 'Yamaha', model: 'NMAX', engine_number: 'ENG002', color: 'azul', status: 'SOLD' },
  ],
};

const mockTransfersData = {
  total_transfers: 15,
  transfers: [
    { id: 1, unit_id: 10, status: 'IN_TRANSIT' },
    { id: 2, unit_id: 11, status: 'RECEIVED' },
  ],
};

const mockSalesData = {
  total_sales: 8,
  sales: [
    { id: 1, brand: 'Honda', model: 'PCX', engine_number: 'ENG001', sold_date: '2025-05-15T00:00:00Z' },
    { id: 2, brand: 'Yamaha', model: 'NMAX', engine_number: 'ENG002', sold_date: '2025-05-20T00:00:00Z' },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  mockSession = { user: { name: 'Admin' }, accessToken: 'fake-token' };
  mockStatus = 'authenticated';
  mockFetch.mockReset();
});

// ============================================================
// ReportsPage
// ============================================================
describe('ReportsPage', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  it('renders page with header and tab buttons', () => {
    render(<ReportsPage />);
    expect(screen.getByText('Reportes')).toBeInTheDocument();
    expect(screen.getByText('Genera y descarga reportes de inventario, transferencias y ventas')).toBeInTheDocument();
    expect(screen.getByText('Inventario')).toBeInTheDocument();
    expect(screen.getByText('Transferencias')).toBeInTheDocument();
    expect(screen.getByText('Ventas')).toBeInTheDocument();
  });

  it('shows inventory report title by default', () => {
    render(<ReportsPage />);
    expect(screen.getByText('Reporte de Inventario')).toBeInTheDocument();
    expect(screen.getByText('Descarga el estado actual del inventario.')).toBeInTheDocument();
  });

  it('switches tab and updates title', async () => {
    render(<ReportsPage />);
    await user.click(screen.getByText('Transferencias'));
    expect(screen.getByText('Reporte de Transferencias')).toBeInTheDocument();
    expect(screen.getByText('Selecciona el rango de fechas para exportar.')).toBeInTheDocument();
  });

  it('switches to sales tab', async () => {
    render(<ReportsPage />);
    await user.click(screen.getByText('Ventas'));
    expect(screen.getByText('Reporte de Ventas')).toBeInTheDocument();
  });

  it('shows date pickers for transfers tab', async () => {
    render(<ReportsPage />);
    await user.click(screen.getByText('Transferencias'));
    expect(screen.getByText('Fecha Desde')).toBeInTheDocument();
    expect(screen.getByText('Fecha Hasta')).toBeInTheDocument();
  });

  it('hides date pickers for inventory tab', () => {
    render(<ReportsPage />);
    expect(screen.queryByText('Fecha Desde')).not.toBeInTheDocument();
    expect(screen.queryByText('Fecha Hasta')).not.toBeInTheDocument();
  });

  it('shows preview and download buttons', () => {
    render(<ReportsPage />);
    expect(screen.getAllByText('Vista Previa').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Descargar Excel')).toBeInTheDocument();
  });

  it('shows empty preview state initially', () => {
    render(<ReportsPage />);
    expect(screen.getByText('Sin datos para mostrar')).toBeInTheDocument();
    expect(screen.getByText('Haz clic en "Vista Previa" para ver los datos.')).toBeInTheDocument();
  });

  it('loads and displays inventory preview data', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockInventoryData));
    render(<ReportsPage />);
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      expect(screen.getByText('42 unidades encontradas')).toBeInTheDocument();
    });
    expect(screen.getByText('Honda PCX')).toBeInTheDocument();
    expect(screen.getByText('Yamaha NMAX')).toBeInTheDocument();
  });

  it('loads and displays transfers preview data', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockTransfersData));
    render(<ReportsPage />);
    await user.click(screen.getByText('Transferencias'));
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      expect(screen.getByText('15 transferencias encontradas')).toBeInTheDocument();
    });
    expect(screen.getByText('Transfer #1')).toBeInTheDocument();
  });

  it('loads and displays sales preview data', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockSalesData));
    render(<ReportsPage />);
    await user.click(screen.getByText('Ventas'));
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      expect(screen.getByText('8 ventas encontradas')).toBeInTheDocument();
    });
    expect(screen.getByText('Honda PCX')).toBeInTheDocument();
  });

  it('shows error message on preview failure', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    render(<ReportsPage />);
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('renders quick reports section', () => {
    render(<ReportsPage />);
    expect(screen.getByText('Reportes Rápidos')).toBeInTheDocument();
    expect(screen.getByText('Transferencias Hoy')).toBeInTheDocument();
    expect(screen.getByText('Inventario Actual')).toBeInTheDocument();
    expect(screen.getByText('Ventas del Mes')).toBeInTheDocument();
  });

  it('resets preview data when switching tabs', async () => {
    mockFetch.mockResolvedValueOnce(mockOk(mockInventoryData));
    render(<ReportsPage />);
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      expect(screen.getByText('42 unidades encontradas')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Transferencias'));
    await waitFor(() => {
      expect(screen.getByText('Sin datos para mostrar')).toBeInTheDocument();
    });
  });

  it('downloads Excel report on button click', async () => {
    const blob = new Blob(['test'], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    mockFetch.mockResolvedValueOnce({ ok: true, blob: () => Promise.resolve(blob) });
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test');
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    render(<ReportsPage />);
    await user.click(screen.getByText('Descargar Excel'));
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/reports/export/inventory'),
        expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer fake-token' }) })
      );
    });
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
  });
});