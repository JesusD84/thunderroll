/**
 * Cliente del backend para la sesión: renovación del token de acceso.
 *
 * Vive aparte del route handler de NextAuth para poder probarlo sin levantar
 * NextAuth entero.
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

/**
 * Margen para renovar antes de que el token expire. Con él, el token se
 * renueva en la lectura de sesión y el usuario no llega a ver un 401.
 */
export const REFRESH_MARGIN_MS = 60_000;

export interface BackendTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Pide al backend un token de acceso nuevo a partir del token de refresco.
 *
 * Devuelve null si el refresh token ya no vale (porque cambiaron las
 * credenciales, porque la cuenta se dio de baja o porque el token caducó):
 * en ese caso la sesión se cierra y el frontend vuelve al login.
 */
export async function refreshBackendToken(
  refreshToken: string,
): Promise<BackendTokenResponse | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${refreshToken}` },
    });
    if (!res.ok) return null;
    return (await res.json()) as BackendTokenResponse;
  } catch (error) {
    console.error('Error al refrescar el token:', error);
    return null;
  }
}

/**
 * ¿Hay que renovar el token de acceso?
 *
 * Se renueva cuando ya venció o cuando le queda poco. Un token sin fecha de
 * expiración (sesiones viejas, abiertas antes de este cambio) no se renueva:
 * no hay con qué pedir uno nuevo.
 */
export function shouldRefreshAccessToken(
  expiresAt: unknown,
  now: number = Date.now(),
): boolean {
  if (typeof expiresAt !== 'number' || Number.isNaN(expiresAt)) return false;
  return expiresAt - now <= REFRESH_MARGIN_MS;
}
