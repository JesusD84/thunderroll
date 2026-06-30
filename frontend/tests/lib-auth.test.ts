import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { getPermissions, normalizeRole, useAuth } from '@/lib/auth';

let mockSession: any = null;
vi.mock('next-auth/react', () => ({
  useSession: () => ({ data: mockSession, status: 'authenticated' }),
}));

beforeEach(() => {
  mockSession = null;
});

describe('normalizeRole', () => {
  it('lowercases string roles', () => {
    expect(normalizeRole('ADMIN')).toBe('admin');
    expect(normalizeRole('Manager')).toBe('manager');
  });
  it('returns empty string for non-strings', () => {
    expect(normalizeRole(undefined)).toBe('');
    expect(normalizeRole(null)).toBe('');
    expect(normalizeRole(42)).toBe('');
  });
});

describe('getPermissions', () => {
  it('grants everything relevant to ADMIN', () => {
    expect(getPermissions('admin')).toEqual({
      manageEquivalences: true,
      deleteEquivalence: true,
      deleteImport: true,
      uploadImport: true,
    });
  });

  it('lets MANAGER manage but not delete', () => {
    expect(getPermissions('manager')).toEqual({
      manageEquivalences: true,
      deleteEquivalence: false,
      deleteImport: false,
      uploadImport: true,
    });
  });

  it('lets OPERATOR only upload', () => {
    expect(getPermissions('operator')).toEqual({
      manageEquivalences: false,
      deleteEquivalence: false,
      deleteImport: false,
      uploadImport: true,
    });
  });

  it('grants nothing to VIEWER or unknown roles', () => {
    const none = {
      manageEquivalences: false,
      deleteEquivalence: false,
      deleteImport: false,
      uploadImport: false,
    };
    expect(getPermissions('viewer')).toEqual(none);
    expect(getPermissions('')).toEqual(none);
    expect(getPermissions(undefined)).toEqual(none);
  });
});

describe('useAuth', () => {
  it('exposes token and role flags for an admin session', () => {
    mockSession = { accessToken: 'tok', user: { role: 'ADMIN' } };
    const { result } = renderHook(() => useAuth());
    expect(result.current.token).toBe('tok');
    expect(result.current.role).toBe('admin');
    expect(result.current.isAdmin).toBe(true);
    expect(result.current.deleteImport).toBe(true);
    expect(result.current.manageEquivalences).toBe(true);
  });

  it('defaults to no permissions when there is no session', () => {
    mockSession = null;
    const { result } = renderHook(() => useAuth());
    expect(result.current.token).toBeUndefined();
    expect(result.current.role).toBe('');
    expect(result.current.isAdmin).toBe(false);
    expect(result.current.deleteImport).toBe(false);
    expect(result.current.manageEquivalences).toBe(false);
  });
});
