import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mockResponse } from './mocks/response';

const mockSignOut = vi.fn((..._args: unknown[]) => Promise.resolve());
const mockGetSession = vi.fn();

vi.mock('next-auth/react', () => ({
  signOut: (...args: unknown[]) => mockSignOut(...args),
  getSession: (...args: unknown[]) => mockGetSession(...args),
}));

const mockAssign = vi.fn();

beforeEach(() => {
  vi.resetModules();
  mockSignOut.mockClear();
  mockGetSession.mockReset();
  mockAssign.mockClear();
  vi.stubGlobal('location', { pathname: '/units/5', search: '', assign: mockAssign });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** 401 en la primera llamada, 200 en la siguiente: la sesión se renovó. */
function unauthorizedThenOk() {
  let calls = 0;
  return vi.fn((_input: RequestInfo | URL, _init?: RequestInit) => {
    calls += 1;
    return Promise.resolve(
      calls === 1
        ? mockResponse({ detail: 'Could not validate credentials' }, { status: 401 })
        : mockResponse({ ok: true }),
    );
  });
}

/** 401 siempre: la sesión está muerta. */
function alwaysUnauthorized() {
  return vi.fn((_input: RequestInfo | URL, _init?: RequestInit) =>
    Promise.resolve(
      mockResponse({ detail: 'Could not validate credentials' }, { status: 401 }),
    ),
  );
}

describe('apiFetch con renovación de sesión', () => {
  it('renueva la sesión y reintenta la petición en vez de cerrar la sesión', async () => {
    const fetchMock = unauthorizedThenOk();
    vi.stubGlobal('fetch', fetchMock);
    mockGetSession.mockResolvedValue({ user: { role: 'admin' } });

    const { apiFetch } = await import('@/lib/api');
    const data = await apiFetch('/api/v1/units/');

    expect(data).toEqual({ ok: true });
    expect(mockGetSession).toHaveBeenCalledTimes(1);
    // La sesión sigue viva: no se cierra ni se navega al login.
    expect(mockSignOut).not.toHaveBeenCalled();
    expect(mockAssign).not.toHaveBeenCalled();
  });

  it('reintenta la misma petición: misma url, mismo método y mismo cuerpo', async () => {
    const fetchMock = unauthorizedThenOk();
    vi.stubGlobal('fetch', fetchMock);
    mockGetSession.mockResolvedValue({ user: { role: 'admin' } });

    const { apiFetch } = await import('@/lib/api');
    await apiFetch('/api/v1/units/', { method: 'POST', json: { a: 1 } });

    const calls = fetchMock.mock.calls;
    expect(calls).toHaveLength(2);
    expect(calls[0][0]).toBe(calls[1][0]);
    expect(calls[0][0]).toBe('/api/proxy/api/v1/units/');
    expect(calls[1][1]?.method).toBe('POST');
    expect(calls[1][1]?.body).toBe(JSON.stringify({ a: 1 }));
  });

  it('no manda ninguna cabecera Authorization: la credencial va en la cookie', async () => {
    const fetchMock = unauthorizedThenOk();
    vi.stubGlobal('fetch', fetchMock);
    mockGetSession.mockResolvedValue({ user: { role: 'admin' } });

    const { apiFetch } = await import('@/lib/api');
    await apiFetch('/api/v1/units/');

    const calls = fetchMock.mock.calls;
    for (const call of calls) {
      expect(new Headers(call[1]?.headers).get('Authorization')).toBeNull();
    }
  });

  it('cierra la sesión cuando el reintento también responde 401', async () => {
    vi.stubGlobal('fetch', alwaysUnauthorized());
    mockGetSession.mockResolvedValue({ user: { role: 'admin' } });

    const { apiFetch } = await import('@/lib/api');
    let settled = false;
    apiFetch('/api/v1/units/').finally(() => {
      settled = true;
    });
    await new Promise((r) => setTimeout(r, 20));

    expect(mockSignOut).toHaveBeenCalledWith({ redirect: false });
    expect(mockAssign).toHaveBeenCalledTimes(1);
    const target = new URL(mockAssign.mock.calls[0][0], 'http://localhost');
    expect(target.pathname).toBe('/login');
    expect(target.searchParams.get('reason')).toBe('expired');
    expect(settled).toBe(false);
  });

  it('cierra la sesión cuando la renovación no devuelve sesión', async () => {
    vi.stubGlobal('fetch', alwaysUnauthorized());
    mockGetSession.mockResolvedValue(null);

    const { apiFetch } = await import('@/lib/api');
    let settled = false;
    apiFetch('/api/v1/units/').finally(() => {
      settled = true;
    });
    await new Promise((r) => setTimeout(r, 20));

    expect(mockSignOut).toHaveBeenCalledWith({ redirect: false });
    expect(mockAssign).toHaveBeenCalledTimes(1);
    expect(settled).toBe(false);
  });

  it('comparte una sola renovación entre las peticiones que fallan a la vez', async () => {
    vi.stubGlobal('fetch', alwaysUnauthorized());
    mockGetSession.mockResolvedValue({ user: { role: 'admin' } });

    const { apiFetch } = await import('@/lib/api');
    void apiFetch('/api/v1/units/');
    void apiFetch('/api/v1/locations/');
    await new Promise((r) => setTimeout(r, 20));

    expect(mockGetSession).toHaveBeenCalledTimes(1);
  });

  it('no intenta renovar cuando el 401 es esperado (login)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          mockResponse({ detail: 'Incorrect username or password' }, { status: 401 }),
        ),
      ),
    );

    const { apiFetch, ApiError } = await import('@/lib/api');
    await expect(
      apiFetch('/api/v1/auth/login', { skipSessionExpiry: true }),
    ).rejects.toBeInstanceOf(ApiError);

    expect(mockGetSession).not.toHaveBeenCalled();
    expect(mockSignOut).not.toHaveBeenCalled();
    expect(mockAssign).not.toHaveBeenCalled();
  });
});
