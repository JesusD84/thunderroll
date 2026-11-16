/**
 * Session helpers for the e2e suite.
 *
 * The middleware and the API proxy read the session from the cookie, so the
 * tests need a REAL NextAuth session cookie: the browser-level mock of
 * `/api/auth/session` that the suite used before is not enough any more.
 *
 * The cookie is encoded with the same secret the Next.js server uses (the
 * one in `NEXTAUTH_SECRET`), so the server can decrypt it.
 */

import { encode } from 'next-auth/jwt';

export const E2E_BACKEND_PORT = process.env.E2E_BACKEND_PORT || '8017';
export const E2E_BACKEND_URL = `http://localhost:${E2E_BACKEND_PORT}`;

export type TestRole = 'admin' | 'manager' | 'operator';

export interface TestSessionOptions {
  role?: TestRole;
  id?: string;
  name?: string;
  email?: string;
}

/**
 * The cookie NextAuth uses for the session, derived the same way the app
 * does (secure variant when the app is served over https).
 */
export function sessionCookieName(): string {
  const secure = process.env.NEXTAUTH_URL?.startsWith('https://') ?? false;
  return secure ? '__Secure-next-auth.session-token' : 'next-auth.session-token';
}

/** The session cookie, encrypted exactly as NextAuth would encrypt it. */
export async function createSessionCookie(
  options: TestSessionOptions = {},
): Promise<string> {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) {
    throw new Error('NEXTAUTH_SECRET must be set to sign the e2e session cookie');
  }

  const role = options.role ?? 'admin';

  return encode({
    token: {
      sub: options.id ?? '1',
      id: options.id ?? '1',
      name: options.name ?? 'Admin User',
      email: options.email ?? 'admin@thunderoll.com',
      role,
      // A token the mock backend accepts. It never reaches the browser: it
      // lives inside the encrypted cookie.
      accessToken: `mock-access-token-${role}`,
      refreshToken: 'mock-refresh-token',
      accessTokenExpiresAt: Date.now() + 60 * 60 * 1000,
      roleCheckedAt: Date.now(),
    },
    secret,
    maxAge: 60 * 60,
  });
}
