/**
 * Server-only helpers to read the NextAuth session cookie.
 *
 * The session cookie is the ONLY place the backend access token lives: it
 * is encrypted, httpOnly, and never handed to the browser. Server code
 * (the middleware and the API proxy) reads it from here; client code never
 * sees the token at all.
 */

import { getToken } from 'next-auth/jwt';
import type { JWT } from 'next-auth/jwt';
import type { NextRequest } from 'next/server';

/**
 * The cookie NextAuth uses for the session.
 *
 * NextAuth picks the secure variant when the app is served over https, so
 * the name is derived the same way here. Deriving it in one place keeps the
 * middleware, the proxy and NextAuth itself looking at the same cookie even
 * when `NEXTAUTH_URL` is the only hint available.
 */
export function sessionCookieName(): string {
  const secure = process.env.NEXTAUTH_URL?.startsWith('https://') ?? false;
  return secure ? '__Secure-next-auth.session-token' : 'next-auth.session-token';
}

/**
 * Read the session token (role + backend tokens) out of the request cookie.
 *
 * Returns null when there is no session, when the cookie is not valid, or
 * when `NEXTAUTH_SECRET` is missing: in all three cases the caller must
 * treat the request as unauthenticated.
 */
export async function getSessionToken(req: NextRequest): Promise<JWT | null> {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) return null;

  try {
    return await getToken({ req, secret, cookieName: sessionCookieName() });
  } catch {
    // A malformed cookie is the same as no cookie at all.
    return null;
  }
}
