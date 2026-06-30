import { test, expect, type Page } from '@playwright/test';
import path from 'path';

// The four real supplier spreadsheets live in the backend fixtures.
const SAMPLES_DIR = path.resolve(__dirname, '../../backend/tests/fixtures/samples');

const SAMPLE_FILES = [
  '2025057车 Frame number and motor number.xlsx',
  'Frame number for tricycle .xls',
  'frame number and motor number for electric bike.xlsx',
  'jc  电机车架号.xl.xlsx',
];

const mockSession = {
  user: { id: '1', email: 'admin@thunderrol.com', name: 'Admin User', role: 'admin' },
  accessToken: 'mock-jwt-token',
  expires: new Date(Date.now() + 86400000).toISOString(),
};

const uploadResult = {
  import_id: 7,
  message: 'Importación realizada',
  total_records: 2,
  successful_imports: 2,
  failed_imports: 0,
};

/** Pull the uploaded filename out of the multipart body so the mock can echo it. */
function uploadedFilename(postData: string | null): string {
  if (!postData) return 'archivo';
  const match = postData.match(/filename="([^"]+)"/);
  return match ? match[1] : 'archivo';
}

function previewFor(filename: string, overrides: Record<string, unknown> = {}) {
  return {
    filename,
    sheets: [
      {
        sheet: 'Hoja1',
        has_header: true,
        columns: ['Frame No.', 'Motor No.', 'Color', 'Model'],
        column_mapping: {
          'Frame No.': 'frame',
          'Motor No.': 'motor',
          Color: 'color',
          Model: 'model',
        },
        mapped_fields: { frame: 'Frame No.', motor: 'Motor No.', color: 'Color', model: 'Model' },
        rows: 2,
      },
    ],
    detected_fields: ['frame', 'motor', 'color', 'model'],
    preview_data: [
      { sheet: 'Hoja1', frame: 'LXYTCKPA9R0123456', motor: 'EM0987654321', color: 'rojo', model: 'X3' },
    ],
    invalid_rows: [],
    invalid_rows_count: 0,
    issues: [],
    validation: { is_valid: true, message: 'Archivo válido' },
    ...overrides,
  };
}

async function setupAuth(page: Page) {
  await page.route('**/api/auth/session', (r) => r.fulfill({ json: mockSession }));
  await page.route('**/api/auth/csrf', (r) => r.fulfill({ json: { csrfToken: 'x' } }));
}

test.describe('Imports e2e (real samples)', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuth(page);
    await page.route('**/api/v1/imports/preview', async (route) => {
      const filename = uploadedFilename(route.request().postData());
      await route.fulfill({ json: previewFor(filename) });
    });
    await page.route('**/api/v1/imports/upload', (route) => route.fulfill({ json: uploadResult }));
  });

  for (const sample of SAMPLE_FILES) {
    test(`previews and imports "${sample}"`, async ({ page }) => {
      await page.goto('/imports');

      await page.setInputFiles('#file', path.join(SAMPLES_DIR, sample));
      await expect(page.getByText(`Archivo seleccionado: ${sample}`)).toBeVisible();

      await page.getByRole('button', { name: 'Vista previa' }).click();

      await expect(page.getByRole('heading', { name: `Vista previa de ${sample}` })).toBeVisible();
      await expect(page.getByText('Archivo listo')).toBeVisible();
      await expect(page.getByText('Campos detectados:')).toBeVisible();

      await page.getByRole('button', { name: 'Importar al inventario' }).click();

      await expect(
        page.getByRole('heading', { name: 'Importación completada' }),
      ).toBeVisible();
      await expect(page.getByText('importación #7')).toBeVisible();
    });
  }

  test('preview with invalid rows does not block import', async ({ page }) => {
    await page.unroute('**/api/v1/imports/preview');
    await page.route('**/api/v1/imports/preview', async (route) => {
      const filename = uploadedFilename(route.request().postData());
      await route.fulfill({
        json: previewFor(filename, {
          invalid_rows: [{ sheet: 'Hoja1', row: 3, reasons: ['Falta chasis'], data: {} }],
          invalid_rows_count: 1,
          issues: [{ level: 'warning', message: 'Algunas filas sin identificador', sheet: 'Hoja1' }],
          validation: { is_valid: false, message: 'Hay filas con problemas' },
        }),
      });
    });

    await page.goto('/imports');
    await page.setInputFiles('#file', path.join(SAMPLES_DIR, SAMPLE_FILES[0]));
    await page.getByRole('button', { name: 'Vista previa' }).click();

    await expect(page.getByText('Filas con problemas (1)')).toBeVisible();
    // Import is still allowed despite invalid rows.
    const importButton = page.getByRole('button', { name: 'Importar al inventario' });
    await expect(importButton).toBeEnabled();
    await importButton.click();
    await expect(
      page.getByRole('heading', { name: 'Importación completada' }),
    ).toBeVisible();
  });
});
