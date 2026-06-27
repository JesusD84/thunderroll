import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImportsHistoryPage from '@/app/imports/history/page';
import ImportDetailPage from '@/app/imports/[id]/page';

// --- Mocks ---
let mockSession: any = { user: { name: 'Admin', role: 'admin' }, accessToken: 'fake-token' };
let mockStatus = 'authenticated';
let mockParams: Record<string, string> = {};

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => mockParams,
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({ data: mockSession, status: mockStatus }),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

function mockJson(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init;
  return Promise.resolve({
    ok,
    status,
    statusText: ok ? 'OK' : 'Error',
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

const importsList = [
  {
    id: 1,
    filename: 'uploads/inv1.xlsx',
    original_filename: 'inv1.xlsx',
    total_records: 10,
    successful_imports: 9,
    failed_imports: 1,
    user_id: 1,
    status: 'completed',
    batch_period: '2026-ABRIL',
    product_type: 'triciclo',
    notes: null,
    import_date: '2026-01-01T10:00:00Z',
    completed_at: '2026-01-01T10:01:00Z',
  },
  {
    id: 2,
    filename: 'uploads/inv2.xlsx',
    original_filename: 'inv2.xlsx',
    total_records: 5,
    successful_imports: 0,
    failed_imports: 5,
    user_id: 1,
    status: 'failed',
    batch_period: null,
    product_type: null,
    notes: 'boom',
    import_date: '2026-01-02T10:00:00Z',
    completed_at: null,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  mockSession = { user: { name: 'Admin', role: 'admin' }, accessToken: 'fake-token' };
  mockStatus = 'authenticated';
  mockParams = {};
});

// ============================================================
// History page
// ============================================================
describe('ImportsHistoryPage', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  it('lists imports with their status', async () => {
    mockFetch.mockReturnValueOnce(mockJson(importsList));
    render(<ImportsHistoryPage />);

    await waitFor(() => {
      expect(screen.getByText('inv1.xlsx')).toBeInTheDocument();
    });
    expect(screen.getByText('inv2.xlsx')).toBeInTheDocument();
    expect(screen.getByText('Completado')).toBeInTheDocument();
    expect(screen.getByText('Fallido')).toBeInTheDocument();

    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('/api/v1/imports/');
  });

  it('shows an empty state when there are no imports', async () => {
    mockFetch.mockReturnValueOnce(mockJson([]));
    render(<ImportsHistoryPage />);

    await waitFor(() => {
      expect(screen.getByText('No hay importaciones todavía.')).toBeInTheDocument();
    });
  });

  it('lets an ADMIN delete an import after confirmation', async () => {
    mockFetch
      .mockReturnValueOnce(mockJson(importsList)) // GET list
      .mockReturnValueOnce(mockJson('')); // DELETE
    render(<ImportsHistoryPage />);

    await waitFor(() => {
      expect(screen.getByText('inv1.xlsx')).toBeInTheDocument();
    });

    await user.click(
      screen.getByRole('button', { name: 'Eliminar importación inv1.xlsx' }),
    );
    await user.click(screen.getByRole('button', { name: 'Eliminar' }));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
    const deleteCall = mockFetch.mock.calls[1];
    expect(deleteCall[0]).toContain('/api/v1/imports/1');
    expect(deleteCall[1].method).toBe('DELETE');

    await waitFor(() => {
      expect(screen.queryByText('inv1.xlsx')).not.toBeInTheDocument();
    });
    expect(screen.getByText('inv2.xlsx')).toBeInTheDocument();
  });

  it('hides the delete action for non-admin roles', async () => {
    mockSession = { user: { name: 'Op', role: 'operator' }, accessToken: 'fake-token' };
    mockFetch.mockReturnValueOnce(mockJson(importsList));
    render(<ImportsHistoryPage />);

    await waitFor(() => {
      expect(screen.getByText('inv1.xlsx')).toBeInTheDocument();
    });
    expect(
      screen.queryByRole('button', { name: 'Eliminar importación inv1.xlsx' }),
    ).not.toBeInTheDocument();
  });
});

// ============================================================
// Detail page
// ============================================================
describe('ImportDetailPage', () => {
  it('renders the import detail and its errors', async () => {
    mockParams = { id: '1' };
    const errorsResponse = [
      {
        id: 11,
        import_id: 1,
        row_number: 4,
        error_message: 'Identificador duplicado',
        raw_data: null,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];
    mockFetch
      .mockReturnValueOnce(mockJson(importsList[0])) // getImport
      .mockReturnValueOnce(mockJson(errorsResponse)); // getImportErrors
    render(<ImportDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Resumen')).toBeInTheDocument();
    });
    expect(screen.getByText('Completado')).toBeInTheDocument();
    expect(screen.getByText('Errores (1)')).toBeInTheDocument();
    expect(screen.getByText('Identificador duplicado')).toBeInTheDocument();

    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/imports/1');
    expect(mockFetch.mock.calls[1][0]).toContain('/api/v1/imports/1/errors');
  });

  it('shows an error when the import cannot be loaded', async () => {
    mockParams = { id: '99' };
    mockFetch
      .mockReturnValueOnce(mockJson({ detail: 'Import record not found' }, { ok: false, status: 404 }))
      .mockReturnValueOnce(mockJson({ detail: 'Import record not found' }, { ok: false, status: 404 }));
    render(<ImportDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('Import record not found')).toBeInTheDocument();
    });
  });
});
