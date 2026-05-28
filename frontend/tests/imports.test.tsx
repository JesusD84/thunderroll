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

function createFile(name: string, type: string): File {
  return new File(['test content'], name, { type });
}

// ============================================================
// ImportsPage
// ============================================================
describe('ImportsPage', () => {
  const user = userEvent.setup({ pointerEventsCheck: 0 });

  it('renders page with header and form', () => {
    render(<ImportsPage />);
    expect(screen.getByText('Importar Inventario')).toBeInTheDocument();
    expect(screen.getByText('Importa unidades desde archivos Excel del proveedor')).toBeInTheDocument();
    expect(screen.getByLabelText('Código de Lote *')).toBeInTheDocument();
    expect(screen.getByLabelText('Factura Proveedor *')).toBeInTheDocument();
    expect(screen.getByLabelText('Archivo Excel')).toBeInTheDocument();
  });

  it('renders instructions card with required columns', () => {
    render(<ImportsPage />);
    expect(screen.getByText('Instrucciones')).toBeInTheDocument();
    expect(screen.getByText('Columnas Requeridas')).toBeInTheDocument();
    expect(screen.getByText('Formato de Datos')).toBeInTheDocument();
    expect(screen.getByText('Descargar Plantilla')).toBeInTheDocument();
  });

  it('shows filename after file selection', async () => {
    render(<ImportsPage />);
    const fileInput = screen.getByLabelText('Archivo Excel');
    const file = createFile('inventario.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    await user.upload(fileInput, file);
    expect(screen.getByText('Archivo seleccionado: inventario.xlsx')).toBeInTheDocument();
  });

  it('preview button is disabled when fields are empty', () => {
    render(<ImportsPage />);
    const previewBtn = screen.getByRole('button', { name: 'Vista Previa' });
    expect(previewBtn).toBeDisabled();
  });

  it('preview button is disabled when only file is selected', async () => {
    render(<ImportsPage />);
    const fileInput = screen.getByLabelText('Archivo Excel');
    await user.upload(fileInput, createFile('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
    const previewBtn = screen.getByRole('button', { name: 'Vista Previa' });
    expect(previewBtn).toBeDisabled();
  });

  it('preview button enabled when all required fields are filled', async () => {
    render(<ImportsPage />);
    await user.type(screen.getByLabelText('Código de Lote *'), 'BATCH_001');
    await user.type(screen.getByLabelText('Factura Proveedor *'), 'INV-001');
    const fileInput = screen.getByLabelText('Archivo Excel');
    await user.upload(fileInput, createFile('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
    const previewBtn = screen.getByRole('button', { name: 'Vista Previa' });
    expect(previewBtn).not.toBeDisabled();
  });

  it('shows preview table after processing', async () => {
    render(<ImportsPage />);
    await user.type(screen.getByLabelText('Código de Lote *'), 'BATCH_001');
    await user.type(screen.getByLabelText('Factura Proveedor *'), 'INV-001');
    await user.upload(screen.getByLabelText('Archivo Excel'), createFile('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      expect(screen.getByText('Vista Previa de Importación')).toBeInTheDocument();
    }, { timeout: 3000 });
    expect(screen.getByText('Honda PCX')).toBeInTheDocument();
    expect(screen.getByText('Yamaha NMAX')).toBeInTheDocument();
  });

  it('shows error badges for rows with errors in preview', async () => {
    render(<ImportsPage />);
    await user.type(screen.getByLabelText('Código de Lote *'), 'BATCH_001');
    await user.type(screen.getByLabelText('Factura Proveedor *'), 'INV-001');
    await user.upload(screen.getByLabelText('Archivo Excel'), createFile('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      const errorBadges = screen.getAllByText('Error');
      expect(errorBadges.length).toBe(1);
    }, { timeout: 3000 });
    const okBadges = screen.getAllByText('OK');
    expect(okBadges.length).toBe(2);
  });

  it('shows import button after preview with unit count', async () => {
    render(<ImportsPage />);
    await user.type(screen.getByLabelText('Código de Lote *'), 'BATCH_001');
    await user.type(screen.getByLabelText('Factura Proveedor *'), 'INV-001');
    await user.upload(screen.getByLabelText('Archivo Excel'), createFile('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      expect(screen.getByText('Importar (3 unidades)')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('import button is disabled when errors exist', async () => {
    render(<ImportsPage />);
    await user.type(screen.getByLabelText('Código de Lote *'), 'BATCH_001');
    await user.type(screen.getByLabelText('Factura Proveedor *'), 'INV-001');
    await user.upload(screen.getByLabelText('Archivo Excel'), createFile('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      const importBtn = screen.getByRole('button', { name: /Importar/ });
      expect(importBtn).toBeDisabled();
    }, { timeout: 3000 });
  });

  it('shows error alert with error details', async () => {
    render(<ImportsPage />);
    await user.type(screen.getByLabelText('Código de Lote *'), 'BATCH_001');
    await user.type(screen.getByLabelText('Factura Proveedor *'), 'INV-001');
    await user.upload(screen.getByLabelText('Archivo Excel'), createFile('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
    await user.click(screen.getByRole('button', { name: 'Vista Previa' }));
    await waitFor(() => {
      expect(screen.getByText('Errores encontrados:')).toBeInTheDocument();
      expect(screen.getByText('Fila 4: Número de motor faltante')).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});