import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiFetch, ApiError, API_URL } from '@/lib/api';
import {
  previewImport,
  uploadImport,
  listImports,
  getImport,
  getImportErrors,
  deleteImport,
  listModelEquivalences,
  listUnmappedModels,
  createModelEquivalence,
  updateModelEquivalence,
  deleteModelEquivalence,
} from '@/lib/imports';

const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

function mockResponse(
  body: unknown,
  init: { ok?: boolean; status?: number; statusText?: string } = {},
) {
  const { ok = true, status = 200, statusText = 'OK' } = init;
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  return Promise.resolve({
    ok,
    status,
    statusText,
    text: () => Promise.resolve(text),
  });
}

function lastCall() {
  const call = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
  return { url: call[0] as string, init: (call[1] || {}) as RequestInit };
}

function headerValue(init: RequestInit, name: string): string | null {
  return new Headers(init.headers).get(name);
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe('apiFetch', () => {
  it('attaches the bearer token when provided', async () => {
    mockFetch.mockReturnValue(mockResponse({ ok: true }));
    await apiFetch('/ping', { token: 'abc123' });
    const { url, init } = lastCall();
    expect(url).toBe(`${API_URL}/ping`);
    expect(headerValue(init, 'Authorization')).toBe('Bearer abc123');
  });

  it('omits the Authorization header when no token', async () => {
    mockFetch.mockReturnValue(mockResponse({ ok: true }));
    await apiFetch('/ping');
    const { init } = lastCall();
    expect(headerValue(init, 'Authorization')).toBeNull();
  });

  it('serializes a JSON body and sets content-type', async () => {
    mockFetch.mockReturnValue(mockResponse({ id: 1 }));
    await apiFetch('/things', { method: 'POST', json: { a: 1 } });
    const { init } = lastCall();
    expect(headerValue(init, 'Content-Type')).toBe('application/json');
    expect(init.body).toBe(JSON.stringify({ a: 1 }));
  });

  it('returns the parsed JSON payload', async () => {
    mockFetch.mockReturnValue(mockResponse({ value: 42 }));
    const data = await apiFetch<{ value: number }>('/x');
    expect(data.value).toBe(42);
  });

  it('returns undefined for an empty body', async () => {
    mockFetch.mockReturnValue(mockResponse(''));
    const data = await apiFetch('/x', { method: 'DELETE' });
    expect(data).toBeUndefined();
  });

  it('throws ApiError with the string detail message on failure', async () => {
    mockFetch.mockReturnValue(
      mockResponse({ detail: 'Invalid file type' }, { ok: false, status: 400 }),
    );
    await expect(apiFetch('/upload')).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      message: 'Invalid file type',
    });
  });

  it('extracts the message from FastAPI validation errors (array detail)', async () => {
    mockFetch.mockReturnValue(
      mockResponse(
        { detail: [{ msg: 'field required', loc: ['body', 'x'] }] },
        { ok: false, status: 422 },
      ),
    );
    await expect(apiFetch('/x')).rejects.toMatchObject({
      status: 422,
      message: 'field required',
    });
  });

  it('falls back to statusText when no detail is present', async () => {
    mockFetch.mockReturnValue(
      mockResponse('', { ok: false, status: 500, statusText: 'Server Error' }),
    );
    await expect(apiFetch('/x')).rejects.toBeInstanceOf(ApiError);
  });
});

describe('imports client', () => {
  it('previewImport posts FormData with file and column_mapping', async () => {
    mockFetch.mockReturnValue(mockResponse({ filename: 'f.xlsx' }));
    const file = new File(['x'], 'f.xlsx');
    await previewImport(file, { NO: 'model', Color: 'color' }, 'tok');
    const { url, init } = lastCall();
    expect(url).toBe(`${API_URL}/api/v1/imports/preview`);
    expect(init.method).toBe('POST');
    expect(headerValue(init, 'Authorization')).toBe('Bearer tok');
    const body = init.body as FormData;
    expect(body.get('file')).toBeInstanceOf(File);
    expect(body.get('column_mapping')).toBe(
      JSON.stringify({ NO: 'model', Color: 'color' }),
    );
  });

  it('previewImport omits column_mapping when empty', async () => {
    mockFetch.mockReturnValue(mockResponse({ filename: 'f.xlsx' }));
    await previewImport(new File(['x'], 'f.xlsx'), null, 'tok');
    const body = lastCall().init.body as FormData;
    expect(body.has('column_mapping')).toBe(false);
  });

  it('uploadImport sends metadata and column_mapping', async () => {
    mockFetch.mockReturnValue(mockResponse({ import_id: 1 }));
    await uploadImport(
      new File(['x'], 'f.csv'),
      { batch_period: '2026-ABRIL', product_type: 'scooter', columnMapping: { A: 'frame' } },
      'tok',
    );
    const { url, init } = lastCall();
    expect(url).toBe(`${API_URL}/api/v1/imports/upload`);
    const body = init.body as FormData;
    expect(body.get('batch_period')).toBe('2026-ABRIL');
    expect(body.get('product_type')).toBe('scooter');
    expect(body.get('column_mapping')).toBe(JSON.stringify({ A: 'frame' }));
  });

  it('uploadImport omits empty metadata fields', async () => {
    mockFetch.mockReturnValue(mockResponse({ import_id: 1 }));
    await uploadImport(new File(['x'], 'f.csv'), {}, 'tok');
    const body = lastCall().init.body as FormData;
    expect(body.has('batch_period')).toBe(false);
    expect(body.has('product_type')).toBe(false);
    expect(body.has('column_mapping')).toBe(false);
  });

  it('listImports builds the pagination query', async () => {
    mockFetch.mockReturnValue(mockResponse([]));
    await listImports('tok', { skip: 10, limit: 25 });
    expect(lastCall().url).toBe(`${API_URL}/api/v1/imports/?skip=10&limit=25`);
  });

  it('getImport targets the record path', async () => {
    mockFetch.mockReturnValue(mockResponse({ id: 7 }));
    await getImport(7, 'tok');
    expect(lastCall().url).toBe(`${API_URL}/api/v1/imports/7`);
  });

  it('getImportErrors targets the errors path', async () => {
    mockFetch.mockReturnValue(mockResponse([]));
    await getImportErrors(7, 'tok');
    expect(lastCall().url).toBe(`${API_URL}/api/v1/imports/7/errors`);
  });

  it('deleteImport uses the DELETE method', async () => {
    mockFetch.mockReturnValue(mockResponse(''));
    await deleteImport(7, 'tok');
    const { url, init } = lastCall();
    expect(url).toBe(`${API_URL}/api/v1/imports/7`);
    expect(init.method).toBe('DELETE');
  });
});

describe('model-equivalences client', () => {
  it('listModelEquivalences targets the base path', async () => {
    mockFetch.mockReturnValue(mockResponse([]));
    await listModelEquivalences('tok');
    expect(lastCall().url).toBe(`${API_URL}/api/v1/model-equivalences/`);
  });

  it('listUnmappedModels targets the unmapped path', async () => {
    mockFetch.mockReturnValue(mockResponse([]));
    await listUnmappedModels('tok');
    expect(lastCall().url).toBe(`${API_URL}/api/v1/model-equivalences/unmapped`);
  });

  it('createModelEquivalence posts a JSON payload', async () => {
    mockFetch.mockReturnValue(mockResponse({ id: 1 }));
    await createModelEquivalence(
      { manufacturer_model: 'X3', internal_model: '571' },
      'tok',
    );
    const { url, init } = lastCall();
    expect(url).toBe(`${API_URL}/api/v1/model-equivalences/`);
    expect(init.method).toBe('POST');
    expect(headerValue(init, 'Content-Type')).toBe('application/json');
    expect(init.body).toBe(
      JSON.stringify({ manufacturer_model: 'X3', internal_model: '571' }),
    );
  });

  it('updateModelEquivalence uses PUT', async () => {
    mockFetch.mockReturnValue(mockResponse({ id: 1 }));
    await updateModelEquivalence(1, { internal_model: 'TR 571 PLUS' }, 'tok');
    const { url, init } = lastCall();
    expect(url).toBe(`${API_URL}/api/v1/model-equivalences/1`);
    expect(init.method).toBe('PUT');
  });

  it('deleteModelEquivalence uses DELETE', async () => {
    mockFetch.mockReturnValue(mockResponse(''));
    await deleteModelEquivalence(1, 'tok');
    expect(lastCall().init.method).toBe('DELETE');
  });
});
