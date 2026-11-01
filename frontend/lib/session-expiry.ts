import { signOut } from 'next-auth/react';

export const SESSION_EXPIRED_MESSAGE = 'La sesión ha expirado';
export const SESSION_EXPIRED_REASON = 'expired';

/** Only same-app relative paths; blocks open redirects such as //evil.com. */
export function safeCallbackUrl(raw: string | null): string {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/login')) {
    return '/';
  }
  return raw;
}

let expiring: Promise<void> | null = null;

/**
 * Single entry point for "the backend rejected our credentials".
 * Idempotent: concurrent 401s share one sign-out and one navigation.
 */
export function handleSessionExpired(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve();
  if (!expiring) {
    expiring = (async () => {
      const { pathname, search } = window.location;
      try {
        // Await: /login must not see "authenticated" and bounce back to "/".
        await signOut({ redirect: false });
      } catch {
        // Navigate anyway: the local session is unusable either way.
      } finally {
        const params = new URLSearchParams({ reason: SESSION_EXPIRED_REASON });
        if (pathname !== '/login') params.set('callbackUrl', pathname + search);
        // Hard navigation drops all in-memory state.
        window.location.assign(`/login?${params.toString()}`);
      }
    })();
  }
  return expiring;
}
