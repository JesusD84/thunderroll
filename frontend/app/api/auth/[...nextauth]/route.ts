
import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';

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

          if (!loginRes.ok) {
            return null;
          }

          const { access_token } = await loginRes.json();

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
          };
        } catch (error) {
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
      }
      return token;
    },
    async session({ session, token }) {
      if (token) {
        (session.user as any).role = token.role;
        (session.user as any).id = token.id;
        (session as any).accessToken = token.accessToken;
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
