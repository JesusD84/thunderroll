import { test, expect, type Page } from '@playwright/test';

import { E2E_BACKEND_URL, createSessionCookie, sessionCookieName } from './session';

/**
 * The session is a REAL NextAuth session cookie: the middleware (server
 * side) and the API proxy read it, so mocking `/api/auth/session` in the
 * browser is not enough any more.
 */
async function signIn(page: Page, role: 'admin' | 'manager' | 'operator' = 'admin') {
  const value = await createSessionCookie({ role });
  await page.context().addCookies([
    { name: sessionCookieName(), value, domain: 'localhost', path: '/' },
  ]);
}

test.describe('Auth', () => {
  test('login page renders', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText('Iniciar Sesión');
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
  });

  test('does not show demo credentials on the public login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByText('Credenciales Demo:')).not.toBeVisible();
  });

  test('protected route redirects to login', async ({ page }) => {
    await page.goto('/units');
    // The middleware answers 307 with the callbackUrl, so the user lands
    // back where they were after signing in.
    await page.waitForURL(/\/login\?callbackUrl=/);
    await expect(page.locator('h2')).toContainText('Iniciar Sesión');
  });
});

test.describe('Authenticated', () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page, 'admin');
    await page.goto('/');
  });

  test('dashboard loads', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('dashboard renders the counts the API returned', async ({ page }) => {
    // Asserting only the heading proved nothing: with a stale mock the page
    // rendered zeros and the test still passed. These check the numbers the
    // dashboard actually shows.
    await expect(page.getByText('Total de Unidades').first().locator('..')).toContainText('42');
    await expect(page.getByText('Disponibles').first().locator('..')).toContainText('30');
    await expect(page.getByText('Vendidas').first().locator('..')).toContainText('8');
    await expect(page.getByText('En Tránsito').first().locator('..')).toContainText('4');
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
    // The data has to arrive too: a proxy that loses the trailing slash
    // would answer 404 and the table would stay empty.
    await expect(page.getByText('Honda')).toBeVisible();
    await expect(page.getByText('PCX')).toBeVisible();
    await expect(page.getByText('Unidades (2)')).toBeVisible();
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

test.describe('The token never reaches the browser', () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page, 'admin');
  });

  test('the session does not carry the access token', async ({ page }) => {
    const response = await page.request.get('/api/auth/session');
    const session = await response.json();

    expect(session.user.role).toBe('admin');
    expect(session.accessToken).toBeUndefined();
    expect(session.accessTokenExpiresAt).toBeUndefined();
  });

  test('the proxy forwards the credential to the backend', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Total de Unidades').first().locator('..')).toContainText('42');

    // The backend records what it received: the credential arrives there,
    // even though the browser never saw it.
    const received = await (await page.request.get(`${E2E_BACKEND_URL}/__mock/requests`)).json();
    const apiCalls = received.filter((entry: { path: string }) =>
      entry.path.startsWith('/api/v1/'),
    );

    expect(apiCalls.length).toBeGreaterThan(0);
    expect(apiCalls.every((entry: { hasAuthorization: boolean }) => entry.hasAuthorization)).toBe(
      true,
    );
    expect(apiCalls[0].authorizationScheme).toBe('Bearer');
  });
});

test.describe('Role gates in the middleware', () => {
  test('an admin can open the reports section', async ({ page }) => {
    await signIn(page, 'admin');
    await page.goto('/reports');
    await expect(page.locator('h1')).toContainText('Reportes');
  });

  test('an operator is sent away from the reports section', async ({ page }) => {
    await signIn(page, 'operator');
    await page.goto('/reports');
    await page.waitForURL(/\/units/);
  });

  test('an operator is sent away from the imports section', async ({ page }) => {
    await signIn(page, 'operator');
    await page.goto('/imports');
    await page.waitForURL(/\/units/);
  });

  test('an operator can open the units section', async ({ page }) => {
    await signIn(page, 'operator');
    await page.goto('/units');
    await expect(page.locator('h1')).toContainText('Gestión de Unidades');
  });
});
