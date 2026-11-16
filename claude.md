# CLAUDE.md — Thunderoll

## Qué es este proyecto

Sistema de trazabilidad de inventario para **Thunderoll**, empresa de scooters/motos en Guadalajara. Rastrea unidades desde importación hasta venta, pasando por bodega, taller, tránsito y sucursales.

> **Onboarding:** [`docs/RAMPEO_PRODUCTO.md`](./docs/RAMPEO_PRODUCTO.md) (negocio y cliente) · [`docs/RAMPEO_TECNICO.md`](./docs/RAMPEO_TECNICO.md) (stack, cómo correr el código, primer PR) · [`AGENTS.md`](./AGENTS.md) (contexto rápido cross-agent).

---

## Stack tecnológico

| Capa | Tecnología | Versión clave |
|------|-----------|---------------|
| **Backend** | FastAPI + SQLAlchemy (sync) + Alembic | Python 3.11+, FastAPI 0.135 |
| **Frontend** | Next.js (App Router) + TypeScript + TailwindCSS | Next 14.2, React 18.2 |
| **DB** | PostgreSQL 15 | psycopg2-binary (sync) |
| **Auth frontend** | NextAuth 4.x con JWT del backend | |
| **Auth backend** | python-jose + passlib/bcrypt + OAuth2PasswordBearer | |
| **UI Components** | shadcn/ui (Radix primitives) + Lucide icons | |
| **State** | Zustand, Jotai, SWR, TanStack Query (todos instalados) | |
| **Formularios** | react-hook-form + zod (y también formik + yup) | |
| **Orquestación** | Docker Compose (postgres, backend, frontend) | |

---

## Estructura del proyecto

```
thunderroll/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── router.py              # Monta /api/v1
│   │   │   └── v1/
│   │   │       ├── router.py           # Registra todos los endpoint routers
│   │   │       └── endpoints/
│   │   │           ├── auth.py          # Login, refresh y reset de contraseña (JWT + rate limit)
│   │   │           ├── units.py         # CRUD de unidades (+ /stats, filtro server-side, paginación)
│   │   │           ├── locations.py     # Ubicaciones
│   │   │           ├── imports.py       # Importación Excel (/preview, /upload, historial, errores)
│   │   │           ├── model_equivalences.py # Equivalencias de modelo (+ /unmapped)
│   │   │           ├── transfers.py     # Transferencias entre ubicaciones
│   │   │           ├── reports.py       # Reportes y exportaciones
│   │   │           └── user.py          # Gestión de usuarios
│   │   ├── core/
│   │   │   ├── security.py             # CryptContext para bcrypt
│   │   │   ├── config.py               # Config validada al importar (SECRET_KEY, DATABASE_URL)
│   │   │   ├── cors.py                 # Orígenes permitidos (localhost solo en development)
│   │   │   └── rate_limit.py           # slowapi: límites por IP y por cuenta
│   │   ├── database/
│   │   │   ├── database.py             # Engine, SessionLocal, Base, get_db
│   │   │   └── seed.py                 # Bootstrap: crea la cuenta admin si la DB está vacía (corre en startup)
│   │   ├── models/
│   │   │   ├── models.py               # SQLAlchemy models (User, Location, Unit, Transfer, ModelEquivalence, Import, ImportError)
│   │   │   └── schemas.py              # Pydantic schemas (Token, Unit, Transfer, etc.)
│   │   ├── repositories/               # Capa de acceso a datos
│   │   ├── schemas/                    # Schemas Pydantic adicionales por dominio
│   │   ├── services/                   # Lógica de negocio
│   │   │   ├── auth_service.py         # JWT, password hashing, RBAC
│   │   │   ├── unit_service.py
│   │   │   ├── transfer_service.py
│   │   │   ├── import_parser.py        # Parser tolerante a esquemas del Excel del proveedor
│   │   │   ├── model_equivalence_service.py
│   │   │   ├── location_service.py
│   │   │   ├── user_service.py
│   │   │   ├── report.py
│   │   │   ├── email.py
│   │   │   └── ...
│   │   └── main.py                     # FastAPI app, CORS, lifespan
│   ├── migrations/                     # Alembic (configurado; el deploy NO lo usa, las tablas se crean con create_all)
│   ├── tests/                          # pytest (SQLite en memoria, SYNC)
│   ├── requirements.txt
│   ├── pyproject.toml                  # ruff, black, mypy, pytest config
│   └── Dockerfile
├── frontend/
│   ├── app/                            # Next.js App Router
│   │   ├── page.tsx                    # Dashboard principal
│   │   ├── login/page.tsx
│   │   ├── units/page.tsx              # Listado de unidades
│   │   ├── units/[id]/page.tsx         # Detalle de unidad
│   │   ├── units/new/page.tsx          # Nueva unidad
│   │   ├── imports/page.tsx            # Importación Excel (wizard: upload → preview → mapeo → import)
│   │   ├── imports/history/page.tsx    # Historial de imports (+ borrado, solo ADMIN)
│   │   ├── imports/[id]/page.tsx       # Detalle de import + errores por fila
│   │   ├── model-equivalences/page.tsx # CRUD de equivalencias + modelos sin equivalencia
│   │   ├── transfers/page.tsx          # Transferencias
│   │   ├── reports/page.tsx            # Reportes
│   │   ├── settings/page.tsx           # Configuración
│   │   ├── api/auth/                   # NextAuth route handler
│   │   ├── layout.tsx                  # Root layout (Inter font, SessionProvider, Navigation)
│   │   └── globals.css
│   ├── lib/                            # Helpers compartidos del cliente
│   │   ├── api.ts                      # apiFetch / sessionAwareFetch (inyecta Bearer, maneja 401)
│   │   ├── imports.ts                  # Funciones tipadas + tipos del contrato de imports
│   │   ├── auth.ts                     # useAuth + getPermissions (gating por rol)
│   │   ├── session-expiry.ts           # handleSessionExpired + safeCallbackUrl
│   │   ├── session-refresh.ts          # refreshAccessToken (single-flight) ante un 401
│   │   ├── backend-auth.ts             # Cliente del backend: refreshBackendToken + shouldRefreshAccessToken
│   │   └── utils.ts                    # (types.ts es boilerplate sin uso)
│   ├── components/
│   │   ├── Navigation.tsx              # Navbar principal
│   │   ├── imports/                    # PreviewResult.tsx, ImportResult.tsx
│   │   ├── providers/SessionProvider   # NextAuth wrapper
│   │   └── ui/                         # shadcn/ui (button, card, table, select, etc.)
│   ├── types/next-auth.d.ts            # Session/JWT type augmentation
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── Dockerfile
├── docker-compose.yml                 # Stack local (postgres + backend + frontend)
├── render.yaml                         # Blueprint de Render (backend + DB)
└── .env.example
```

---

## Modelos de datos clave

### Enums (valores reales en `models.py`)
- **UserRole**: `admin`, `manager`, `operator` (mostrado como "Operativo" en la UI; sin acceso a imports/equivalencias/reportes/usuarios, solo lectura de units + despachar/recibir transferencias)
- **UnitStatus**: `WAREHOUSE_UNIDENTIFIED`, `AVAILABLE`, `SOLD`, `IN_TRANSIT`
- **TransferStatus**: `PENDING`, `IN_TRANSIT`, `RECEIVED`, `CANCELLED`

### Tablas principales
- **users** — email, username, first_name, last_name, role, hashed_password, is_active, token_version (contador de revocación; viaja dentro de los tokens)
- **locations** — name, address
- **units** — engine_number (unique, nullable), chassis_number (unique, nullable), model, brand, color, current_location_id, status, sold_date, notes
- **transfers** — unit_id, dispatched_by_id, received_by_id, origin_location_id, destination_location_id, status, dispatched_at, received_at (**una transferencia = una unidad**, no hay tabla pivote)
- **model_equivalences** — manufacturer_model (unique), internal_model, notes, created_at, updated_at (mapea el nombre de modelo del fabricante al modelo interno del cliente)
- **imports** — filename, original_filename, total_records, successful_imports, failed_imports, user_id, status, import_date, completed_at
- **import_errors** — import_id, row_number, error_message, raw_data

> No existe tabla `movements` ni enum `MovementType`. La trazabilidad se reconstruye a partir de los `transfers` y del `status`/`sold_date` de cada unidad.

---

## Autenticación y tokens

Todos los tokens son JWT firmados con `SECRET_KEY`. Cada token dice **qué es** (`typ`) y **a qué versión de la cuenta** pertenece (`ver`); ambos claims se validan en el punto de uso, así que un token solo sirve para lo suyo.

### Claims

| Claim | Significado |
|-------|-------------|
| `sub` | id del usuario (nunca el username) en los tokens de acceso y refresco; email en los de reset |
| `typ` | `access` \| `refresh` \| `password_reset` |
| `ver` | `users.token_version` de la cuenta: si no coincide con el valor guardado, el token está revocado |
| `exp` | caducidad (acceso 60 min, refresco 7 días, reset de contraseña 15 min) |

### Tipos de token

| `typ` | Para qué sirve | Cómo queda invalidado |
|-------|----------------|-----------------------|
| `access` | Credencial de la API (`Authorization: Bearer …`) | Al expirar, o al subir `token_version` |
| `refresh` | Pedir un `access` nuevo sin volver a autenticarse | Al expirar, o al subir `token_version` |
| `password_reset` | Canjear la contraseña desde el email | **De un solo uso**: al canjearlo, la contraseña cambia y el contador sube |

Cada tipo se rechaza donde se espera el otro: un token de reset no abre sesión (**401**) y un token de acceso no resetea contraseñas (**400**).

### Revocación (`users.token_version`)

No hay session store: la revocación se hace con un contador entero en `users.token_version` que viaja dentro del token.

- Se **incrementa** al cambiar la contraseña, al resetearla, al cambiar el rol y al desactivar la cuenta.
- Un token cuyo `ver` no coincide con el valor guardado → **401**.
- El token de reset también queda invalidado por lo mismo: al canjearlo, la contraseña cambia, el contador sube y ese token no se puede usar dos veces.

### Contrato de los endpoints

`POST /api/v1/auth/login` (form-urlencoded) →
```json
{ "access_token": "…", "refresh_token": "…", "token_type": "bearer", "expires_in": 3600 }
```

`POST /api/v1/auth/refresh` — cabecera `Authorization: Bearer <refresh_token>` →
```json
{ "access_token": "…", "refresh_token": "…", "token_type": "bearer", "expires_in": 3600 }
```

Devuelve un `access_token` nuevo; el `refresh_token` **no rota** (7 días fijos desde su emisión). Un refresh token revocado, expirado o de otro tipo → **401**.

`POST /api/v1/auth/forgot-password` → `{"message": "…"}`, siempre **200** exista o no la cuenta. El correo se manda en un `BackgroundTask`: un SMTP roto no cambia la respuesta, solo queda en el log.

`POST /api/v1/auth/reset-password` (`{"token": "…", "new_password": "…"}`) → **200** o **400**.

### Rate limiting

`login` y `forgot-password`: 5/min por IP **y** por cuenta. `refresh`: 30/min por IP y por cuenta. Al pasarse: **429**.

---

## Patrones de arquitectura

### Backend
- **Patrón Repository-Service-Router**: `repositories/` → `services/` → `api/v1/endpoints/`
- **Dependency Injection**: FastAPI `Depends()` para DB session (`get_db`) y auth (`get_current_user`)
- **RBAC**: `require_role([UserRole.ADMIN, ...])` como dependency
- **DB sync** (no async): `create_engine` + `sessionmaker` regulares con psycopg2-binary
- **Schemas duplicados**: Existen en `app/models/schemas.py` Y en `app/schemas/` (por dominio). Los endpoints usan ambos.
- **Seed automático**: `create_demo_data()` corre en el lifespan de FastAPI al iniciar

### Frontend
- **Next.js App Router** (no Pages Router)
- **Path alias**: `@/*` apunta a la raíz del frontend
- **Auth**: NextAuth con custom credentials provider que llama al backend JWT
- **Session type** extendida en `types/next-auth.d.ts` con `role`, `accessToken` y `accessTokenExpiresAt`
- **UI**: shadcn/ui components en `components/ui/`
- **Fetching**: el patrón consolidado es `fetch` + `useState` vía `lib/api.ts` (`apiFetch` inyecta el `Bearer`); SWR, TanStack Query, Zustand y Jotai están instalados pero **no** son el estándar usado
- **Permisos en UI**: `lib/auth.ts` (`useAuth` + `getPermissions`) es la única fuente de gating del frontend; refleja las reglas de `require_role` del backend
- **401 / sesión expirada**: `lib/session-expiry.ts` (`handleSessionExpired`, single-flight) cierra sesión y redirige a `/login?reason=expired&callbackUrl=…`; `safeCallbackUrl()` bloquea redirects externos. Las peticiones autenticadas deben ir por `sessionAwareFetch()`
- **Refresco de sesión**: el access token dura 60 min; el `refresh_token` (7 días) permite renovarlo sin volver a autenticarse. El backend renueva de forma proactiva en el callback `jwt` de NextAuth (`lib/backend-auth.ts`), y `lib/api.ts` reintenta la petición una vez si el backend responde 401. Si el refresh tampoco vale, cae al flujo de sesión expirada

---

## Comandos de desarrollo

### Con Docker (recomendado)
```bash
docker compose up --build          # Levantar todo
docker compose down -v             # Bajar y limpiar volúmenes
```

### Local (sin Docker)
```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # servidor
python -m app.database.seed                                # poblar datos demo
alembic upgrade head                                       # migraciones (opcional)

# Frontend
cd frontend
npm install --legacy-peer-deps
npm run dev                        # next dev en :3000
```

### Testing
```bash
cd backend && pytest tests/ -v     # Backend (pytest)
cd frontend && npm test            # Frontend (vitest)
cd frontend && npm run test:e2e    # E2E con Playwright
```

### Linting / Formateo (backend)
```bash
cd backend && ruff check app/      # lint
cd backend && black app/           # formateo
```

---

## CI/CD

- **CI (GitHub Actions)**: en cada PR hacia `main` corren dos checks, `Backend Tests` (pytest) y `Frontend Tests` (vitest). No tienen filtros de path: ambos corren siempre.
- **Branch protection en `main`**: requiere PR, que ambos checks pasen, rama actualizada (strict) y conversaciones resueltas. No se permite push directo ni force-push.
- **CD Frontend (Vercel)**: preview por PR, producción al mergear a `main` (`thunderroll.vercel.app`).
- **CD Backend + DB (Render)**: deploy al push a `main` vía `render.yaml` (runtime python; FastAPI + PostgreSQL).
- **Variables clave en Vercel**: `BACKEND_URL` (login server-side de NextAuth) **y** `NEXT_PUBLIC_API_URL` (llamadas del navegador) — ambas necesarias y distintas. Detalle completo en `CI_CD_PLAN.md`.

---

## URLs en desarrollo

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| API Backend | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

### API prefix
Todos los endpoints de negocio van bajo `/api/v1/` (ej: `/api/v1/auth/login`, `/api/v1/units`)

---

## Credenciales demo (seed)

`create_demo_data()` solo siembra una cuenta bootstrap cuando la tabla `users` está vacía — MANAGER y OPERATOR ya no se auto-crean, se dan de alta desde esa cuenta en Configuración → Usuarios.

La contraseña del admin bootstrap **no está en el repositorio**: usa `BOOTSTRAP_ADMIN_PASSWORD` si está definida; si no, el seed genera una aleatoria y la imprime una sola vez en el log de arranque. Cámbiala desde Configuración → Usuarios.

---

## Cosas importantes a saber

1. **La DB es sync**: el app usa SQLAlchemy sync con `psycopg2-binary`. Los tests en `conftest.py` también usan SQLite en memoria **sync** (no async), coinciden con el app y **corren correctamente** (pasan en CI).

2. **Schemas duplicados**: Pydantic schemas existen en dos lugares: `app/models/schemas.py` (monolítico) y `app/schemas/` (separados por dominio). Al agregar/modificar schemas, verificar cuál se usa en el endpoint correspondiente.

3. **Múltiples libs de state management instaladas**: Zustand, Jotai, SWR y TanStack Query están todas en package.json. El patrón consolidado del proyecto es `fetch` + `useState` vía `lib/api.ts` — al hacer nuevas features, seguir ese patrón y no introducir otra librería.

4. **Múltiples libs de forms**: react-hook-form + zod y formik + yup coexisten.

5. **Desarrollo local**: la forma recomendada es `docker compose up --build`. No hay Makefile; los comandos sin Docker están en la sección "Comandos de desarrollo".

6. **Prisma NO se usa**: aunque pueda aparecer en devDeps, no hay `schema.prisma` ni configuración. La autenticación es NextAuth con credentials provider que llama al backend.

7. **CORS**: `app/core/cors.py` solo agrega los orígenes de `localhost` (`localhost:3000`, `127.0.0.1:3000`, `frontend:3000`) cuando `ENV=development`; en producción valen únicamente `FRONTEND_URL` y `ALLOWED_ORIGINS`.

8. **No hay .env comprometido** — copiar `.env.example` a `.env` antes de iniciar.

---

## Flujo de negocio principal

```
Importar Excel → Unidades en AVAILABLE (en bodega)
                    ↓
            Transferir a sucursal → IN_TRANSIT
                    ↓
            Recibir en sucursal → AVAILABLE (en sucursal)
                    ↓
                 Vender → SOLD
```

Cada cambio de estado se refleja en `units.status` / `units.sold_date` y deja un registro en la tabla `transfers`; la trazabilidad completa se reconstruye a partir de ambos (no existe tabla `movements`).

---

## Módulo de importaciones (Excel del proveedor)

El módulo está **completo** (FR-00…FR-10). Seguimiento local: `frontend/IMPORTS_MODULE_TASKS.md`.

- **Campos canónicos**: `frame`, `motor`, `color`, `model`, `brand` — siempre `string` (preservar seriales largos, sin notación científica ni `.0`).
- **Sinónimos del parser**: `marca`/`brand`/`品牌` → `brand`; la columna `Marca` del Excel del proveedor mapea a `brand` y si viene vacía se guarda `"Sin especificar"`.
- **Metadata del upload**: `batch_period` (ej. `"2026-ABRIL"`) y `product_type` (opcionales). Formatos: `.xlsx`, `.xls`, `.csv`.
- **Preview no bloquea** el import: `invalid_rows` es esperado y el import es atómico con éxito parcial (errores por fila en `import_errors`).
- **Endpoints**: `POST /imports/preview`, `POST /imports/upload`, `GET /imports/`, `GET /imports/{id}`, `GET /imports/{id}/errors`, `DELETE /imports/{id}` (solo ADMIN); equivalencias en `/model-equivalences` (CRUD + `GET /unmapped`).
- **Frontend**: wizard en `/imports` (archivo+metadata → preview → mapeo asistido → importar) + historial en `/imports/history` + detalle en `/imports/[id]`.

---

## Workflow de trabajo

- **Una rama y un PR por tarea**, commits con mensajes descriptivos, tests antes de cada PR.
- `main` está protegida: requiere PR, que pasen **Backend Tests** (pytest) y **Frontend Tests** (vitest), rama actualizada y conversaciones resueltas. **No push directo ni force-push a `main`.**
- Frontend → Vercel (preview por PR, producción al mergear). Backend + DB → Render (push a `main`).
- Alembic está configurado pero **el deploy no lo ejecuta**: las tablas se crean con `create_all` en el lifespan (se revirtió `alembic upgrade head` del startCommand por una migración rota).
- **`create_all` no altera las tablas que ya existen**: solo crea las que faltan. Una columna nueva no llega a la base real (Neon) con el deploy, y la app no arranca contra ella (`column users.token_version does not exist`). **Toda columna nueva hay que aplicarla a la base antes de mergear**, con su migración real: `alembic upgrade head` apuntando a la base (la cadena de migraciones está rota antes de la 005, así que primero `alembic stamp` del revision anterior). Hay un script de ejemplo en `backend/tmp_apply_005_neon.py`.

---

## Convenciones de código

### Backend (Python)
- **Formatter**: Black (line-length 88)
- **Linter**: Ruff
- **Types**: mypy con strict mode
- **Target**: Python 3.11
- **Tests**: pytest con asyncio_mode=auto

### Frontend (TypeScript)
- **Framework**: Next.js 14 App Router
- **Styling**: TailwindCSS + shadcn/ui
- **Strict mode**: habilitado en tsconfig
- **Path imports**: `@/components/...`, `@/lib/...`, `@/types/...`

---

## Variables de entorno clave

```bash
# Backend
DATABASE_URL          # PostgreSQL connection string
SECRET_KEY            # JWT signing key (obligatoria: sin ella se genera una efímera)
ALGORITHM             # JWT algorithm (HS256)
ACCESS_TOKEN_EXPIRE_MINUTES  # Token TTL (default: 60)
REFRESH_TOKEN_EXPIRE_DAYS   # Vida del token de refresco (default: 7)
RATE_LIMIT_LOGIN_PER_MINUTE, RATE_LIMIT_FORGOT_PASSWORD_PER_MINUTE, RATE_LIMIT_REFRESH_PER_MINUTE  # Límites por IP y por cuenta (5 / 5 / 30)
BOOTSTRAP_ADMIN_PASSWORD      # Password inicial del admin bootstrap (opcional)

# Frontend
NEXT_PUBLIC_API_URL   # URL del backend (http://localhost:8000) — llamadas del navegador
BACKEND_URL           # URL del backend para el login server-side de NextAuth (distinta de la anterior)
NEXTAUTH_URL          # URL del frontend (http://localhost:3000)
NEXTAUTH_SECRET       # Secret para NextAuth

# SMTP (para emails)
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

# CORS
FRONTEND_URL, ALLOWED_ORIGINS
ENV                      # development = agrega los orígenes de localhost a la lista de CORS
```

> Las variables viven **centralizadas en el `.env` de la raíz** (docker-compose las inyecta a postgres/backend/frontend). `backend/.env` ya no existe.
