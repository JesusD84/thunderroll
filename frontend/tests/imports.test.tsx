import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImportsPage from '@/app/imports/page';

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

beforeEach(() => {
  vi.clearAllMocks();
  mockSession = { user: { name: 'Admin' }, accessToken: 'fake-token' };
  mockStatus = 'authenticated';
});

function createFile(name: string, type = ''): File {
  return new File(['test content'], name, { type });
}

const previewResponse = {
  filename: 'inventario.xlsx',
  sheets: [
    {
      sheet: 'Hoja1',
      has_header: true,
      columns: ['NO', 'Color', 'VIN', 'Motor', 'Notas'],
      column_mapping: { NO: 'model', Color: 'color', VIN: 'frame', Motor: 'motor', Notas: null },
      mapped_fields: { model: 'NO', color: 'Color', frame: 'VIN', motor: 'Motor' },
      rows: 2,
    },
  ],
  detected_fields: ['frame', 'motor', 'color', 'model'],
  preview_data: [
    { sheet: 'Hoja1', frame: 'HXY202507500001', motor: '20250823035825', color: 'rojo', model: 'X3' },
    { sheet: 'Hoja1', frame: 'HXY202507500002', motor: '20250823035826', color: 'negro', model: 'TY-D530' },
  ],
  invalid_rows: [{ sheet: 'Hoja1', row: 4, reasons: ['Falta número de motor'], data: {} }],
  invalid_rows_count: 1,
  issues: [{ level: 'warning', message: 'Hoja vacía omitida', sheet: 'Hoja2' }],
  validation: { is_valid: true, message: 'File is ready for import' },
};

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

// ============================================================
// ImportsPage (real upload form -> POST /preview)
// ============================================================
describe('ImportsPage', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('renders the header and real upload form fields', () => {
    render(<ImportsPage />);
    expect(screen.getByText('Importar Inventario')).toBeInTheDocument();
    expect(screen.getByLabelText('Periodo de lote')).toBeInTheDocument();
    expect(screen.getByLabelText('Tipo de producto')).toBeInTheDocument();
    expect(screen.getByLabelText('Archivo')).toBeInTheDocument();
  });

  it('accepts xlsx, xls and csv files', () => {
    render(<ImportsPage />);
    const fileInput = screen.getByLabelText('Archivo') as HTMLInputElement;
    expect(fileInput.accept).toBe('.xlsx,.xls,.csv');
  });

  it('enables the preview button only after a file is selected', async () => {
    render(<ImportsPage />);
    expect(screen.getByRole('button', { name: 'Vista previa' })).toBeDisabled();
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.xlsx'));
    expect(screen.getByText('Archivo seleccionado: inv.xlsx')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Vista previa' })).not.toBeDisabled();
  });

  it('does not require batch metadata to preview', async () => {
    render(<ImportsPage />);
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.csv'));
    expect(screen.getByRole('button', { name: 'Vista previa' })).not.toBeDisabled();
  });

  it('calls POST /preview and shows the summary with identifiers preserved', async () => {
    mockFetch.mockReturnValue(mockJson(previewResponse));
    render(<ImportsPage />);
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.xlsx'));
    await user.click(screen.getByRole('button', { name: 'Vista previa' }));

    await waitFor(() => {
      expect(screen.getByText('File is ready for import')).toBeInTheDocument();
    });
    // Long chassis/engine numbers must survive verbatim (no scientific notation).
    expect(screen.getByText('HXY202507500001')).toBeInTheDocument();
    expect(screen.getByText('20250823035826')).toBeInTheDocument();

    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('/api/v1/imports/preview');
  });

  it('renders per-sheet columns with the proposed mapping', async () => {
    mockFetch.mockReturnValue(mockJson(previewResponse));
    render(<ImportsPage />);
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.xlsx'));
    await user.click(screen.getByRole('button', { name: 'Vista previa' }));

    await waitFor(() => {
      expect(screen.getByText('Hojas detectadas')).toBeInTheDocument();
    });
    // raw columns and their detected canonical field / unmapped state
    expect(screen.getByText('VIN')).toBeInTheDocument();
    expect(screen.getByText('Notas')).toBeInTheDocument();
    expect(screen.getByText('Sin mapear')).toBeInTheDocument();
    // sheet tab label
    expect(screen.getByRole('tab', { name: 'Hoja1' })).toBeInTheDocument();
  });

  it('renders parser issues', async () => {
    mockFetch.mockReturnValue(mockJson(previewResponse));
    render(<ImportsPage />);
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.xlsx'));
    await user.click(screen.getByRole('button', { name: 'Vista previa' }));

    await waitFor(() => {
      expect(screen.getByText(/Hoja vacía omitida/)).toBeInTheDocument();
    });
    expect(screen.getByText('Avisos (1)')).toBeInTheDocument();
  });

  it('lists invalid rows with their reasons without blocking', async () => {
    mockFetch.mockReturnValue(mockJson(previewResponse));
    render(<ImportsPage />);
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.xlsx'));
    await user.click(screen.getByRole('button', { name: 'Vista previa' }));

    await waitFor(() => {
      expect(screen.getByText('Filas con problemas (1)')).toBeInTheDocument();
    });
    expect(screen.getByText('Falta número de motor')).toBeInTheDocument();
  });

  it('lets the user remap a column and re-previews with column_mapping', async () => {
    mockFetch.mockReturnValue(mockJson(previewResponse));
    render(<ImportsPage />);
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.xlsx'));
    await user.click(screen.getByRole('button', { name: 'Vista previa' }));

    await waitFor(() => {
      expect(screen.getByText('Hojas detectadas')).toBeInTheDocument();
    });

    // The unmapped "Notas" column exposes a Select; map it to "Modelo".
    await user.click(screen.getByRole('combobox', { name: 'Campo para Notas' }));
    await user.click(screen.getByRole('option', { name: 'Modelo' }));

    await user.click(screen.getByRole('button', { name: 'Re-previsualizar' }));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    // The second request carries the column_mapping with the override applied.
    const body = mockFetch.mock.calls[1][1].body as FormData;
    const mapping = JSON.parse(body.get('column_mapping') as string);
    expect(mapping.Notas).toBe('model');
    // Auto-detected columns are pinned too (idempotent mapping).
    expect(mapping.VIN).toBe('frame');
    expect(mapping.Motor).toBe('motor');
  });

  it('omits a column from column_mapping when set back to "Sin mapear"', async () => {
    mockFetch.mockReturnValue(mockJson(previewResponse));
    render(<ImportsPage />);
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.xlsx'));
    await user.click(screen.getByRole('button', { name: 'Vista previa' }));

    await waitFor(() => {
      expect(screen.getByText('Hojas detectadas')).toBeInTheDocument();
    });

    // Color is auto-detected; set it to "Sin mapear" so it is dropped from the payload.
    await user.click(screen.getByRole('combobox', { name: 'Campo para Color' }));
    await user.click(screen.getByRole('option', { name: 'Sin mapear' }));
    await user.click(screen.getByRole('button', { name: 'Re-previsualizar' }));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
    const body = mockFetch.mock.calls[1][1].body as FormData;
    const mapping = JSON.parse(body.get('column_mapping') as string);
    expect(mapping.Color).toBeUndefined();
  });

  it('shows an error alert when the backend rejects the file', async () => {
    mockFetch.mockReturnValue(
      mockJson(
        { detail: 'Invalid file type. Only Excel (.xlsx, .xls) and CSV files are supported.' },
        { ok: false, status: 400 },
      ),
    );
    render(<ImportsPage />);
    await user.upload(screen.getByLabelText('Archivo'), createFile('inv.xlsx'));
    await user.click(screen.getByRole('button', { name: 'Vista previa' }));

    await waitFor(() => {
      expect(screen.getByText('No se pudo procesar el archivo')).toBeInTheDocument();
    });
    expect(
      screen.getByText('Invalid file type. Only Excel (.xlsx, .xls) and CSV files are supported.'),
    ).toBeInTheDocument();
  });
});