'use client';

import { useSession } from 'next-auth/react';

import { getPermissions, normalizeRole } from '@/lib/permissions';
import type { Permissions, Role } from '@/lib/permissions';

/**
 * The permission rules live in `lib/permissions.ts` so the edge middleware
 * can use the very same ones. They are re-exported here because this module
 * is the one the UI imports.
 */
export { getPermissions, normalizeRole } from '@/lib/permissions';
export type { Permissions, Role } from '@/lib/permissions';

export interface AuthInfo extends Permissions {
  role: string;
  isAdmin: boolean;
  isManager: boolean;
  isOperator: boolean;
}

/**
 * Read the session once and expose the role flags + permissions.
 *
 * The backend access token is NOT part of this: it lives inside the
 * encrypted session cookie and is only ever read on the server (the proxy
 * route handler). The browser never sees it, so there is nothing to leak
 * through an XSS.
 */
export function useAuth(): AuthInfo {
  const { data: session } = useSession();
  const role = normalizeRole((session?.user as { role?: string } | undefined)?.role);
  return {
    role,
    isAdmin: role === 'admin',
    isManager: role === 'manager',
    isOperator: role === 'operator',
    ...getPermissions(role),
  };
}
