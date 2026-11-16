
import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import type { JWT } from 'next-auth/jwt';

import {
  BackendTokenResponse,
  fetchBackendUser,
  refreshBackendToken,
  shouldRefreshAccessToken,
} from '@/lib/backend-auth';

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

/**
 * Cada cuánto se relee el rol del backend.
 *
 * El rol se guarda en la cookie de sesión (para que el middleware pueda
 * aplicarlo sin pedir nada al backend). Como un cambio de rol debe
 * reflejarse sin cerrar la sesión, la copia se refresca cada vez que la
 * sesión se renueva y, como máximo, una vez por minuto en el resto de
 * lecturas: así el cambio se ve en menos de un minuto sin pedir el usuario
 * al backend en cada navegación.
 */
const ROLE_REFRESH_INTERVAL_MS = 60_000;

/**
 * Relee el rol del backend y lo guarda en la cookie de sesión.
 *
 * Con `renewed` (la sesión acaba de renovarse) el rol se relee siempre; si
 * no, solo cuando la copia es más vieja que el intervalo.
 */
async function refreshRole(token: JWT, renewed: boolean): Promise<void> {
  if (!token.accessToken) return;

  const checkedAt = typeof token.roleCheckedAt === 'number' ? token.roleCheckedAt : 0;
  const stale = Date.now() - checkedAt > ROLE_REFRESH_INTERVAL_MS;
  if (!renewed && !stale) return;

  const user = await fetchBackendUser(token.accessToken);
  if (!user) return;

  token.role = user.role;
  token.roleCheckedAt = Date.now();
}

const handler = NextAuth({
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const params = new URLSearchParams();
          params.append('username', credentials.email);
          params.append('password', credentials.password);

          const loginRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params.toString(),
          });

          // El backend limita los intentos: se distingue del error de
          // credenciales para poder avisar de que hay que esperar, en vez de
          // decir que la contraseña está mal.
          if (loginRes.status === 429) {
            throw new Error('RateLimit');
          }

          if (!loginRes.ok) {
            return null;
          }

          const { access_token, refresh_token, expires_in } =
            (await loginRes.json()) as BackendTokenResponse;

          const meRes = await fetch(`${BACKEND_URL}/api/v1/user/me`, {
            headers: { 'Authorization': `Bearer ${access_token}` },
          });

          if (!meRes.ok) {
            return null;
          }

          const user = await meRes.json();

          return {
            id: String(user.id),
            email: user.email,
            name: `${user.first_name} ${user.last_name}`,
            role: user.role,
            accessToken: access_token,
            refreshToken: refresh_token,
            accessTokenExpiresAt: Date.now() + expires_in * 1000,
          };
        } catch (error) {
          // Un 'RateLimit' se relanza: es información para la pantalla de
          // login, no un fallo de autenticación.
          if (error instanceof Error && error.message === 'RateLimit') {
            throw error;
          }
          console.error('Error de autenticación:', error);
          return null;
        }
      }
    })
  ],
  pages: {
    signIn: '/login',
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.role = (user as any).role;
        token.id = user.id;
        token.accessToken = (user as any).accessToken;
        token.refreshToken = (user as any).refreshToken;
        token.accessTokenExpiresAt = (user as any).accessTokenExpiresAt;
        // El rol recién leído del backend ya está al día.
        token.roleCheckedAt = Date.now();
        return token;
      }

      // Sesión ya abierta: si el token de acceso está por expirar, se pide
      // uno nuevo con el token de refresco. Esto pasa en cada lectura de
      // sesión (/api/auth/session), así que la sesión se renueva sola.
      const expiresAt = token.accessTokenExpiresAt;
      let renewed = false;
      if (token.refreshToken && shouldRefreshAccessToken(expiresAt)) {
        const fresh = await refreshBackendToken(token.refreshToken);
        if (fresh) {
          token.accessToken = fresh.access_token;
          token.accessTokenExpiresAt = Date.now() + fresh.expires_in * 1000;
          renewed = true;
        } else {
          // El token de refresco ya no vale: la sesión se cierra. Se borra
          // también el refresh token para no reintentar en cada lectura.
          token.accessToken = undefined;
          token.refreshToken = undefined;
          token.accessTokenExpiresAt = undefined;
        }
      }

      // El rol se relee del backend: un cambio de rol aplica sin cerrar la
      // sesión. El backend sigue siendo la fuente de verdad (evalúa el rol
      // en cada petición); esto solo mantiene la copia de la cookie al día.
      await refreshRole(token, renewed);

      return token;
    },
    async session({ session, token }) {
      if (token) {
        (session.user as any).role = token.role;
        (session.user as any).id = token.id;
        // El token de acceso NO se copia a la sesión: vive solo dentro de
        // la cookie cifrada y lo lee el servidor (el proxy de la API). Si
        // llegara al navegador, cualquier XSS podría leerlo.
      }
      return session;
    },
  },
  session: {
    strategy: 'jwt',
  },
  secret: process.env.NEXTAUTH_SECRET,
});

export { handler as GET, handler as POST };
