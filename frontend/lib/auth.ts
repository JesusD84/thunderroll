
/**
 * Authentication configuration for NextAuth.js
 */

import { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { apiClient } from "./api-client";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const response = await apiClient.post('/auth/login', {
            email: credentials.email,
            password: credentials.password
          });

          if (response.status === 200) {
            const { access_token } = response.data;
            
            // Get user info with the token
            const userResponse = await apiClient.get('/auth/me', {
              headers: {
                Authorization: `Bearer ${access_token}`
              }
            });

            return {
              id: userResponse.data.id.toString(),
              email: userResponse.data.email,
              name: userResponse.data.name,
              role: userResponse.data.role,
              accessToken: access_token
            };
          }
        } catch (error) {
          console.error('Auth error:', error);
        }

        return null;
      }
    })
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.accessToken;
        token.role = user.role;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.user.role = token.role as string;
      return session;
    }
  },
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: 'jwt',
  }
};
