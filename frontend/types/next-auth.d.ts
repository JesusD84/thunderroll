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
     * El token de acceso del backend NO está aquí a propósito: vive solo
     * dentro de la cookie cifrada de la sesión y lo lee el servidor (el
     * proxy de la API). Si el navegador lo recibiera, cualquier XSS podría
     * llevárselo.
     */
  }

  interface User {
    id: string
    email: string
    name: string
    role: string
    /**
     * Token de acceso del backend. Solo existe en el servidor (durante el
     * login y dentro de la cookie cifrada).
     */
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
    id?: string
    accessToken?: string
    refreshToken?: string
    accessTokenExpiresAt?: number
    /** Momento (ms epoch) de la última lectura del rol contra el backend. */
    roleCheckedAt?: number
  }
}
