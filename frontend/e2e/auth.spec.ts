import { test, expect } from '@playwright/test';

const mockSession = {
  user: { id: '1', email: 'admin@thunderrol.com', name: 'Admin User', role: 'admin' },
  accessToken: 'mock-jwt-token',
  expires: new Date(Date.now() + 86400000).toISOString(),
};

const mockDashboard = {
  total_units: 42, available_units: 30, sold_units: 8, in_transit_units: 4,
  inventory_by_location: [{ location: 'Bodega Central', count: 25 }],
  sales_by_month: [{ month: '2025-05', count: 3 }],
  recent_transfers: [], recent_imports: [],
};

const mockUnits = [
  { id: 1, brand: 'Honda', model: 'PCX', engine_number: 'ENG001', status: 'AVAILABLE', location_name: 'Bodega Central' },
  { id: 2, brand: 'Yamaha', model: 'NMAX', engine_number: 'ENG002', status: 'SOLD', location_name: 'Sucursal Norte' },
];

async function setupMocks(page: any) {
  await page.route('**/api/auth/session', r => r.fulfill({ json: mockSession }));
  await page.route('**/api/auth/csrf', r => r.fulfill({ json: { csrfToken: 'x' } }));
  await page.route('**/api/auth/signout', r => r.fulfill({ json: { url: '/login' } }));
  await page.route('**/api/v1/reports/dashboard', r => r.fulfill({ json: mockDashboard }));
  await page.route('**/api/v1/units/**', r => r.fulfill({ json: mockUnits }));
  await page.route('**/api/v1/locations/', r => r.fulfill({ json: [{ id: 1, name: 'Bodega Central' }] }));
  await page.route('**/api/v1/user/', r => r.fulfill({ json: [{ id: 1, email: 'a@t.com', first_name: 'A', last_name: 'U', role: 'admin', is_active: true }] }));
}

test.describe('Auth', () => {
  test('login page renders', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText('Iniciar Sesión');
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
  });

  test('shows demo credentials', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByText('Credenciales Demo:')).toBeVisible();
  });

  test('protected route redirects to login', async ({ page }) => {
    await page.goto('/units');
    await page.waitForURL('/login');
  });
});

test.describe('Authenticated', () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto('/');
  });

  test('dashboard loads', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('nav links visible', async ({ page }) => {
    await expect(page.getByText('Dashboard').first()).toBeVisible();
    await expect(page.getByText('Unidades').first()).toBeVisible();
    await expect(page.getByText('Importar').first()).toBeVisible();
    await expect(page.getByText('Transferencias').first()).toBeVisible();
    await expect(page.getByText('Reportes').first()).toBeVisible();
    await expect(page.getByText('Configuración').first()).toBeVisible();
  });

  test('navigates to Units', async ({ page }) => {
    await page.getByText('Unidades').first().click();
    await page.waitForURL('/units');
    await expect(page.locator('h1')).toContainText('Unidades');
  });

  test('navigates to Imports', async ({ page }) => {
    await page.getByText('Importar').first().click();
    await page.waitForURL('/imports');
  });

  test('navigates to Transfers', async ({ page }) => {
    await page.getByText('Transferencias').first().click();
    await page.waitForURL('/transfers');
  });

  test('navigates to Reports', async ({ page }) => {
    await page.getByText('Reportes').first().click();
    await page.waitForURL('/reports');
  });

  test('navigates to Settings', async ({ page }) => {
    await page.getByText('Configuración').first().click();
    await page.waitForURL('/settings');
  });
});