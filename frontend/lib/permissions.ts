/**
 * Role rules, shared by the UI and by the edge middleware.
 *
 * This module is isomorphic on purpose: `lib/auth.ts` (client) and
 * `middleware.ts` (edge runtime) both import it, so the sections the
 * middleware locks and the buttons the UI hides can never drift apart.
 *
 * The backend stays the source of truth: `require_role` decides what the API
 * accepts. These flags only decide what the browser is offered.
 */

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
  deleteUnit: boolean;
  deleteTransfer: boolean;
  deleteLocation: boolean;
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
    // The destructive endpoints are admin-only on the API
    // (DELETE /units/{id}, DELETE /transfers/{id}, DELETE /locations/{id}),
    // so the UI must not offer them to anyone else.
    deleteUnit: isAdmin,
    deleteTransfer: isAdmin,
    deleteLocation: isAdmin,
    manageUsers: isAdmin || isManager,
  };
}

/**
 * Sections that are not for every signed-in user.
 *
 * The middleware uses these to keep a role out of a page it cannot use; the
 * page itself keeps its own checks as UX (so the redirect still happens
 * without a full page load). The permission named here is the same flag the
 * navigation uses to decide whether to show the link at all.
 */
export interface RouteRule {
  /** Path prefix the rule applies to. */
  prefix: string;
  /** Permission the role needs to enter the section. */
  permission: keyof Permissions;
}

export const ROLE_GATED_ROUTES: readonly RouteRule[] = [
  { prefix: '/imports', permission: 'viewImports' },
  { prefix: '/model-equivalences', permission: 'viewEquivalences' },
  { prefix: '/reports', permission: 'viewReports' },
  { prefix: '/units/new', permission: 'manageUnits' },
];

/**
 * The permission a path needs, or null when every signed-in user may open it.
 * The match is on whole path segments, so `/units/new` does not swallow
 * `/units` and `/reports` does not swallow `/reports-export`.
 */
export function requiredPermissionForPath(pathname: string): keyof Permissions | null {
  const normalized = pathname.replace(/\/+$/, '') || '/';
  for (const rule of ROLE_GATED_ROUTES) {
    if (normalized === rule.prefix || normalized.startsWith(`${rule.prefix}/`)) {
      return rule.permission;
    }
  }
  return null;
}

/**
 * May this role open this path?
 *
 * Unknown paths and paths without a rule are open to any signed-in user:
 * the API is still the one that decides, and a 403 is a better answer than
 * a redirect to a page that does not exist.
 */
export function canAccessPath(role: unknown, pathname: string): boolean {
  const permission = requiredPermissionForPath(pathname);
  if (!permission) return true;
  return getPermissions(role)[permission];
}
