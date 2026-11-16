import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

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

/** Respuesta 401 para el token viejo y 200 para el nuevo. */
function expiredThenOk(newToken: string) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers);
    const auth = headers.get('Authorization');
    if (auth === `Bearer ${newToken}`) {
      return Promise.resolve(new Response('{"ok":true}', { status: 200 }));
    }
    return Promise.resolve(
      new Response('{"detail":"Could not validate credentials"}', { status: 401 }),
    );
  });
}

describe('apiFetch con refresco de token', () => {
  it('renueva el token y reintenta la petición en vez de cerrar la sesión', async () => {
    vi.stubGlobal('fetch', expiredThenOk('token-nuevo'));
    mockGetSession.mockResolvedValue({ accessToken: 'token-nuevo' });

    const { apiFetch } = await import('@/lib/api');
    const data = await apiFetch('/api/v1/units/', { token: 'token-viejo' });

    expect(data).toEqual({ ok: true });
    expect(mockGetSession).toHaveBeenCalledTimes(1);
    // La sesión sigue viva: no se cierra ni se navega al login.
    expect(mockSignOut).not.toHaveBeenCalled();
    expect(mockAssign).not.toHaveBeenCalled();
  });

  it('reintenta con el token nuevo, no con el viejo', async () => {
    const fetchMock = expiredThenOk('token-nuevo');
    vi.stubGlobal('fetch', fetchMock);
    mockGetSession.mockResolvedValue({ accessToken: 'token-nuevo' });

    const { apiFetch } = await import('@/lib/api');
    await apiFetch('/api/v1/units/', { token: 'token-viejo' });

    const calls = fetchMock.mock.calls;
    expect(calls).toHaveLength(2);
    const retriedHeaders = new Headers(calls[1][1]?.headers);
    expect(retriedHeaders.get('Authorization')).toBe('Bearer token-nuevo');
  });

  it('cierra la sesión cuando el refresco no devuelve token', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response('{"detail":"Could not validate credentials"}', { status: 401 }),
        ),
      ),
    );
    mockGetSession.mockResolvedValue(null);

    const { apiFetch } = await import('@/lib/api');
    let settled = false;
    apiFetch('/api/v1/units/', { token: 'token-viejo' }).finally(() => {
      settled = true;
    });
    await new Promise((r) => setTimeout(r, 20));

    expect(mockSignOut).toHaveBeenCalledWith({ redirect: false });
    expect(mockAssign).toHaveBeenCalledTimes(1);
    expect(settled).toBe(false);
  });

  it('cierra la sesión cuando el refresco devuelve el mismo token', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response('{"detail":"Could not validate credentials"}', { status: 401 }),
        ),
      ),
    );
    mockGetSession.mockResolvedValue({ accessToken: 'token-viejo' });

    const { apiFetch } = await import('@/lib/api');
    let settled = false;
    apiFetch('/api/v1/units/', { token: 'token-viejo' }).finally(() => {
      settled = true;
    });
    await new Promise((r) => setTimeout(r, 20));

    expect(mockSignOut).toHaveBeenCalledTimes(1);
    expect(settled).toBe(false);
  });

  it('cierra la sesión cuando el reintento también responde 401', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response('{"detail":"Could not validate credentials"}', { status: 401 }),
        ),
      ),
    );
    mockGetSession.mockResolvedValue({ accessToken: 'token-nuevo' });

    const { apiFetch } = await import('@/lib/api');
    let settled = false;
    apiFetch('/api/v1/units/', { token: 'token-viejo' }).finally(() => {
      settled = true;
    });
    await new Promise((r) => setTimeout(r, 20));

    expect(mockSignOut).toHaveBeenCalledTimes(1);
    expect(settled).toBe(false);
  });

  it('comparte un solo refresco entre las peticiones que fallan a la vez', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(
          new Response('{"detail":"Could not validate credentials"}', { status: 401 }),
        ),
      ),
    );
    mockGetSession.mockResolvedValue({ accessToken: 'token-nuevo' });

    const { apiFetch } = await import('@/lib/api');
    void apiFetch('/api/v1/units/', { token: 'token-viejo' });
    void apiFetch('/api/v1/locations/', { token: 'token-viejo' });
    await new Promise((r) => setTimeout(r, 20));

    expect(mockGetSession).toHaveBeenCalledTimes(1);
  });

  it('no intenta refrescar cuando el 401 es esperado (login)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve(new Response('{"detail":"Incorrect username or password"}', { status: 401 })),
      ),
    );

    const { apiFetch, ApiError } = await import('@/lib/api');
    await expect(
      apiFetch('/api/v1/auth/login', { skipSessionExpiry: true }),
    ).rejects.toBeInstanceOf(ApiError);

    expect(mockGetSession).not.toHaveBeenCalled();
    expect(mockSignOut).not.toHaveBeenCalled();
  });
});
