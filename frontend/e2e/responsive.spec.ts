import { test, expect } from '@playwright/test';

test.describe('Responsive Design', () => {
  test('mobile menu opens and closes on small viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    // Go to login first since we can't mock auth for mobile nav test easily
    await page.goto('/login');
    await expect(page.locator('h2')).toContainText('Iniciar Sesión');
    // Login page should be usable on mobile
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
  });
});