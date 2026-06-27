import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Navigation from '@/components/Navigation';

const mockPush = vi.fn();
const mockSignOut = vi.fn();
let mockPathname = '/';
let mockStatus = 'authenticated';

vi.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: { user: { name: 'Admin User' } },
    status: mockStatus,
  }),
  signOut: (...args: any[]) => mockSignOut(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockPathname = '/';
  mockStatus = 'authenticated';
});

describe('Navigation', () => {
  it('renders brand name', () => {
    render(<Navigation />);
    expect(screen.getByText('Thunderrol')).toBeInTheDocument();
  });

  it('renders all nav links', () => {
    render(<Navigation />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Unidades')).toBeInTheDocument();
    expect(screen.getByText('Importar')).toBeInTheDocument();
    expect(screen.getByText('Equivalencias')).toBeInTheDocument();
    expect(screen.getByText('Transferencias')).toBeInTheDocument();
    expect(screen.getByText('Reportes')).toBeInTheDocument();
    expect(screen.getByText('Configuración')).toBeInTheDocument();
  });

  it('shows user name', () => {
    render(<Navigation />);
    expect(screen.getByText('Admin User')).toBeInTheDocument();
  });

  it('calls signOut and redirects on logout', async () => {
    render(<Navigation />);
    const logoutButtons = screen.getAllByText('Salir');
    await userEvent.click(logoutButtons[0]);
    expect(mockSignOut).toHaveBeenCalledWith({ redirect: false });
    expect(mockPush).toHaveBeenCalledWith('/login');
  });

  it('returns null on login page', () => {
    mockPathname = '/login';
    const { container } = render(<Navigation />);
    expect(container.innerHTML).toBe('');
  });

  it('returns null when loading', () => {
    mockStatus = 'loading';
    const { container } = render(<Navigation />);
    expect(container.innerHTML).toBe('');
  });

  it('returns null when unauthenticated', () => {
    mockStatus = 'unauthenticated';
    const { container } = render(<Navigation />);
    expect(container.innerHTML).toBe('');
  });
});