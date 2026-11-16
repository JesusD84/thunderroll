/**
 * Mock of a `Response`, shared by every test that stubs `global.fetch`.
 *
 * The API client (`lib/api.ts`) reads the body with `response.text()` and
 * parses it, exactly like the browser does, so a stub that only implements
 * `json()` blows up with "response.text is not a function". This helper
 * builds an object with the same surface the browser offers: `ok`, `status`,
 * `statusText`, `headers.get()`, `json()`, `text()` and `blob()`.
 *
 * The credential does not travel in the request any more (it lives in the
 * session cookie and the server-side proxy adds the `Authorization` header),
 * so nothing here has to deal with tokens.
 */

export interface MockResponseInit {
  status?: number;              // default 200
  totalCount?: number;          // sets the X-Total-Count header
  headers?: Record<string, string>;
  contentType?: string;
}

export interface MockResponse {
  ok: boolean;
  status: number;
  statusText: string;
  headers: { get(name: string): string | null };
  json(): Promise<unknown>;
  text(): Promise<string>;
  blob(): Promise<Blob>;
}

const STATUS_TEXTS: Record<number, string> = {
  200: 'OK',
  201: 'Created',
  204: 'No Content',
  400: 'Bad Request',
  401: 'Unauthorized',
  403: 'Forbidden',
  404: 'Not Found',
  409: 'Conflict',
  413: 'Payload Too Large',
  422: 'Unprocessable Entity',
  500: 'Internal Server Error',
};

/** Parses the body as JSON, falling back to the raw string. */
function parseBody(raw: string): unknown {
  if (!raw) return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

export function mockResponse(data: unknown, init: MockResponseInit = {}): MockResponse {
  const status = init.status ?? 200;
  const contentType = init.contentType ?? 'application/json';
  const raw =
    data === undefined ? '' : typeof data === 'string' ? data : JSON.stringify(data);

  const headers = new Map<string, string>([['content-type', contentType]]);
  if (init.totalCount !== undefined) {
    headers.set('x-total-count', String(init.totalCount));
  }
  for (const [name, value] of Object.entries(init.headers ?? {})) {
    headers.set(name.toLowerCase(), value);
  }

  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: STATUS_TEXTS[status] ?? '',
    headers: {
      get(name: string) {
        return headers.get(name.toLowerCase()) ?? null;
      },
    },
    json: () => Promise.resolve(parseBody(raw)),
    text: () => Promise.resolve(raw),
    blob: () => Promise.resolve(new Blob([raw], { type: contentType })),
  };
}
