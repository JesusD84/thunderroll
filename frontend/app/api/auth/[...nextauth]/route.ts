
import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';

import {
  BackendTokenResponse,
  refreshBackendToken,
  shouldRefreshAccessToken,
} from '@/lib/backend-auth';

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

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
        return token;
      }

      // Sesión ya abierta: si el token de acceso está por expirar, se pide
      // uno nuevo con el token de refresco. Esto pasa en cada lectura de
      // sesión (/api/auth/session), así que la sesión se renueva sola.
      const expiresAt = token.accessTokenExpiresAt;
      if (token.refreshToken && shouldRefreshAccessToken(expiresAt)) {
        const fresh = await refreshBackendToken(token.refreshToken);
        if (fresh) {
          token.accessToken = fresh.access_token;
          token.accessTokenExpiresAt = Date.now() + fresh.expires_in * 1000;
        } else {
          // El token de refresco ya no vale: la sesión se cierra. Se borra
          // también el refresh token para no reintentar en cada lectura.
          token.accessToken = undefined;
          token.refreshToken = undefined;
          token.accessTokenExpiresAt = undefined;
        }
      }

      return token;
    },
    async session({ session, token }) {
      if (token) {
        (session.user as any).role = token.role;
        (session.user as any).id = token.id;
        (session as any).accessToken = token.accessToken;
        (session as any).accessTokenExpiresAt = token.accessTokenExpiresAt;
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
