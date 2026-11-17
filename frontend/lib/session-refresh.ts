import { getSession } from 'next-auth/react';

/**
 * Renews the session on the server.
 *
 * The backend tokens live inside the encrypted session cookie, so the
 * browser cannot renew them by itself: it asks NextAuth to re-read the
 * session, and the `jwt` callback (server side) swaps the access token for a
 * fresh one when it is about to expire. The renewed cookie comes back with
 * the response, so the next call to the proxy already carries the new token.
 *
 * It is single-flight: several requests that fail at once share a single
 * renewal, instead of one per request.
 */
let inFlight: Promise<unknown> | null = null;

export function renewSession(): Promise<unknown> {
  if (typeof window === 'undefined') return Promise.resolve(null);
  if (!inFlight) {
    const current = (async () => {
      try {
        return await getSession();
      } catch {
        // No session (or a broken one): there is nothing to renew.
        return null;
      }
    })();
    inFlight = current;
    void current.finally(() => {
      // Only cleared if this is still the current renewal: if another one
      // started meanwhile, that one wins.
      if (inFlight === current) inFlight = null;
    });
  }
  return inFlight;
}
