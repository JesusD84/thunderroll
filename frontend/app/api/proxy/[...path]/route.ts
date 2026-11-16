/**
 * API proxy: the only way the browser reaches the backend.
 *
 * The browser sends its requests here without any credential: the proxy
 * reads the backend access token from the encrypted session cookie (server
 * side only) and forwards the call with the `Authorization: Bearer` header.
 * The token never reaches the page, so an XSS cannot steal it.
 *
 * Path shape: `/api/proxy/api/v1/units/` -> `<BACKEND_URL>/api/v1/units/`.
 *
 * The backend answers a path that misses its trailing slash with a
 * redirect, and that redirect is followed here, on the server: the browser
 * must never see a redirect that points outside this origin.
 */

import { NextRequest, NextResponse } from 'next/server';

import { getSessionToken } from '@/lib/server/session';

export const dynamic = 'force-dynamic';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';
const PROXY_PREFIX = '/api/proxy';

/**
 * Endpoints the browser must not reach through the proxy: the auth ones
 * manage their own credentials (login, refresh, password reset).
 */
const BLOCKED_ROOTS = new Set(['auth']);

/** A path segment may only hold characters a real API segment needs. */
const SAFE_SEGMENT = /^[A-Za-z0-9._-]+$/;

function isSafeSegment(segment: string): boolean {
  return SAFE_SEGMENT.test(segment) && segment !== '.' && segment !== '..';
}

/** The origin of the backend: a redirect is only followed inside it. */
function backendOrigin(): string {
  try {
    return new URL(BACKEND_URL).origin;
  } catch {
    // A malformed BACKEND_URL must not break the import of this module.
    return '';
  }
}

/** Headers of the backend response the browser is allowed to see. */
const FORWARDED_RESPONSE_HEADERS = [
  'content-type',
  'content-disposition',
  'x-total-count',
];

/**
 * The path of the backend the request is for.
 *
 * The client sends the backend path as it is (`/api/proxy/api/v1/units/`), so
 * the prefix comes off here and goes back on when the URL is built. The
 * trailing slash is part of the path (the backend routes have it), so the
 * path is read as a string and not as a list of segments.
 */
function backendPath(pathname: string): string | null {
  if (!pathname.startsWith(PROXY_PREFIX)) return null;

  let path = pathname.slice(PROXY_PREFIX.length);
  if (!path.startsWith('/')) return null;

  if (path === API_PREFIX || path.startsWith(`${API_PREFIX}/`)) {
    path = path.slice(API_PREFIX.length);
  }

  return path || null;
}

async function handler(
  req: NextRequest,
  { params }: { params: { path?: string[] } },
): Promise<NextResponse> {
  const path = backendPath(req.nextUrl.pathname);
  // The segments of the backend path (the `/api/v1` prefix is already off).
  const segments = path ? path.split('/').filter((segment) => segment !== '') : [];
  const routeSegments = (params.path ?? []).filter((segment) => segment !== '');

  // A path that does not look like an API path is a probing attempt, not a
  // route: it is rejected before it can reach the backend.
  if (
    !path ||
    routeSegments.length === 0 ||
    !routeSegments.every(isSafeSegment) ||
    !segments.every(isSafeSegment)
  ) {
    return NextResponse.json({ detail: 'Ruta no válida' }, { status: 400 });
  }

  if (BLOCKED_ROOTS.has(segments[0].toLowerCase())) {
    return NextResponse.json({ detail: 'Ruta no permitida' }, { status: 403 });
  }

  const session = await getSessionToken(req);
  const accessToken = session?.accessToken;
  if (!accessToken) {
    // No session (or a session whose backend token is gone): the client
    // turns this into the "session expired" flow.
    return NextResponse.json({ detail: 'No autenticado' }, { status: 401 });
  }

  const target = new URL(`${API_PREFIX}${path}`, BACKEND_URL);
  target.search = req.nextUrl.search;

  // Only the headers the backend needs are forwarded: never the cookies of
  // the browser and never a client-provided Authorization header.
  const headers = new Headers();
  headers.set('Authorization', `Bearer ${accessToken}`);
  const contentType = req.headers.get('content-type');
  if (contentType) headers.set('Content-Type', contentType);

  const hasBody = req.method !== 'GET' && req.method !== 'HEAD';
  const body = hasBody ? await req.arrayBuffer() : undefined;

  const callBackend = (url: URL) =>
    fetch(url, {
      method: req.method,
      headers,
      body,
      cache: 'no-store',
      // The redirects are handled here, not by the browser: a redirect to
      // the backend's origin would send the browser outside the app.
      redirect: 'manual' as const,
    });

  let upstream: Response;
  try {
    upstream = await callBackend(target);

    // The backend answers a path that misses its trailing slash with a
    // redirect (`/api/v1/units` -> `/api/v1/units/`). It is followed HERE,
    // on the server, and only towards the backend: the browser must never
    // see a redirect that points outside this origin.
    if (upstream.status === 307 || upstream.status === 308) {
      const location = upstream.headers.get('location');
      if (location) {
        const redirected = new URL(location, BACKEND_URL);
        if (redirected.origin === backendOrigin()) {
          upstream = await callBackend(redirected);
        }
      }
    }
  } catch {
    return NextResponse.json(
      { detail: 'No se pudo conectar con el servidor' },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE };
