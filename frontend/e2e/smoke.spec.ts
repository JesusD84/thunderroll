import { test, expect } from '@playwright/test';

import { createSessionCookie, sessionCookieName } from './session';

test('the homepage asks for a session when there is none', async ({ page }) => {
  await page.goto('/');
  // The middleware is the one that answers: no session, no page.
  await page.waitForURL(/\/login/);
  await expect(page).toHaveTitle(/Thunderoll/);
});

test('the homepage loads for a signed-in user', async ({ page }) => {
  const value = await createSessionCookie({ role: 'admin' });
  await page.context().addCookies([
    { name: sessionCookieName(), value, domain: 'localhost', path: '/' },
  ]);

  await page.goto('/');
  await expect(page.locator('h1')).toContainText('Dashboard');
  await expect(page).toHaveTitle(/Thunderoll/);
});
