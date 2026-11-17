import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import {
  REFRESH_MARGIN_MS,
  refreshBackendToken,
  shouldRefreshAccessToken,
} from '@/lib/backend-auth';
import { mockResponse } from './mocks/response';

const NOW = 1_700_000_000_000;

describe('shouldRefreshAccessToken', () => {
  it('renueva cuando el token ya venció', () => {
    expect(shouldRefreshAccessToken(NOW - 1000, NOW)).toBe(true);
  });

  it('renueva cuando le queda menos de un minuto', () => {
    expect(shouldRefreshAccessToken(NOW + 30_000, NOW)).toBe(true);
    expect(shouldRefreshAccessToken(NOW + REFRESH_MARGIN_MS, NOW)).toBe(true);
  });

  it('no renueva si el token todavía aguanta', () => {
    expect(shouldRefreshAccessToken(NOW + 10 * 60_000, NOW)).toBe(false);
  });

  it('no renueva sin fecha de expiración', () => {
    expect(shouldRefreshAccessToken(undefined, NOW)).toBe(false);
    expect(shouldRefreshAccessToken(null, NOW)).toBe(false);
    expect(shouldRefreshAccessToken(Number.NaN, NOW)).toBe(false);
    expect(shouldRefreshAccessToken('en una hora', NOW)).toBe(false);
  });
});

describe('refreshBackendToken', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('devuelve el token nuevo cuando el backend lo acepta', async () => {
    const body = {
      access_token: 'nuevo',
      refresh_token: 'refresh',
      token_type: 'bearer',
      expires_in: 3600,
    };
    vi.mocked(fetch).mockResolvedValue(
      mockResponse(body, { status: 200 }) as unknown as Response,
    );

    const result = await refreshBackendToken('refresh');

    expect(result).toEqual(body);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect((init?.headers as Record<string, string>).Authorization).toBe(
      'Bearer refresh',
    );
  });

  it('devuelve null cuando el refresh token ya no vale', async () => {
    vi.mocked(fetch).mockResolvedValue(
      mockResponse({ detail: 'Invalid refresh token' }, { status: 401 }) as unknown as Response,
    );

    expect(await refreshBackendToken('refresh')).toBeNull();
  });

  it('devuelve null cuando el backend no contesta', async () => {
    vi.mocked(fetch).mockRejectedValue(new Error('network down'));

    expect(await refreshBackendToken('refresh')).toBeNull();
  });
});
