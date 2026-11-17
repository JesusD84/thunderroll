import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env.CI;

// El puerto se puede mover con E2E_PORT para correr la suite sin tumbar un
// dev server que ya esté ocupando el 3000.
const port = process.env.E2E_PORT || '3000';
const baseURL = `http://localhost:${port}`;

// El backend de mentira. Desde que el navegador ya no habla con la API
// directamente (todo pasa por el proxy del servidor), la API tiene que
// existir en algún lado para que los tests tengan contra qué responder.
const backendPort = process.env.E2E_BACKEND_PORT || '8017';
const backendURL = `http://localhost:${backendPort}`;

// El middleware y el proxy leen la cookie de sesión con este secreto, y el
// test la firma con el mismo: si no coinciden, el servidor no abre la
// sesión. El valor tiene que estar disponible al COMPILAR (el middleware
// lo lleva embebido) y al correr los tests.
const secret = process.env.NEXTAUTH_SECRET || 'e2e-session-secret';
process.env.NEXTAUTH_SECRET = secret;
process.env.E2E_BACKEND_PORT = backendPort;

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
  webServer: [
    {
      // La API de mentira: responde lo que la UI lee y exige el header
      // Authorization (si el proxy no lo reenvía, el test falla).
      command: `node e2e/mock-backend.mjs`,
      url: `${backendURL}/health`,
      env: { PORT: backendPort },
      reuseExistingServer: !isCI,
      timeout: 30_000,
    },
    {
      // En CI se compila y arranca la build de producción: sin file watcher y
      // más cerca de lo que ve el usuario. En local, el dev server.
      command: isCI
        ? `npm run build && npx next start -p ${port}`
        : `npx next dev -p ${port}`,
      url: baseURL,
      env: {
        BACKEND_URL: backendURL,
        NEXTAUTH_URL: baseURL,
        NEXTAUTH_SECRET: secret,
      },
      reuseExistingServer: !isCI,
      // La build en frío en un runner puede tardar: sin esto el job falla por
      // timeout antes de que el servidor esté listo.
      timeout: 180_000,
    },
  ],
});
