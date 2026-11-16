
import NextAuth from "next-auth"

declare module "next-auth" {
  interface Session {
    user: {
      id: string
      email: string
      name: string
      role: string
    }
    /**
     * Token de acceso del backend. Vive dentro de la cookie de sesión
     * (cifrada), no en el localStorage.
     */
    accessToken?: string
    /** Momento (ms epoch) en que el token de acceso deja de servir. */
    accessTokenExpiresAt?: number
  }

  interface User {
    id: string
    email: string
    name: string
    role: string
    accessToken: string
    /** Token de refresco: sirve para pedir un access token nuevo. */
    refreshToken: string
    /** Momento (ms epoch) en que el token de acceso deja de servir. */
    accessTokenExpiresAt: number
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    role: string
    accessToken?: string
    refreshToken?: string
    accessTokenExpiresAt?: number
  }
}
