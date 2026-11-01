import { handleSessionExpired } from '@/lib/session-expiry';

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

/**
 * fetch wrapper for every authenticated request. A 401 means the backend
 * token is dead: start the sign-out flow and never resolve, so callers do not
 * render the error while the page navigates to /login. 403 and other statuses
 * pass through untouched.
 */
export async function sessionAwareFetch(
  input: string,
  init?: RequestInit,
  { skipSessionExpiry = false }: { skipSessionExpiry?: boolean } = {},
): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401 && !skipSessionExpiry) {
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
