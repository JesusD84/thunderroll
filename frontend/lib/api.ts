import { handleSessionExpired } from '@/lib/session-expiry';
import { refreshAccessToken } from '@/lib/session-refresh';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export interface ApiFetchOptions extends Omit<RequestInit, 'body' | 'headers'> {
  token?: string | null;
  headers?: HeadersInit;
  body?: BodyInit | null;
  json?: unknown;
  /** Set where a 401 is an expected answer (e.g. login). */
  skipSessionExpiry?: boolean;
}

/** Lee el token Bearer de las cabeceras de una petición, si lo hay. */
function bearerToken(headers: HeadersInit | undefined): string | null {
  if (!headers) return null;
  const value = new Headers(headers).get('Authorization');
  if (!value || !value.toLowerCase().startsWith('bearer ')) return null;
  return value.slice('bearer '.length).trim() || null;
}

/** Copia la petición cambiando el token de acceso por uno nuevo. */
function withBearerToken(init: RequestInit | undefined, token: string): RequestInit {
  const headers = new Headers(init?.headers);
  headers.set('Authorization', `Bearer ${token}`);
  return { ...init, headers };
}

/**
 * fetch wrapper for every authenticated request. A 401 means the backend
 * token is dead. Before giving up on the session, it tries to renew the
 * access token: if the refresh token is still valid the request is retried
 * once with the new token, so an expiring token does not throw the user out.
 * When the refresh does not work either, the sign-out flow starts and the
 * promise never resolves, so callers do not render the error while the page
 * navigates to /login. 403 and other statuses pass through untouched.
 */
export async function sessionAwareFetch(
  input: string,
  init?: RequestInit,
  { skipSessionExpiry = false }: { skipSessionExpiry?: boolean } = {},
): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401 && !skipSessionExpiry) {
    const usedToken = bearerToken(init?.headers);
    const freshToken = await refreshAccessToken();
    // Solo se reintenta si el token cambió de verdad: si el refresco no
    // pudo renovar nada, la sesión está muerta y hay que cerrarla.
    if (freshToken && freshToken !== usedToken) {
      const retried = await fetch(input, withBearerToken(init, freshToken));
      // Un segundo 401 significa que la sesión se acabó de verdad.
      if (retried.status !== 401) return retried;
    }
    void handleSessionExpired();
    // Trade-off: callers' `finally` blocks do not run; the page is leaving anyway.
    return new Promise<Response>(() => {});
  }
  return response;
}

function extractMessage(status: number, statusText: string, data: unknown): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (first && typeof first === 'object' && 'msg' in first) {
        return String((first as { msg: unknown }).msg);
      }
    }
  }
  if (typeof data === 'string' && data.trim()) return data;
  return statusText || `Request failed with status ${status}`;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { token, json, headers, body, skipSessionExpiry, ...rest } = options;

  const finalHeaders = new Headers(headers);
  if (token) {
    finalHeaders.set('Authorization', `Bearer ${token}`);
  }

  let finalBody = body;
  if (json !== undefined) {
    finalHeaders.set('Content-Type', 'application/json');
    finalBody = JSON.stringify(json);
  }

  const response = await sessionAwareFetch(
    `${API_URL}${path}`,
    { ...rest, headers: finalHeaders, body: finalBody },
    { skipSessionExpiry },
  );

  const raw = await response.text();
  let data: unknown = undefined;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = raw;
    }
  }

  if (!response.ok) {
    throw new ApiError(
      extractMessage(response.status, response.statusText, data),
      response.status,
      data,
    );
  }

  return data as T;
}
