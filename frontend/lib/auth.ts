'use client';

import { useSession } from 'next-auth/react';

export type Role = 'admin' | 'manager' | 'operator';

/** Lowercase a possibly-missing role value, returning '' when absent. */
export function normalizeRole(value: unknown): string {
  return typeof value === 'string' ? value.toLowerCase() : '';
}

/**
 * Centralized, permission-based gating for the whole app.
 * Mirrors the backend `require_role` rules so the UI hides actions the
 * API would reject. Operator ("Operativo") is intentionally the most
 * restricted role: it can only dispatch/receive transfers (check units
 * in/out) and view available units across locations — no imports, no
 * equivalences, no reports, no unit CRUD, no user management.
 */
export interface Permissions {
  manageEquivalences: boolean;
  deleteEquivalence: boolean;
  viewEquivalences: boolean;
  deleteImport: boolean;
  uploadImport: boolean;
  viewImports: boolean;
  viewReports: boolean;
  manageUnits: boolean;
  manageUsers: boolean;
}

export function getPermissions(role: unknown): Permissions {
  const r = normalizeRole(role);
  const isAdmin = r === 'admin';
  const isManager = r === 'manager';
  return {
    manageEquivalences: isAdmin || isManager,
    deleteEquivalence: isAdmin,
    viewEquivalences: isAdmin || isManager,
    deleteImport: isAdmin,
    uploadImport: isAdmin || isManager,
    viewImports: isAdmin || isManager,
    viewReports: isAdmin || isManager,
    manageUnits: isAdmin || isManager,
    manageUsers: isAdmin || isManager,
  };
}

export interface AuthInfo extends Permissions {
  token: string | undefined;
  role: string;
  isAdmin: boolean;
  isManager: boolean;
  isOperator: boolean;
}

/** Read the session once and expose token + role flags + permissions. */
export function useAuth(): AuthInfo {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const role = normalizeRole((session?.user as { role?: string } | undefined)?.role);
  return {
    token,
    role,
    isAdmin: role === 'admin',
    isManager: role === 'manager',
    isOperator: role === 'operator',
    ...getPermissions(role),
  };
}
