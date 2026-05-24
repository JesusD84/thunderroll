import { describe, it, expect, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginPage from '@/app/login/page';

const mockPush = vi.fn();
const mockSignIn = vi.fn();
let mockStatus = 'unauthenticated';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: mockStatus === 'authenticated' ? { user: { name: 'Test' } } : null,
    status: mockStatus,
  }),
  signIn: (...args: any[]) => mockSignIn(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockStatus = 'unauthenticated';
});

describe('LoginPage', () => {
  it('renders login form', () => {
    render(<LoginPage />);
    expect(screen.getByRole('heading', { name: 'Iniciar Sesión' })).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Iniciar Sesión/ })).toBeInTheDocument();
  });

  it('shows demo credentials', () => {
    render(<LoginPage />);
    expect(screen.getByText('Credenciales Demo:')).toBeInTheDocument();
    expect(screen.getByText(/admin@thunderrol.com/)).toBeInTheDocument();
  });

  it('calls signIn on submit', async () => {
    mockSignIn.mockResolvedValue({ ok: true, error: null });
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText('Email'), 'admin@test.com');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'pass123');
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Sesión/ }));
    expect(mockSignIn).toHaveBeenCalledWith('credentials', {
      email: 'admin@test.com',
      password: 'pass123',
      redirect: false,
    });
  });

  it('shows error on failed login', async () => {
    mockSignIn.mockResolvedValue({ ok: false, error: 'Invalid' });
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText('Email'), 'bad@test.com');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Sesión/ }));
    expect(await screen.findByText(/Credenciales inválidas/)).toBeInTheDocument();
  });

  it('redirects if already authenticated', async () => {
    mockStatus = 'authenticated';
    render(<LoginPage />);
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/');
    });
  });

  it('disables button while loading', async () => {
    mockSignIn.mockImplementation(() => new Promise(() => {}));
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'pass');
    await userEvent.click(screen.getByRole('button', { name: /Iniciar Sesión/ }));
    expect(screen.getByRole('button')).toBeDisabled();
  });
});