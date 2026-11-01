import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mockSignOut = vi.fn(() => Promise.resolve());
vi.mock('next-auth/react', () => ({
  signOut: (...args: unknown[]) => mockSignOut(...args),
}));

const mockAssign = vi.fn();

beforeEach(() => {
  vi.resetModules();
  mockSignOut.mockClear();
  mockAssign.mockClear();
  vi.stubGlobal('location', { pathname: '/units/5', search: '?tab=1', assign: mockAssign });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('safeCallbackUrl', () => {
  it('keeps same-app relative paths', async () => {
    const { safeCallbackUrl } = await import('@/lib/session-expiry');
    expect(safeCallbackUrl('/units/5?tab=1')).toBe('/units/5?tab=1');
  });

  it('falls back to / for missing, external, or login targets', async () => {
    const { safeCallbackUrl } = await import('@/lib/session-expiry');
    expect(safeCallbackUrl(null)).toBe('/');
    expect(safeCallbackUrl('')).toBe('/');
    expect(safeCallbackUrl('//evil.com')).toBe('/');
    expect(safeCallbackUrl('https://evil.com')).toBe('/');
    expect(safeCallbackUrl('/login?x=1')).toBe('/');
  });
});

describe('handleSessionExpired', () => {
  it('signs out before navigating to /login with the reason and callbackUrl', async () => {
    const { handleSessionExpired } = await import('@/lib/session-expiry');
    await handleSessionExpired();

    expect(mockSignOut).toHaveBeenCalledWith({ redirect: false });
    expect(mockAssign).toHaveBeenCalledTimes(1);
    const target = new URL(mockAssign.mock.calls[0][0], 'http://localhost');
    expect(target.pathname).toBe('/login');
    expect(target.searchParams.get('reason')).toBe('expired');
    expect(target.searchParams.get('callbackUrl')).toBe('/units/5?tab=1');
  });

  it('runs one sign-out and one navigation for concurrent calls', async () => {
    const { handleSessionExpired } = await import('@/lib/session-expiry');
    await Promise.all([handleSessionExpired(), handleSessionExpired(), handleSessionExpired()]);

    expect(mockSignOut).toHaveBeenCalledTimes(1);
    expect(mockAssign).toHaveBeenCalledTimes(1);
  });

  it('still navigates when signOut fails', async () => {
    mockSignOut.mockRejectedValueOnce(new Error('network'));
    const { handleSessionExpired } = await import('@/lib/session-expiry');
    await handleSessionExpired();

    expect(mockAssign).toHaveBeenCalledTimes(1);
  });

  it('omits callbackUrl when already on /login', async () => {
    vi.stubGlobal('location', { pathname: '/login', search: '', assign: mockAssign });
    const { handleSessionExpired } = await import('@/lib/session-expiry');
    await handleSessionExpired();

    expect(mockAssign.mock.calls[0][0]).toBe('/login?reason=expired');
  });
});

describe('sessionAwareFetch / apiFetch', () => {
  it('triggers the expiry flow on 401 and never resolves', async () => {
    const fetchMock = vi.fn(() => Promise.resolve(new Response('{"detail":"Could not validate credentials"}', { status: 401 })));
    vi.stubGlobal('fetch', fetchMock);
    const { apiFetch } = await import('@/lib/api');

    let settled = false;
    apiFetch('/api/v1/units/', { token: 'expired' }).finally(() => { settled = true; });
    await new Promise((r) => setTimeout(r, 20));

    expect(mockSignOut).toHaveBeenCalledTimes(1);
    expect(mockAssign).toHaveBeenCalledTimes(1);
    expect(settled).toBe(false);
  });

  it('passes 403 through as an ApiError without signing out', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response('{"detail":"Not enough permissions"}', { status: 403 }))));
    const { apiFetch, ApiError } = await import('@/lib/api');

    await expect(apiFetch('/api/v1/imports/', { token: 'ok' })).rejects.toBeInstanceOf(ApiError);
    expect(mockSignOut).not.toHaveBeenCalled();
    expect(mockAssign).not.toHaveBeenCalled();
  });

  it('does not treat a 401 as expiry when skipSessionExpiry is set', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response('{"detail":"Incorrect username or password"}', { status: 401 }))));
    const { apiFetch, ApiError } = await import('@/lib/api');

    await expect(apiFetch('/api/v1/auth/login', { skipSessionExpiry: true })).rejects.toBeInstanceOf(ApiError);
    expect(mockSignOut).not.toHaveBeenCalled();
  });
});
