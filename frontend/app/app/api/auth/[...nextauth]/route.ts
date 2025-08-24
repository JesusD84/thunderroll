
import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { PrismaClient, UserStatus } from '@prisma/client';
import bcrypt from 'bcryptjs';

export const dynamic = "force-dynamic";

const prisma = new PrismaClient();

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
          // Buscar usuario en la base de datos
          const user = await prisma.user.findUnique({
            where: { 
              email: credentials.email,
              status: UserStatus.ACTIVE 
            }
          });

          if (!user || !user.hashedPassword) {
            return null;
          }

          // Verificar contraseña
          const isValid = await bcrypt.compare(credentials.password, user.hashedPassword);
          
          if (!isValid) {
            return null;
          }

          // Actualizar último login
          await prisma.user.update({
            where: { id: user.id },
            data: { lastLoginAt: new Date() }
          });

          return {
            id: user.id,
            email: user.email,
            name: user.name || user.email,
            role: user.role
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
      }
      return token;
    },
    async session({ session, token }) {
      if (token) {
        (session.user as any).role = token.role;
        (session.user as any).id = token.id;
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
