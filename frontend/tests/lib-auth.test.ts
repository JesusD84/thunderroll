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
  it('grants everything to ADMIN', () => {
    expect(getPermissions('admin')).toEqual({
      manageEquivalences: true,
      deleteEquivalence: true,
      viewEquivalences: true,
      deleteImport: true,
      uploadImport: true,
      viewImports: true,
      viewReports: true,
      manageUnits: true,
      deleteUnit: true,
      deleteTransfer: true,
      deleteLocation: true,
      manageUsers: true,
    });
  });

  it('lets MANAGER manage but not delete', () => {
    expect(getPermissions('manager')).toEqual({
      manageEquivalences: true,
      deleteEquivalence: false,
      viewEquivalences: true,
      deleteImport: false,
      uploadImport: true,
      viewImports: true,
      viewReports: true,
      manageUnits: true,
      deleteUnit: false,
      deleteTransfer: false,
      deleteLocation: false,
      manageUsers: true,
    });
  });

  it('restricts OPERATOR to units/transfers only', () => {
    const operatorPermissions = {
      manageEquivalences: false,
      deleteEquivalence: false,
      viewEquivalences: false,
      deleteImport: false,
      uploadImport: false,
      viewImports: false,
      viewReports: false,
      manageUnits: false,
      deleteUnit: false,
      deleteTransfer: false,
      deleteLocation: false,
      manageUsers: false,
    };
    expect(getPermissions('operator')).toEqual(operatorPermissions);
  });

  it('grants nothing to unknown roles', () => {
    const none = {
      manageEquivalences: false,
      deleteEquivalence: false,
      viewEquivalences: false,
      deleteImport: false,
      uploadImport: false,
      viewImports: false,
      viewReports: false,
      manageUnits: false,
      deleteUnit: false,
      deleteTransfer: false,
      deleteLocation: false,
      manageUsers: false,
    };
    expect(getPermissions('')).toEqual(none);
    expect(getPermissions(undefined)).toEqual(none);
  });
});

describe('useAuth', () => {
  it('exposes the role flags and permissions for an admin session', () => {
    mockSession = { user: { role: 'ADMIN' } };
    const { result } = renderHook(() => useAuth());
    expect(result.current.role).toBe('admin');
    expect(result.current.isAdmin).toBe(true);
    expect(result.current.deleteImport).toBe(true);
    expect(result.current.manageEquivalences).toBe(true);
  });

  it('does not expose any token: the credential never reaches the browser', () => {
    mockSession = { accessToken: 'tok', user: { role: 'admin' } };
    const { result } = renderHook(() => useAuth());
    expect('token' in result.current).toBe(false);
    expect('accessToken' in result.current).toBe(false);
  });

  it('defaults to no permissions when there is no session', () => {
    mockSession = null;
    const { result } = renderHook(() => useAuth());
    expect(result.current.role).toBe('');
    expect(result.current.isAdmin).toBe(false);
    expect(result.current.deleteImport).toBe(false);
    expect(result.current.manageEquivalences).toBe(false);
    expect('token' in result.current).toBe(false);
  });
});
