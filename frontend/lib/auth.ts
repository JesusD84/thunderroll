'use client';

import { useSession } from 'next-auth/react';

export type Role = 'admin' | 'manager' | 'operator' | 'viewer';

/** Lowercase a possibly-missing role value, returning '' when absent. */
export function normalizeRole(value: unknown): string {
  return typeof value === 'string' ? value.toLowerCase() : '';
}

/**
 * Centralized, permission-based gating for the imports module.
 * Mirrors the backend `require_role` rules so the UI hides actions the
 * API would reject:
 * - manage equivalences (create/update): ADMIN or MANAGER
 * - delete equivalence / delete import: ADMIN only
 * - upload/preview imports: any authenticated operator role
 */
export interface Permissions {
  manageEquivalences: boolean;
  deleteEquivalence: boolean;
  deleteImport: boolean;
  uploadImport: boolean;
}

export function getPermissions(role: unknown): Permissions {
  const r = normalizeRole(role);
  const isAdmin = r === 'admin';
  const isManager = r === 'manager';
  const isOperator = r === 'operator';
  return {
    manageEquivalences: isAdmin || isManager,
    deleteEquivalence: isAdmin,
    deleteImport: isAdmin,
    uploadImport: isAdmin || isManager || isOperator,
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
