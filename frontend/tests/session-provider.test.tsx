import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import SessionProvider from '@/components/providers/SessionProvider';

vi.mock('next-auth/react', () => ({
  SessionProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('SessionProvider', () => {
  it('renders children', () => {
    render(
      <SessionProvider>
        <div>Hello World</div>
      </SessionProvider>
    );
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });
});