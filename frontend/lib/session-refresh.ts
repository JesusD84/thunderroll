import { getSession } from 'next-auth/react';

/**
 * Renueva el token de acceso cuando el backend ya no lo acepta.
 *
 * `getSession()` consulta `/api/auth/session`, y ahí el callback `jwt` de
 * NextAuth pide al backend un token nuevo cuando el que tenía ya venció. La
 * respuesta trae el token renovado y la cookie de sesión queda actualizada,
 * así que los componentes que leen `useSession()` también se enteran.
 *
 * Es single-flight: varias peticiones que fallan a la vez comparten un solo
 * refresco, en lugar de lanzar uno por petición.
 */
let inFlight: Promise<string | null> | null = null;

export function refreshAccessToken(): Promise<string | null> {
  if (typeof window === 'undefined') return Promise.resolve(null);
  if (!inFlight) {
    const current = (async () => {
      try {
        const session = await getSession();
        const token = (session as { accessToken?: string } | null)?.accessToken;
        return token ?? null;
      } catch {
        // Sin sesión (o con la sesión rota) no hay token que renovar.
        return null;
      }
    })();
    inFlight = current;
    void current.finally(() => {
      // Solo se limpia si sigue siendo este refresco: si otro empezó
      // mientras tanto, ese manda.
      if (inFlight === current) inFlight = null;
    });
  }
  return inFlight;
}
