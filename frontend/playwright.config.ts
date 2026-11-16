import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env.CI;

// El puerto se puede mover con E2E_PORT para correr la suite sin tumbar un
// dev server que ya esté ocupando el 3000.
const port = process.env.E2E_PORT || '3000';
const baseURL = `http://localhost:${port}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  // En CI el reporter de GitHub deja el fallo anotado en el PR, y el HTML
  // queda como artefacto para abrirlo cuando haga falta. En local, el HTML
  // se abre solo al terminar.
  reporter: isCI
    ? [['github'], ['html', { open: 'never' }]]
    : 'html',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    // En CI se compila y arranca la build de producción: sin file watcher y
    // más cerca de lo que ve el usuario. En local, el dev server.
    command: isCI
      ? `npm run build && npx next start -p ${port}`
      : `npx next dev -p ${port}`,
    url: baseURL,
    reuseExistingServer: !isCI,
    // La build en frío en un runner puede tardar: sin esto el job falla por
    // timeout antes de que el servidor esté listo.
    timeout: 180_000,
  },
});
