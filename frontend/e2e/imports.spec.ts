import { test, expect, type Page } from '@playwright/test';
import fs from 'fs';
import os from 'os';
import path from 'path';

import { createSessionCookie, sessionCookieName } from './session';

// The four real supplier spreadsheets live in the backend fixtures.
const SAMPLES_DIR = path.resolve(__dirname, '../../backend/tests/fixtures/samples');

const SAMPLE_FILES = [
  '2025057车 Frame number and motor number.xlsx',
  'Frame number for tricycle .xls',
  'frame number and motor number for electric bike.xlsx',
  'jc  电机车架号.xl.xlsx',
];

async function signIn(page: Page) {
  const value = await createSessionCookie({ role: 'admin' });
  await page.context().addCookies([
    { name: sessionCookieName(), value, domain: 'localhost', path: '/' },
  ]);
}

/**
 * A copy of a sample whose name asks the mock backend for a preview with
 * problems. The name is the signal: the mock has no shared state, because
 * the tests run in parallel.
 */
const INVALID_SAMPLE = path.join(os.tmpdir(), 'invalid-rows-sample.xlsx');

test.describe('Imports e2e (real samples)', () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page);
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
    fs.copyFileSync(path.join(SAMPLES_DIR, SAMPLE_FILES[0]), INVALID_SAMPLE);

    await page.goto('/imports');
    await page.setInputFiles('#file', INVALID_SAMPLE);
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
