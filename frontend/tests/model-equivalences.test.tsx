import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ModelEquivalencesPage from '@/app/model-equivalences/page';
import type { ModelEquivalence } from '@/lib/imports';

// --- Mocks ---
let mockSession: any = { user: { name: 'Admin', role: 'admin' }, accessToken: 'fake-token' };

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({ data: mockSession, status: 'authenticated' }),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

function mockJson(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const { ok = true, status = 200 } = init;
  return Promise.resolve({
    ok,
    status,
    statusText: ok ? 'OK' : 'Error',
    text: () => Promise.resolve(JSON.stringify(body)),
  });
}

let eqs: ModelEquivalence[];
let unmappedModels: string[];
let failNextPost: { status: number; detail: string } | null;

function seed() {
  eqs = [
    {
      id: 1,
      manufacturer_model: 'X3',
      internal_model: 'Thunder X3',
      notes: 'serie premium',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: null,
    },
  ];
  unmappedModels = ['DIAOYU-Z'];
  failNextPost = null;
}

function installFetch() {
  mockFetch.mockImplementation((url: string, opts: any = {}) => {
    const method = opts.method ?? 'GET';
    if (url.includes('/model-equivalences/unmapped')) {
      return mockJson(unmappedModels);
    }
    const idMatch = url.match(/\/model-equivalences\/(\d+)$/);
    if (idMatch) {
      const id = Number(idMatch[1]);
      if (method === 'DELETE') {
        eqs = eqs.filter((e) => e.id !== id);
        return mockJson({ message: 'deleted' });
      }
      if (method === 'PUT') {
        const body = JSON.parse(opts.body);
        eqs = eqs.map((e) => (e.id === id ? { ...e, ...body } : e));
        return mockJson(eqs.find((e) => e.id === id));
      }
    }
    if (method === 'POST') {
      if (failNextPost) {
        return mockJson({ detail: failNextPost.detail }, { ok: false, status: failNextPost.status });
      }
      const body = JSON.parse(opts.body);
      const rec: ModelEquivalence = {
        id: 99,
        created_at: '2026-02-01T00:00:00Z',
        updated_at: null,
        ...body,
      };
      eqs = [...eqs, rec];
      return mockJson(rec, { status: 201 });
    }
    // GET list
    return mockJson(eqs);
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockSession = { user: { name: 'Admin', role: 'admin' }, accessToken: 'fake-token' };
  seed();
  installFetch();
});

const user = userEvent.setup({ pointerEventsCheck: 0 });

describe('ModelEquivalencesPage', () => {
  it('lists equivalences and unmapped models', async () => {
    render(<ModelEquivalencesPage />);

    await waitFor(() => {
      expect(screen.getByText('X3')).toBeInTheDocument();
    });
    expect(screen.getByText('Thunder X3')).toBeInTheDocument();
    expect(screen.getByText('DIAOYU-Z')).toBeInTheDocument();
    expect(screen.getByText('Modelos sin equivalencia (1)')).toBeInTheDocument();
  });

  it('creates a new equivalence', async () => {
    render(<ModelEquivalencesPage />);
    await waitFor(() => expect(screen.getByText('X3')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Nueva equivalencia/ }));
    await user.type(screen.getByLabelText('Modelo del fabricante'), 'XIAODOU');
    await user.type(screen.getByLabelText('Modelo interno'), 'Thunder Mini');
    await user.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => {
      const post = mockFetch.mock.calls.find((c) => c[1]?.method === 'POST');
      expect(post).toBeTruthy();
      expect(JSON.parse(post![1].body)).toMatchObject({
        manufacturer_model: 'XIAODOU',
        internal_model: 'Thunder Mini',
      });
    });
    await waitFor(() => expect(screen.getByText('XIAODOU')).toBeInTheDocument());
  });

  it('prefills the manufacturer model when creating from an unmapped model', async () => {
    render(<ModelEquivalencesPage />);
    await waitFor(() => expect(screen.getByText('DIAOYU-Z')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: 'Crear equivalencia para DIAOYU-Z' }));
    expect(screen.getByLabelText('Modelo del fabricante')).toHaveValue('DIAOYU-Z');
  });

  it('shows the backend error when creating a duplicate', async () => {
    failNextPost = { status: 409, detail: "An equivalence for 'X3' already exists" };
    render(<ModelEquivalencesPage />);
    await waitFor(() => expect(screen.getByText('X3')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Nueva equivalencia/ }));
    await user.type(screen.getByLabelText('Modelo del fabricante'), 'X3');
    await user.type(screen.getByLabelText('Modelo interno'), 'Thunder X3');
    await user.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => {
      expect(screen.getByText("An equivalence for 'X3' already exists")).toBeInTheDocument();
    });
  });

  it('edits an equivalence', async () => {
    render(<ModelEquivalencesPage />);
    await waitFor(() => expect(screen.getByText('X3')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: 'Editar X3' }));
    const internal = screen.getByLabelText('Modelo interno');
    await user.clear(internal);
    await user.type(internal, 'Thunder X3 Pro');
    await user.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => {
      const put = mockFetch.mock.calls.find((c) => c[1]?.method === 'PUT');
      expect(put).toBeTruthy();
      expect(put![0]).toContain('/model-equivalences/1');
      expect(JSON.parse(put![1].body)).toMatchObject({ internal_model: 'Thunder X3 Pro' });
    });
  });

  it('lets an ADMIN delete an equivalence', async () => {
    render(<ModelEquivalencesPage />);
    await waitFor(() => expect(screen.getByText('X3')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: 'Eliminar X3' }));
    await user.click(screen.getByRole('button', { name: 'Eliminar' }));

    await waitFor(() => {
      const del = mockFetch.mock.calls.find((c) => c[1]?.method === 'DELETE');
      expect(del).toBeTruthy();
      expect(del![0]).toContain('/model-equivalences/1');
    });
  });

  it('hides delete for MANAGER but allows editing', async () => {
    mockSession = { user: { name: 'Mgr', role: 'manager' }, accessToken: 'fake-token' };
    render(<ModelEquivalencesPage />);
    await waitFor(() => expect(screen.getByText('X3')).toBeInTheDocument());

    expect(screen.getByRole('button', { name: 'Editar X3' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Eliminar X3' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Nueva equivalencia/ })).toBeInTheDocument();
  });

  it('is read-only for OPERATOR', async () => {
    mockSession = { user: { name: 'Op', role: 'operator' }, accessToken: 'fake-token' };
    render(<ModelEquivalencesPage />);
    await waitFor(() => expect(screen.getByText('X3')).toBeInTheDocument());

    expect(screen.queryByRole('button', { name: /Nueva equivalencia/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Editar X3' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Eliminar X3' })).not.toBeInTheDocument();
  });
});
