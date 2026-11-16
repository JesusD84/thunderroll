# Curso: Next.js 14 + NextAuth 4 — de cero a nivel entrevista

> Material de estudio para el proyecto **Thunderoll** (Next.js `14.2.28`, React `18.2.0`, NextAuth `4.24.7`,
> TypeScript, Tailwind, shadcn/ui).
>
> Cada módulo tiene: **concepto** → **cómo se ve en este repo** → **qué te van a preguntar en una entrevista**.
> Los ejemplos usan el código real del proyecto.

---

## Cómo usar este curso

1. Lee el módulo.
2. Intenta responderte las preguntas de entrevista **en voz alta y sin mirar**. Si no puedes, vuelve al módulo.
3. Haz los ejercicios (están al final, son opcionales pero muy recomendados).
4. Cuando lo domines, pasa al siguiente módulo.

**Al final hay un banco de 25 preguntas de entrevista** con las respuestas modelo.

---

# Módulo 0 · Las 3 capas (esto responde tu pregunta)

Uno de los errores más comunes en entrevistas es confundir estas tres cosas. Memoriza esta tabla:

| Capa | Qué es | Qué te da |
|---|---|---|
| **React** | Librería de UI (Facebook, 2013) | Componentes, `useState`, `useEffect`, JSX |
| **Next.js** | Framework **sobre** React (Vercel, 2016) | Routing por carpetas, renderizado en servidor, optimizaciones, API routes |
| **NextAuth / Auth.js** | Librería de **autenticación** (Vercel) | Login, sesión, cookies, proteger rutas |

```
React          → "cómo construyo una interfaz con componentes"
Next.js        → "cómo la sirvo, ruteo y optimizo"
NextAuth       → "cómo sé quién es el usuario"
```

**¿NextAuth es parte de Next.js? No.** Es una librería **separada**, de los mismos autores (Vercel), que
**solo funciona dentro de Next.js** (porque depende de sus Route Handlers y de su sistema de cookies).
Se instala aparte:

```bash
npm install next-auth
```

### Dato de entrevista

> **P:** ¿NextAuth es parte de Next.js?
> **R:** No. NextAuth (ahora llamado Auth.js) es una librería independiente de Vercel que se integra con
> Next.js. Next.js no trae autenticación; te da las piezas (Route Handlers, cookies, middleware) para que
> construyas la que quieras. NextAuth es una de esas construcciones: una capa que te ahorra escribir el
> flujo de login, el manejo de cookies firmadas y los providers OAuth.

**Ojo con el renombramiento**: `next-auth` v4 (el que usa este proyecto) es la API clásica con
`NextAuth({...})` y `export { handler as GET, handler as POST }`. La v5 (Auth.js) cambió a
`NextAuth(config)` → `handlers` + `auth()`, y usa `AUTH_SECRET` en vez de `NEXTAUTH_SECRET`. Si te
preguntan, di que el proyecto está en v4 y mencionas la v5 como la evolución.

---

# Módulo 1 · ¿Qué problema resuelve Next.js?

React por sí solo te da un archivo HTML vacío y un bundle de JS. El navegador tiene que:
1. descargar el JS,
2. ejecutarlo,
3. y recién entonces pedir datos y pintar.

Consecuencias: **se ve en blanco un rato**, y **los buscadores no ven el contenido** (SEO).

Next.js resuelve esto Permitiendo **generar HTML en el servidor**, antes de que llegue al navegador.

### Los 4 modos de render que debes saber

| Modo | Qué es | Cuándo |
|---|---|---|
| **SSR** (Server-Side Rendering) | El HTML se genera **en cada request** | Contenido que cambia por usuario (dashboard, unidades) |
| **SSG** (Static Site Generation) | El HTML se genera **en el build** | Contenido que no cambia (landing, docs) |
| **ISR** (Incremental Static Regeneration) | Estático que se **revalida** cada X segundos | Catálogo que cambia poco |
| **CSR** (Client-Side Rendering) | El HTML se genera **en el navegador** | Apps muy interactivas (dashboards SPA) |

**En App Router (Next 13+), SSR y SSG son "lo mismo": los Server Components se renderizan en el servidor.**
La diferencia es *cuándo* se ejecuta ese render: en cada request (dinámico) o en el build (estático).

```tsx
// Esto es SSG: se genera en el build, una vez
export const dynamic = 'force-static';

// Esto es SSR: se genera en cada request
export const dynamic = 'force-dynamic';

// Esto es ISR: estático, pero se revalida cada 60s
export const revalidate = 60;

// Esto desactiva el caché de fetch
export const revalidate = 0;
```

> **Dato de entrevista**: "Next.js 15 cambió `params`, `searchParams`, `cookies()` y `headers()` a **async**
> (devuelven Promises). En Next 14 son síncronos. Este proyecto usa Next 14."

---

# Módulo 2 · App Router: el sistema de archivos es el router

```
app/
├── layout.tsx                 # Raíz: <html>, <body>, providers globales
├── page.tsx                   # Ruta "/"
├── loading.tsx                # Skeleton mientras carga
├── error.tsx                  # Error boundary (DEBE ser client component)
├── not-found.tsx              # 404
├── units/
│   ├── page.tsx               # "/units"
│   ├── [id]/
│   │   └── page.tsx           # "/units/42"
│   └── new/
│       └── page.tsx           # "/units/new"
├── api/
│   └── auth/
│       └── [...nextauth]/
│           └── route.ts       # Endpoints HTTP de NextAuth
└── imports/
    ├── page.tsx
    ├── history/page.tsx
    └── [id]/page.tsx
```

### Los archivos especiales y qué hacen

| Archivo | Para qué | ¿Server o Client? |
|---|---|---|
| `layout.tsx` | Envoltura que **se conserva** entre navegaciones | Server (puede tener client dentro) |
| `template.tsx` | Igual que layout pero **se recrea** en cada navegación | Server |
| `page.tsx` | El contenido de la ruta | Server por defecto |
| `loading.tsx` | UI de carga (Suspense boundary implícito) | Server |
| `error.tsx` | Captura errores del subtree | **Obligatoriamente client** (necesita `reset()`) |
| `not-found.tsx` | 404 | Server |
| `route.ts` | Endpoint HTTP (devuelve JSON, no HTML) | **Siempre server** |

**`layout.tsx` vs `template.tsx`**: es pregunta clásica de entrevista.

- `layout.tsx` **se preserva** al navegar → el estado del layout no se resetea. Ideal para shells (navbar, sidebar).
- `template.tsx` **se vuelve a montar** en cada navegación → ideal si quieres resetear estado o animar de nuevo.

En este repo, `app/layout.tsx` monta el `<html>`, el `<SessionProvider>` y la `<Navigation>`:

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={inter.className}>
        <SessionProvider>
          <Navigation />
          <div className="pt-16">{children}</div>
          <Toaster />
        </SessionProvider>
      </body>
    </html>
  );
}
```

> **Dato de entrevista**: "¿Por qué `<html>` y `<body>` deben estar en `layout.tsx` y no en `page.tsx`?"
> Porque solo el layout raíz puede renderizar el documento HTML completo. `page.tsx` renderiza contenido
> **dentro** de ese documento.

---

# Módulo 3 · Server vs Client Components (el corazón de Next 13+)

Esta es **la** pregunta de entrevista más importante de Next.js moderno.

## La regla

- **Por defecto, TODO es Server Component.** Se renderizan en el servidor.
- `'use client'` **marca un componente (y todo lo que importa) como cliente**.

```tsx
'use client';
// ↓ todo lo que este archivo importa también se vuelve Client Component
import { useState } from 'react';
import { Chart } from './Chart';
```

## ⚠️ El malentendido #1: `'use client'` NO significa "se renderiza en el navegador"

Esto es lo que casi todosbelieve y es **falso**.

> `'use client'` **no apaga el server-side rendering.** Dice: *"además de generar HTML, este componente
> también se ejecuta en el navegador"*.

### Las dos fases

```
FASE 1 · PRE-RENDER (servidor, durante el BUILD)
  Next genera el HTML de TODAS las rutas (en este repo: 13).
  · Server Components → se ejecutan en el server
  · Client Components → TAMBIÉN se ejecutan en el server, para generar su HTML
  Resultado: HTML completo guardado como estático, con los datos ya dentro.

FASE 2 · HIDRATACIÓN (navegador, al cargar la página)
  Se descarga el JS y React "despierta" ese HTML:
  le conecta los event handlers y reconstruye el estado.
```

**Evidencia en este repo**: el build dice `✓ Generating static pages (13/13)` y falla en `/units`. Si los
Client Components "se renderizaran en el navegador", **no habría nada que prerenderizar**.

### El experimento que lo demuestra

Quita el `<Suspense>` de `app/units/page.tsx` y prueba:

```bash
npm run dev    →  /units responde HTTP 200   ✅ funciona
npm run build  →  ⨯ useSearchParams() should be wrapped in a suspense boundary
```

**Dev es lenient, build es estricto.** En dev no hay build: Next renderiza bajo demanda, en runtime, y ya
tiene la URL real → `useSearchParams()` no tiene problema. En build tiene que generar el HTML por
adelantado, sin request → sin query params → **CSR bailout** → necesita boundary.

### Por qué el bailout necesita un `<Suspense>`

En el pre-render, `useSearchParams()` se ejecuta en el server. En el build **no hay request**, así que no hay
query string → el componente no puede producir su HTML final → Next marca ese subtree como "esto se
renderiza en el cliente" y necesita un punto de espera para poder hacer un **render parcial**:

- **fuera** del boundary → HTML estático, llega instantáneo
- **dentro** → se resuelve en el cliente, con el `fallback` mientras tanto

Sin boundary, Next tendría que bloquear toda la página → no habría prerender posible → error de build.

### La analogía del restaurante

- **Pre-render** = la cocina deja el plato en el mostrador **antes** de que llegues.
- **Hidratación** = el mesero te da la carta con notas de qué puedes pedir extra (el JS).
- **`'use client'`** = "este plato viene con mesero". **No significa que la cocina no lo cocine.**

Y `useSearchParams()` es un plato cuyo contenido **depende de lo que el cliente escribió en su nota de
pedido**. En el build no hay cliente → no hay nota → hay que hacerlo "bajo pedido" (bailout) → y hace falta
un letrero de "un momento" (el `fallback`).

### La regla de una frase

> Un Client Component **se renderiza dos veces**: una en el servidor (build → HTML) y otra en el navegador
> (hidratación). Por eso los hooks que dependen del request (`useSearchParams`, `usePathname` con search
> params, `cookies()`) necesitan un boundary cuando la ruta se prerenderiza.

### Por qué esto importa en entrevista

La respuesta **naive** a "¿SSR vs CSR en App Router?" es incorrecta:

> ❌ "SSR son los Server Components y CSR los Client Components."

La respuesta correcta:

> ✅ "La distinción no es *quién* renderiza, sino **qué partes del árbol son interactivas**. Un Client
> Component también tiene su HTML prerenderizado en el servidor. Lo que cambia es el **costo**: un Server
> Component no envía JS al navegador; un Client Component envía su JS y además hay que **hidratarlo**
> (re-ejecutar su lógica en el navegador). La hidratación no es solo descargar JS, es trabajo de CPU en el
> cliente."

---

## Qué puede y qué no puede cada uno

| | Server Component | Client Component |
|---|---|---|
| `useState`, `useEffect` | ❌ | ✅ |
| `useRouter`, `usePathname` | ❌ (hooks de Next) | ✅ |
| Acceder a la **sesión del usuario** | ❌ (no la tiene) | ✅ (viene en la cookie httpOnly) |
| Leer **secretos** del servidor (`DATABASE_URL`) | ✅ | ❌ |
| Hablar con la **base de datos** | ✅ | ❌ |
| `window`, `document`, `localStorage` | ❌ | ✅ |
| Eventos (`onClick`, `onChange`) | ❌ | ✅ |
| Bundle JS enviado al navegador | No (se ejecuta en el server) | Sí |

## El patrón "server wrapper + client inner"

> ⚠️ **Ojo: este repo NO usa ese patrón.** En `app/units/page.tsx` el `'use client'` está **al principio del
> archivo**, así que **todo el archivo es Client Module** — incluyendo el `default export`. La única
> Server Component de todo `app/` es `app/layout.tsx`.
>
> El patrón correcto (que verás en la mayoría de proyectos reales de Next 14) requiere **separar en dos
> archivos**, porque `'use client'` es **por archivo**, no por componente:

```tsx
// app/units/page.tsx          ← SIN 'use client' → Server Component
import { Suspense } from 'react';
import { UnitsPageContent } from './UnitsPageContent';

export default function UnitsPage() {
  return (
    <Suspense fallback={<div>Cargando...</div>}>
      <UnitsPageContent />
    </Suspense>
  );
}
```

```tsx
// app/units/UnitsPageContent.tsx   ← CON 'use client' → Client Component
'use client';
export function UnitsPageContent() {
  const [units, setUnits] = useState<Unit[]>([]);
  ...
}
```

**¿Por qué separarlo?** Porque el Server Component se puede prerenderizar estáticamente y **no viaja al
navegador**, y el Client Component sí. Juntarlos en un archivo client significa que **todo** ese JS se
descarga, aunque la mayor parte no lo necesite.

**Regla mental**: `'use client'` es un **directorio de módulo**, no un atributo de función. Si lo pones en
un archivo, **todo lo que hay en ese archivo** (y todo lo que importa) se vuelve cliente.

```tsx
// app/units/page.tsx  (estado ACTUAL de este repo)
'use client';                          // ← TODO el archivo es cliente
import { useState, useEffect, Suspense } from 'react';
function UnitsPageContent() { ... }   // ← cliente
export default function UnitsPage() { // ← ¡también cliente! (mismo archivo)
  return <Suspense><UnitsPageContent /></Suspense>;
}
```

Para que `UnitsPage` fuera Server Component, habría que **mover `UnitsPageContent` a otro archivo**.
Ese es el error conceptual que más se comete al empezar.

**¿Por qué existe el `<Suspense>` en este repo?**

1. `UnitsPageContent` usa `useSearchParams()` (línea 84) — el hook que lee los query params de la URL.
2. En una ruta que Next intenta **prerenderizar estáticamente** en el build, Next **no sabe** qué search
   params tendrá cada visitante → esa parte debe renderizarse en el cliente.
3. Next 14 **exige** un `<Suspense>` alrededor de cualquier componente que use `useSearchParams()`, o el
   build falla con:

   > `useSearchParams() should be wrapped in a suspense boundary at page "/units"`

4. El `<Suspense>` **acota** esa parte dinámica: mientras Next resuelve los search params, se muestra el
   `fallback`; después, el contenido real.

> **Dato de entrevista**: "En App Router, ¿se puede tener un Client Component dentro de uno Server?"
> **Sí**, y es lo estándar. Lo que **no** se puede es al revés: un Server Component importado por un Client
> Component se convierte en Client. La frontera va **hacia abajo** en el árbol.

## La pregunta de oro: "¿cuándo uso Server vs Client?"

**Regla práctica:**

> **¿El componente necesita interactividad o datos del usuario? → Client.**
> **¿Solo muestra datos que el servidor ya tiene? → Server.**

Y un criterio más fino que marca la diferencia:

> Si el componente **no necesita `useState`, `useEffect`, un event handler, ni `useSession`**, déjalo como
> Server Component. Cada `'use client'` que agregas **engorda el bundle de JavaScript** que viaja al
> navegador. Es el error #1 de performance en Next.js.

---

# Módulo 4 · Data fetching en App Router

## En un Server Component (lo nuevo)

```tsx
// app/units/page.tsx — sin 'use client'
export default async function UnitsPage() {
  const res = await fetch(`${process.env.API_URL}/api/v1/units/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const units = await res.json();
  return <table>{/* ... */}</table>;
}
```

Puntos clave:
- Es un `async` component. Puedes hacer `await` directamente.
- El fetch **ocurre en el servidor** → el token **no viaja al navegador**.
- Los datos llegan ya renderizados en el HTML.

**El problema**: en este proyecto, el token del backend **solo existe en el navegador** (vive en la cookie
httpOnly de NextAuth, que el Server Component no puede leer de la misma forma que un Route Handler).
Por eso el proyecto hace el fetch **desde el cliente**. Ese es el motivo real de que `page.tsx` sea client.

## En un Client Component (como este repo)

```tsx
'use client';
useEffect(() => {
  sessionAwareFetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => res.json())
    .then(setUnits);
}, [session]);
```

## Caching (Next 14)

| Config | Efecto |
|---|---|
| `fetch(url)` en Server Component | **Cacheado** por defecto ( indefinitely en 14) |
| `fetch(url, { cache: 'no-store' })` | Sin caché, siempre fresco |
| `fetch(url, { next: { revalidate: 60 } })` | ISR: revalida cada 60s |
| `export const dynamic = 'force-dynamic'` | La ruta completa es dinámico |
| `export const revalidate = 0` | Desactiva caché |

> ⚠️ **Trampa de entrevista**: el caché de `fetch` **solo aplica a Server Components**. En un Client
> Component el fetch del navegador **no** se cachea con el Data Cache de Next. Muchos devs asumen que sí.

---

# Módulo 5 · Server Actions y Route Handlers

## Server Actions (`'use server'`)

Funciones que se ejecutan **en el servidor** pero se invocan **desde el cliente**, como si fueran funciones locales:

```tsx
'use server';
export async function createUnit(data: FormData) {
  // corre en el servidor
  await db.insert(...);
  revalidatePath('/units');   // ← invalida el caché de esa ruta
}
```

```tsx
// en un Client Component
const [state, formAction] = useActionState(createUnit, {});
<form action={formAction}>...</form>
```

Se usan para **mutaciones** (crear, editar, borrar). Ventaja: no expones un endpoint público.

> ⚠️ **Trampa**: una Server Action es un **endpoint HTTP público** por debajo. Si hace algo destructivo,
> **tú validas el auth y el rol dentro de la action**. Next no lo hace por ti.

## Route Handlers (`route.ts`)

Endpoints HTTP dentro de Next.js. **Siempre server-side.**

```ts
// app/api/whatever/route.ts
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  return NextResponse.json({ ok: true });
}
```

En este repo, `app/api/auth/[...nextauth]/route.ts` es un Route Handler. NextAuth publica ahí todos sus
endpoints (`session`, `csrf`, `providers`, `signin`, `signout`, `callback/*`).

**Next.js 14 vs 15**: en 15, `params` en route handlers y pages es una Promise.

---

# Módulo 6 · NextAuth: el flujo completo

## Qué es

NextAuth te da: login con email/password o OAuth, sesión persistente, y helpers para proteger rutas.
**No valida passwords ni guarda usuarios**: eso lo hace tu backend (como en Thunderoll, que usa FastAPI +
PostgreSQL con `bcrypt`).

## El flujo, paso a paso

```
1. Usuario escribe email+password en /login (tu página custom)
        │
2. signIn('credentials', { email, password, redirect: false })
        │  → POST /api/auth/callback/credentials
        ▼
3. route.ts → NextAuth → llama a tu authorize()  [SERVER]
        │
4. authorize() → POST BACKEND_URL/api/v1/auth/login  [tu backend]
        │
5. Backend verifica bcrypt → devuelve access_token (JWT)
        │
6. authorize() → GET BACKEND_URL/api/v1/user/me → { id, email, name, role }
        │
7. NextAuth llama a callbacks.jwt({ token, user }) → mete role, id, accessToken en SU token
        │
8. NextAuth firma el token con NEXTAUTH_SECRET y lo guarda en la cookie
   "next-auth.session-token" (httpOnly, sameSite=lax)
        │
9. En cada página, useSession() → GET /api/auth/session → lee+verifica la cookie → devuelve la sesión
```

## Los 3 providers que debes saber

| Provider | Cómo funciona | Cuándo |
|---|---|---|
| **Credentials** | Tú validas email/password contra **tu** backend | Apps con usuarios propios |
| **OAuth** (Google, GitHub) | El proveedor te da un perfil ya verificado | Si quieres login social |
| **Email** (magic link) | Te manda un link por correo | Sin passwords |

Este proyecto usa **Credentials**, que es el más común en apps B2B.

## `authorize()` — el corazón

```ts
async authorize(credentials) {
  if (!credentials?.email || !credentials?.password) return null;

  const params = new URLSearchParams();
  params.append('username', credentials.email);
  params.append('password', credentials.password);

  const loginRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params.toString(),
  });
  if (!loginRes.ok) return null;          // ← login falló

  const { access_token } = await loginRes.json();

  const meRes = await fetch(`${BACKEND_URL}/api/v1/user/me`, {
    headers: { 'Authorization': `Bearer ${access_token}` },
  });
  if (!meRes.ok) return null;

  const user = await meRes.json();

  return {                                   // ← esto se mete en el token
    id: String(user.id),
    email: user.email,
    name: `${user.first_name} ${user.last_name}`,
    role: user.role,
    accessToken: access_token,
  };
}
```

**Reglas de `authorize()`**:
- Devuelve el objeto de usuario, o `null` si falla (no lances errores).
- Lo que devuelves **se mete dentro del token**. Solo lo que devuelves queda disponible.
- Es **server-side**: aquí sí puedes usar secretos del servidor.

## Los callbacks

```ts
callbacks: {
  // Qué meto en el token (server)
  async jwt({ token, user }) {
    if (user) { token.role = user.role; token.id = user.id; token.accessToken = user.accessToken; }
    return token;
  },
  // Qué expongo al cliente
  async session({ session, token }) {
    session.user.role = token.role;
    session.user.id = token.id;
    session.accessToken = token.accessToken;
    return token;
  },
}
```

**Por qué dos callbacks**: el `jwt` corre cuando se **crea/renueva** el token (login). El `session` corre
**cada vez** que alguien pide `/api/auth/session`. El primero escribe, el segundo lee.

## Estrategia de sesión

```ts
session: { strategy: 'jwt' }   // default si no hay adapter
```

| | `jwt` | `database` |
|---|---|---|
| Dónde vive | En la cookie (firmada, no cifrada) | Una fila en una tabla `sessions` |
| Tabla en tu DB | No | Sí |
| Revocar una sesión | Difícil (hay que esperar al expiry) | Fácil: `DELETE FROM sessions` |
| "Cerrar sesión en todos los dispositivos" | ❌ | ✅ |
| "Ver mis sesiones activas" | ❌ | ✅ |
| RTLS (revocar al cambiar password) | ❌ | ✅ |

**Este proyecto usa `jwt`** → por eso `models.py` no tiene tabla `sessions`.

## `useSession()` vs `getServerSession()`

| | `useSession()` | `getServerSession()` |
|---|---|---|
| Dónde corre | Cliente (browser) | Servidor (Server Component / Route Handler) |
| Import | `next-auth/react` | `next-auth` (v4: `next-auth/next`) |
| Cuándo está disponible | `'use client'` | Server |
| Devuelve | `{ data, status }` | El objeto session o `null` |

En NextAuth v5 cambió a `auth()`.

---

# Módulo 7 · Proteger rutas

## Tres mecanismos

### 1. `middleware.ts` (lo más eficiente)

Un archivo en la **raíz** del proyecto. Se ejecuta **antes** de que se renderice cualquier página, tanto
en el server como en el edge.

```ts
// middleware.ts
export { default } from 'next-auth/middleware';

export const config = {
  matcher: ['/units/:path*', '/imports/:path*'],   // qué rutas proteger
};
```

Con `withAuth` + `authorized`:

```ts
import { withAuth } from 'next-auth/middleware';

export default withAuth(
  function middleware(req) {
    // req.nextUrl.pathname y req.nextauth.token
  },
  { callbacks: { authorized: ({ token, req }) => token?.role === 'admin' } }
);
```

**Ventaja**: el usuario no logueado **ni llega a ver la página** (ni el HTML). Es la mejor opción para
proteger de verdad.

> ⚠️ **Este repo NO tiene `middleware.ts`.** Toda la protección es del lado del cliente:
> `app/units/page.tsx` hace `router.replace('/')` si no tiene permisos, y `Navigation.tsx` esconde los
> menús. Eso **no es seguridad** — solo UX: el HTML y la lógica se siguen descargando.
> **En una entrevista, mencionar esto es un plus enorme**: "el gating del cliente es cosmético; la
> seguridad real está en `require_role()` del backend".

### 2. Por página (server)

```tsx
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/auth';

export default async function Page() {
  const session = await getServerSession(authOptions);
  if (!session) redirect('/login');
  return <ProtectedContent />;
}
```

### 3. Por API (obligatorio)

El backend **siempre** valida. Un `require_role([UserRole.ADMIN])` en FastAPI es la frontera de confianza real.

### El patrón completo y correcto

```
middleware.ts   →  puerta de entrada (UX rápida, evita flashes)
Server Component →  verificación real en el render
API / backend    →  verificación REAL (obligatoria, nunca confíes en el frontend)
```

---

# Módulo 8 · Roles y RBAC

NextAuth **no tiene RBAC**. Solo te da `session.user.role` (lo que tú metiste en el callback `jwt`).
El control de acceso lo implementas tú.

En este repo:

| Backend (`lib/auth.ts`) | Frontend (`lib/auth.ts`) |
|---|---|
| `require_role([UserRole.ADMIN, UserRole.MANAGER])` | `getPermissions(role).manageEquivalences` |

Y son **espejo**: la UI esconde botones que la API rechazaría con 403.

> **Dato de entrevista**: "¿Cómo manejas roles en Next.js?"
> Respuesta: "El rol viaja en el JWT de sesión (lo pongo en el callback `jwt`). En el cliente uso un hook
> tipo `useAuth()` que deriva permisos y esconde acciones. Pero **el gating del cliente es solo UX**: la
> autorización real tiene que estar en el servidor, porque cualquiera puede llamar la API directamente."

---

# Módulo 9 · Seguridad — lo que NO debes hacer

| ❌ Mal | ✅ Bien | Por qué |
|---|---|---|
| Guardar el token en `localStorage` | Cookie **httpOnly** | `localStorage` es legible por cualquier XSS |
| Confiar en el frontend para autorizar | Validar en el backend | El cliente se puede modificar |
| `JWT_SECRET` en `NEXT_PUBLIC_*` | Secreto solo en el server | `NEXT_PUBLIC_` = visible para todos |
| Comparar passwords con `==` | `bcrypt`/`argon2` | Los hashes no se comparan, se verifican |
| Sesión "database" sin `expires` | Fecha de expiración | Sesiones eterno = puerta abierta |

### CSRF

NextAuth gestiona el token CSRF internamente (`/api/auth/csrf`). Si haces POSTs a **tu** API desde el
cliente, considera un header anti-CSRF o que el token Bearer ya te protege (al estar en un header
personalizado, no se puede mandar en un form simple).

---

# Módulo 10 · Trampas comunes

| Trampa | Síntoma | Solución |
|---|---|---|
| `useSearchParams()` sin `<Suspense>` | Error de build: "useSearchParams() should be wrapped in a suspense boundary" | Envolver en `<Suspense>` (como en `app/units/page.tsx`) |
| `error.tsx` sin `'use client'` | Error de build | `error.tsx` **debe** ser client (usa `reset()`) |
| Olvidar `await` en un Server Component async | Render con datos vacíos | `await` siempre |
| Poner `<html>` en `page.tsx` | Error: solo el layout raíz puede | Va en `layout.tsx` |
| `params` como Promise | En Next 15, `params` es async | `const { id } = await params` |
| Cachear un fetch con datos de usuario | Fuga de datos entre usuarios | `cache: 'no-store'` o `dynamic = 'force-dynamic'` |
| Confiar en `useSearchParams` para auth | Manipulable por el usuario | Autorización real en el server |
| `use client` en todo | Bundle enorme, peor performance | Client solo lo que lo necesite |

---

# Módulo 11 · Banco de preguntas de entrevista

## Next.js — nivel foundational

**P1. ¿Qué es Next.js y qué problema resuelve?**
> Framework de React que añade renderizado en servidor, routing por sistema de archivos, optimización de
> bundle y construcción de API. Resuelve el problema del "HTML vacío + JS que tarda" y el SEO.

**P2. ¿Server Components vs Client Components?**
> Los Server Components se renderizan en el servidor por defecto: pueden acceder a la DB y a secretos, no
> van al bundle JS, pero no pueden usar estado ni eventos. Los Client Components (`'use client'`) corren en
> el navegador: pueden usar `useState`/`useEffect` y leer la sesión del usuario. Un Server Component puede
> importar un Client Component; al revés, el Server se vuelve Client.

**P3. ¿SSR vs SSG vs CSR?**
> SSR = HTML por request. SSG = HTML en el build. CSR = el JS genera el HTML en el navegador. En App
> Router, SSR y SSG se controlan con `dynamic` y `revalidate`.

**P4. ¿Qué es un layout? ¿Y la diferencia con template?**
> `layout.tsx` envuelve la ruta y **se preserva** entre navegaciones (estado intacto). `template.tsx` se
> vuelve a montar en cada navegación. El layout raíz es el único que puede renderizar `<html>`.

**P5. ¿Qué son las Server Actions?**
> Funciones marcadas con `'use server'` que se ejecutan en el servidor pero se invocan desde el cliente,
> como `formAction`. Ideales para mutaciones. Son endpoints HTTP públicos: valida auth y rol dentro.

**P6. ¿Qué es un Route Handler?**
> Un endpoint HTTP dentro de Next.js (`app/api/.../route.ts`). Siempre server-side. Devuelve JSON o
> respuestas, no HTML.

**P7. ¿Cómo reduces el bundle de JS?**
> Server Components por defecto, `'use client'` solo donde haga falta, `next/dynamic` para lazy loading,
> `next/image` para imágenes, `next/font` para fuentes (self-hosting).

## NextAuth — nivel foundational

**P8. ¿Qué es NextAuth?**
> Librería de autenticación para Next.js (Vercel). Gestiona login, sesión y cookies firmadas. No valida
> passwords ni guarda usuarios: delega en tu backend o en un proveedor OAuth.

**P9. ¿Cómo funciona el flujo de login?**
> `signIn()` → POST a `/api/auth/callback/<provider>` → NextAuth llama a `authorize()` → si devuelve un
> usuario, el callback `jwt` mete los datos en un token → NextAuth lo firma con `NEXTAUTH_SECRET` y lo
> guarda en la cookie httpOnly `next-auth.session-token` → `useSession()` la lee vía
> `/api/auth/session`.

**P10. ¿Qué es `authorize()`?**
> La función server-side donde validas las credenciales contra tu backend. Devuelve el objeto de usuario
> o `null`. Lo que devuelves es lo que queda disponible en la sesión.

**P11. ¿Cookie vs localStorage para el token?**
> Cookie httpOnly: invisible al JS (protege contra XSS), el navegador la manda sola. `localStorage` es
> legible por cualquier script inyectado. Por eso NextAuth usa cookie httpOnly + `sameSite`.

**P12. ¿Qué es un JWT y está cifrado?**
> Un formato de token con 3 partes: header, payload y firma. **Firmado, no cifrado**: cualquiera con el
> token puede leer su contenido; lo que impide falsificarlo es la firma. Por eso no se deben meter datos
> sensibles en el payload.

**P13. ¿Sesión con JWT vs con base de datos?**
> JWT en cookie: sin tabla extra, pero no se puede revocar antes del expiry. DB: fila de sesión, se puede
> revocar y listar dispositivos, pero necesita tabla y queries.

**P14. ¿Cómo proteges rutas?**
> Tres capas: `middleware.ts` (antes de renderizar, evita flashes), verificación en el Server Component
> (`getServerSession` + `redirect`), y **siempre** autorización en la API. El gating del cliente es UX, no
> seguridad.

**P15. ¿Cómo manejas roles?**
> NextAuth no tiene RBAC. Guardas el rol en el token (callback `jwt`) y derivas permisos en un hook
> (`useAuth`). Pero la autorización real va en el servidor.

**P16. ¿Qué es el callback `session` vs `jwt`?**
> `jwt` = qué escribes en el token (corre al crear/renovar la sesión). `session` = qué expones al cliente
> (corre en cada lectura de la sesión).

**P17. ¿Cómo manejas el "sesión expirada"?**
> Un 401 de la API dispara un flujo centralizado: cerrar sesión (borrar la cookie vía el endpoint
> `signout`) y redirigir a login con un `callbackUrl` validado. Se hace single-flight para no disparar N
> signouts con N requests en paralelo.

**P18. ¿Por qué es peligroso un `callbackUrl` sin validar?**
> Open redirect: un atacante manda `/login?callbackUrl=https://evil.com` y, tras loguearse, el usuario es
> redirigido a un sitio de phishing. Se valida que sea una ruta relativa interna.

## Preguntas de nivel "senior" (las que differentiation)

**P19. ¿Por qué Next 15 hizo async `params` y `searchParams`?**
> Para que el framework pueda ir liberando el render de forma streaming: no bloquea el HTML por esperar
> los params. Rompe compatibilidade, por eso hay que ver la versión.

**P20. ¿Cómo cachearías un endpoint que cambia seguido?**
> `cache: 'no-store'` en el fetch, o `export const dynamic = 'force-dynamic'`. Y `revalidatePath()` /
> `revalidateTag()` desde una Server Action después de mutar.

**P21. ¿Cómo evitas que un usuario vea datos de otro en una página cacheada?**
> Nunca uses caché de Next para datos dependientes del usuario. O `no-store`, o render dinámico, o
> incluye el userId en la clave de caché.

**P22. Diferencia entre `useSession()` y `getServerSession()`.**
> El primero corre en el browser y te da `{data, status}` (puede ser `null` mientras carga). El segundo
> corre en el server y te da la sesión o `null`, sin estado de carga.

**P23. ¿Por qué este proyecto hace el fetch desde el cliente y no desde el Server Component?**
> Porque los datos dependen del token del backend, y ese token solo existe en el navegador (dentro de la
> cookie httpOnly de NextAuth, accesible por el Route Handler pero no por el Server Component de la app).
> El patrón correcto cuando el token está en el cliente es fetch client-side, o usar Route Handlers /
> Server Actions donde sí se puede leer la cookie.

**P24. ¿Qué harías si tuvieras que invalidar todas las sesiones de un usuario?**
> Cambiar a `strategy: 'database'` y borrar las filas de `sessions` de ese usuario. Con JWT puro, el token
> sigue vivo hasta su `exp` (por eso el TTL de la cookie y del access token importan).

**P25. Un cliente dice que "el botón de borrar no hace nada" en la UI, pero la API sí borra. ¿Dónde está el bug?**
> Probablemente en el gating: la acción depende de un permiso que el usuario no tiene (403) y el frontend no
> distingue "sin permiso" de "error". Revisar `getPermissions` vs `require_role`, y que el handler de error
> muestre el 403 con un mensaje claro.

---

# Módulo 12 · Ejercicios con ESTE proyecto

## E1 · Traza el login (30 min)
1. `app/login/page.tsx` → ¿qué llama? (`signIn`)
2. `app/api/auth/[...nextauth]/route.ts` → ¿qué llama? (tu backend)
3. `backend/app/api/v1/endpoints/auth.py` → ¿qué verifica? (bcrypt)
4. Dibuja el camino completo del password: ¿dónde viaja **cifrado** (hash) y en qué momento?

## E2 · Rompe algo a propósito (45 min)
1. En `backend/app/services/auth_service.py`, cambia `ACCESS_TOKEN_EXPIRE_MINUTES` a `1`.
2. Reinicia el backend, haz login, espera 2 minutos, navega a `/units`.
3. **Observa** qué pasa: ¿se cierra la sesión sola? ¿a dónde te manda?
4. **Explica** el flujo: `sessionAwareFetch` → 401 → `handleSessionExpired` → `signOut()` → `/login?reason=expired`.
5. **Arreglalo** y explica por qué `safeCallbackUrl` existe.

## E3 · El bug del rol (30 min)
1. En `frontend/lib/auth.ts`, cambia `manageUnits: isAdmin || isManager` por `manageUnits: true`.
2. Haz login como `operator` y mira el botón "Nueva unidad" en `/units`.
3. ¿Qué **pasa** en la UI? ¿Y qué pasa si haces click? (mira el 403 del backend)
4. Explica por qué el espejo entre `getPermissions` y `require_role` importa.

## E4 · La cookie (15 min)
1. DevTools → Application → Cookies → `next-auth.session-token`.
2. Pégalo en jwt.io o en el script de Python del ramp-up.
3. ¿Qué hay dentro? ¿Ves el `accessToken` del backend ahí? ¿Y el `role`?
4. ¿Por qué eso es un problema si el token fuera httpOnly: false?

## E5 · Escribe desde cero (60 min)
Implementa un Route Handler propio: `app/api/health/route.ts` que devuelva
`{ status: 'ok', user: session?.user?.email ?? null }` usando `getServerSession`.
Objetivo: que entiendas por qué un Route Handler **sí** puede leer la sesión.

---

# Módulo 13 · Checklist de autoevaluación

Antes de una entrevista, deberías poder:

- [ ] Explicar React vs Next.js vs NextAuth sin tartamudear
- [ ] Dibujar el flujo de login completo de memoria
- [ ] Explicar Server vs Client Component y dar un ejemplo del repo
- [ ] Nombrar los 4 modos de render y cuándo usar cada uno
- [ ] Decir la diferencia entre `layout.tsx` y `template.tsx`
- [ ] Explicar `authorize()`, `jwt` callback y `session` callback
- [ ] Explicar por qué cookie httpOnly y no localStorage
- [ ] Comparar JWT vs session en base de datos
- [ ] Explicar las 3 capas de protección de rutas
- [ ] Saber por qué el gating del cliente NO es seguridad
- [ ] Responder "qué pasa si el token expira" con el flujo exacto
- [ ] Mencionar el versionado (Next 14 vs 15, next-auth v4 vs Auth.js v5)

---

# Recursos

- **Docs oficiales Next.js**: https://nextjs.org/docs (App Router: `/docs/app`)
- **Docs Auth.js / NextAuth**: https://next-auth.js.org/getting-started/introduction
- **Next.js Learn** (tutorial interactivo, gratis): https://nextjs.org/learn
- **MDN HTTP**: https://developer.mozilla.org/es/docs/Web/HTTP
- **jwt.io** — para decodificar tokens
- **OWASP**: https://owasp.org/www-project-cheat-sheets/
