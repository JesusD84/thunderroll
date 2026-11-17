import { handleSessionExpired } from '@/lib/session-expiry';
import { renewSession } from '@/lib/session-refresh';

/**
 * Base of every call the browser makes to the backend.
 *
 * It points at the server-side proxy (`app/api/proxy`), not at the backend:
 * the browser never talks to the API directly and never carries a token.
 */
export const API_BASE = '/api/proxy';

export class ApiError extends Error {
  readonly status: number;
  /**
   * The `detail` the backend sent: a string with the reason, or the list of
   * validation errors (FastAPI answers 422 with an array when the request
   * does not validate).
   */
  readonly detail: unknown;
  /** The whole parsed body, for the cases that need more than the detail. */
  readonly body: unknown;

  constructor(message: string, status: number, detail?: unknown, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.body = body;
  }
}

export interface ApiFetchOptions extends Omit<RequestInit, 'body' | 'headers'> {
  headers?: HeadersInit;
  body?: BodyInit | null;
  json?: unknown;
  /** Set where a 401 is an expected answer (e.g. login). */
  skipSessionExpiry?: boolean;
}

/**
 * fetch wrapper for every authenticated request.
 *
 * The credentials are not in the request: they are in the session cookie,
 * and the proxy route handler turns them into the `Authorization` header on
 * the server. A 401 means the session is not usable any more. Before giving
 * up on it, the session is renewed (the server swaps the access token for a
 * fresh one and writes the new cookie) and the request is retried once, so
 * an expiring token does not throw the user out. When the renewal does not
 * work either, the sign-out flow starts and the promise never resolves, so
 * callers do not render the error while the page navigates to /login.
 * 403 and other statuses pass through untouched.
 */
export async function sessionAwareFetch(
  input: string,
  init?: RequestInit,
  { skipSessionExpiry = false }: { skipSessionExpiry?: boolean } = {},
): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401 && !skipSessionExpiry) {
    await renewSession();
    // The body is a string, a FormData or an ArrayBuffer: it can be sent
    // again, so the retry is safe.
    const retried = await fetch(input, init);
    // A second 401 means the session is gone for good.
    if (retried.status !== 401) return retried;

    void handleSessionExpired();
    // Trade-off: callers' `finally` blocks do not run; the page is leaving anyway.
    return new Promise<Response>(() => {});
  }
  return response;
}

/**
 * The `detail` of an error: a string with the reason, the list of validation
 * errors, or the body itself when the backend did not send a `detail`.
 */
function extractDetail(data: unknown): unknown {
  if (data && typeof data === 'object' && 'detail' in data) {
    return (data as { detail: unknown }).detail;
  }
  return data;
}

function extractMessage(status: number, statusText: string, detail: unknown): string {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (first && typeof first === 'object' && 'msg' in first) {
      return String((first as { msg: unknown }).msg);
    }
  }
  return statusText || `Request failed with status ${status}`;
}

/**
 * Call the backend through the proxy and return the parsed body.
 *
 * `path` is the path of the backend endpoint, e.g. `/api/v1/units/`. Errors
 * come back as an `ApiError` carrying the status and the parsed detail.
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { json, headers, body, skipSessionExpiry, ...rest } = options;

  const finalHeaders = new Headers(headers);
  let finalBody = body;
  if (json !== undefined) {
    finalHeaders.set('Content-Type', 'application/json');
    finalBody = JSON.stringify(json);
  }

  const response = await sessionAwareFetch(
    `${API_BASE}${path}`,
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
    const detail = extractDetail(data);
    throw new ApiError(
      extractMessage(response.status, response.statusText, detail),
      response.status,
      detail,
      data,
    );
  }

  return data as T;
}
