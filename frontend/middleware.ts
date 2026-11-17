/**
 * Route protection: no session, no page.
 *
 * `withAuth` reads the session cookie (server side) and sends anyone
 * without a session to the login page. On top of that, the sections that
 * are not for every role are closed with the same permission flags the UI
 * uses (`lib/permissions.ts`), so a role cannot reach a page it cannot use
 * even by typing the URL.
 *
 * The pages keep their own checks as UX, and the backend stays the source
 * of truth: it is the one that answers 403 for what a role cannot do.
 */

import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

import { canAccessPath, normalizeRole } from '@/lib/permissions';
import { sessionCookieName } from '@/lib/server/session';

export default withAuth(
  function middleware(req) {
    const role = normalizeRole(req.nextauth?.token?.role);

    if (!canAccessPath(role, req.nextUrl.pathname)) {
      // The role cannot open this section: send it to a page it can open
      // instead of showing a page that would only fail its API calls.
      return NextResponse.redirect(new URL('/units', req.url));
    }

    return NextResponse.next();
  },
  {
    pages: { signIn: '/login' },
    secret: process.env.NEXTAUTH_SECRET,
    // The same cookie NextAuth writes, so both always agree.
    cookies: { sessionToken: { name: sessionCookieName() } },
    callbacks: {
      authorized: ({ token }) => !!token,
    },
  },
);

export const config = {
  matcher: [
    /*
     * Everything except:
     * - /api/auth/*   : NextAuth's own endpoints (login, session, csrf...).
     * - /api/proxy/*  : the API proxy answers 401 by itself, so the browser
     *   gets a JSON error instead of an HTML redirect.
     * - /login       : the sign-in page.
     * - /_next/*     : Next.js internals.
     * - /favicon.ico : static asset.
     */
    '/((?!api/auth(?:/|$)|api/proxy(?:/|$)|login(?:/|$)|_next(?:/|$)|favicon\\.ico).*)',
  ],
};
