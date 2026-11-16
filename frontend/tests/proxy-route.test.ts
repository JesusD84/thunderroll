import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';

/**
 * The API proxy: the only way the browser reaches the backend.
 *
 * These tests cover the two things that must not break silently: the path
 * that reaches the backend, and the credential that travels with it.
 */

// The env has to exist before the route module is loaded (it reads
// BACKEND_URL when it is imported).
vi.hoisted(() => {
  process.env.BACKEND_URL = 'http://backend.test:8000';
  process.env.NEXTAUTH_SECRET = 'test-secret';
});

const mockGetToken = vi.fn();
vi.mock('next-auth/jwt', () => ({
  getToken: (...args: unknown[]) => mockGetToken(...args),
}));

import { GET, POST } from '@/app/api/proxy/[...path]/route';

const fetchMock = vi.fn();

function upstream(body: unknown, init: ResponseInit = {}) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      ...init,
    }),
  );
}

type NextRequestInit = ConstructorParameters<typeof NextRequest>[1];

function request(path: string, init: NextRequestInit = {}) {
  return new NextRequest(`http://localhost:3000/api/proxy${path}`, init);
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGetToken.mockResolvedValue({ accessToken: 'backend-access-token' });
  fetchMock.mockImplementation(() => upstream({ ok: true }));
  vi.stubGlobal('fetch', fetchMock);
});

describe('The API proxy', () => {
  it('forwards the request to the backend with the session credential', async () => {
    const response = await GET(request('/api/v1/units/?skip=0&limit=20'), {
      params: { path: ['api', 'v1', 'units'] },
    });

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ ok: true });

    const [target, init] = fetchMock.mock.calls[0];
    expect(String(target)).toBe('http://backend.test:8000/api/v1/units/?skip=0&limit=20');

    const headers = new Headers(init.headers);
    expect(headers.get('Authorization')).toBe('Bearer backend-access-token');
  });

  it('does not repeat the api prefix', async () => {
    // The client sends the backend path as it is: the proxy has to take the
    // prefix off before putting it back on.
    await GET(request('/api/v1/reports/dashboard'), {
      params: { path: ['api', 'v1', 'reports', 'dashboard'] },
    });

    const [target] = fetchMock.mock.calls[0];
    expect(String(target)).toBe('http://backend.test:8000/api/v1/reports/dashboard');
  });

  it('answers 401 when there is no session', async () => {
    mockGetToken.mockResolvedValue(null);

    const response = await GET(request('/api/v1/units/'), {
      params: { path: ['api', 'v1', 'units'] },
    });

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('answers 401 when the session has no backend token', async () => {
    mockGetToken.mockResolvedValue({ role: 'admin' });

    const response = await GET(request('/api/v1/units/'), {
      params: { path: ['api', 'v1', 'units'] },
    });

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('never lets the browser reach the auth endpoints', async () => {
    const response = await GET(request('/api/v1/auth/login'), {
      params: { path: ['api', 'v1', 'auth', 'login'] },
    });

    expect(response.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects a path that tries to climb out of the API', async () => {
    const response = await GET(request('/api/v1/../secrets'), {
      params: { path: ['api', 'v1', '..', 'secrets'] },
    });

    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('forwards the method and the body of a write', async () => {
    await POST(request('/api/v1/units/', { method: 'POST' }), {
      params: { path: ['api', 'v1', 'units'] },
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe('POST');
    expect(init.body).toBeInstanceOf(ArrayBuffer);
  });

  it('does not forward the cookies of the browser', async () => {
    await GET(request('/api/v1/units/', { headers: { cookie: 'sesion=secreto' } }), {
      params: { path: ['api', 'v1', 'units'] },
    });

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init.headers);
    expect(headers.get('cookie')).toBeNull();
    expect(headers.get('authorization')).toBe('Bearer backend-access-token');
  });

  it('answers 502 when the backend is unreachable', async () => {
    fetchMock.mockRejectedValue(new Error('ECONNREFUSED'));

    const response = await GET(request('/api/v1/units/'), {
      params: { path: ['api', 'v1', 'units'] },
    });

    expect(response.status).toBe(502);
  });

  it('follows the redirect of the backend on the server', async () => {
    // The backend answers a path that misses its trailing slash with a
    // redirect. It has to be followed here: if it reached the browser it
    // would point outside this origin.
    fetchMock
      .mockReturnValueOnce(
        Promise.resolve(
          new Response(null, {
            status: 307,
            headers: { location: '/api/v1/units/' },
          }),
        ),
      )
      .mockReturnValueOnce(upstream({ ok: true }));

    const response = await GET(request('/api/v1/units'), {
      params: { path: ['api', 'v1', 'units'] },
    });

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ ok: true });

    const [first] = fetchMock.mock.calls[0];
    const [second] = fetchMock.mock.calls[1];
    expect(String(first)).toBe('http://backend.test:8000/api/v1/units');
    expect(String(second)).toBe('http://backend.test:8000/api/v1/units/');
  });

  it('does not follow a redirect that leaves the backend', async () => {
    fetchMock.mockReturnValue(
      Promise.resolve(
        new Response(null, {
          status: 302,
          headers: { location: 'https://otro-sitio.test/robo' },
        }),
      ),
    );

    const response = await GET(request('/api/v1/units'), {
      params: { path: ['api', 'v1', 'units'] },
    });

    expect(response.status).toBe(302);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
