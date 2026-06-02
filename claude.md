# CLAUDE.md — Thunderroll

## Qué es este proyecto

Sistema de trazabilidad de inventario para **Thunderrol**, empresa de scooters/motos en Guadalajara. Rastrea unidades desde importación hasta venta, pasando por bodega, taller, tránsito y sucursales.

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
│   │   │           ├── auth.py          # Login, JWT
│   │   │           ├── units.py         # CRUD de unidades
│   │   │           ├── locations.py     # Ubicaciones
│   │   │           ├── imports.py       # Importación Excel
│   │   │           ├── transfers.py     # Transferencias entre ubicaciones
│   │   │           ├── reports.py       # Reportes y exportaciones
│   │   │           └── user.py          # Gestión de usuarios
│   │   ├── core/
│   │   │   └── security.py             # CryptContext para bcrypt
│   │   ├── database/
│   │   │   ├── database.py             # Engine, SessionLocal, Base, get_db
│   │   │   └── seed.py                 # Demo data (corre en startup)
│   │   ├── models/
│   │   │   ├── models.py               # SQLAlchemy models (User, Location, Unit, Transfer, Import, ImportError)
│   │   │   └── schemas.py              # Pydantic schemas (Token, Unit, Transfer, etc.)
│   │   ├── repositories/               # Capa de acceso a datos
│   │   ├── schemas/                    # Schemas Pydantic adicionales por dominio
│   │   ├── services/                   # Lógica de negocio
│   │   │   ├── auth_service.py         # JWT, password hashing, RBAC
│   │   │   ├── unit_service.py
│   │   │   ├── transfer.py
│   │   │   ├── import_excel.py
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
│   │   ├── imports/page.tsx            # Importación Excel
│   │   ├── transfers/page.tsx          # Transferencias
│   │   ├── reports/page.tsx            # Reportes
│   │   ├── settings/page.tsx           # Configuración
│   │   ├── api/auth/                   # NextAuth route handler
│   │   ├── layout.tsx                  # Root layout (Inter font, SessionProvider, Navigation)
│   │   └── globals.css
│   ├── components/
│   │   ├── Navigation.tsx              # Navbar principal
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
- **UserRole**: `admin`, `manager`, `operator`, `viewer`
- **UnitStatus**: `WAREHOUSE_UNIDENTIFIED`, `AVAILABLE`, `SOLD`, `IN_TRANSIT`
- **TransferStatus**: `PENDING`, `IN_TRANSIT`, `RECEIVED`, `CANCELLED`

### Tablas principales
- **users** — email, username, first_name, last_name, role, hashed_password, is_active
- **locations** — name, address
- **units** — engine_number (unique, nullable), chassis_number (unique, nullable), model, brand, color, current_location_id, status, sold_date, notes
- **transfers** — unit_id, dispatched_by_id, received_by_id, origin_location_id, destination_location_id, status, dispatched_at, received_at (**una transferencia = una unidad**, no hay tabla pivote)
- **imports** — filename, original_filename, total_records, successful_imports, failed_imports, user_id, status, import_date, completed_at
- **import_errors** — import_id, row_number, error_message, raw_data

> No existe tabla `movements` ni enum `MovementType`. La trazabilidad se reconstruye a partir de los `transfers` y del `status`/`sold_date` de cada unidad.

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
- **Session type** extendida en `types/next-auth.d.ts` con `role` y `accessToken`
- **UI**: shadcn/ui components en `components/ui/`
- **Fetching**: Mezcla de SWR, TanStack Query y fetch directo (no hay un patrón único consolidado)

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

| Usuario | Password | Rol |
|---------|----------|-----|
| admin@thunderrol.com / admin | admin123 | ADMIN |
| manager@thunderrol.com / manager | manager123 | MANAGER |
| operator@thunderrol.com / operator | operator123 | OPERATOR |
| viewer@thunderrol.com / viewer | viewer123 | VIEWER |

---

## Cosas importantes a saber

1. **La DB es sync**: el app usa SQLAlchemy sync con `psycopg2-binary`. Los tests en `conftest.py` también usan SQLite en memoria **sync** (no async), coinciden con el app y **corren correctamente** (pasan en CI).

2. **Schemas duplicados**: Pydantic schemas existen en dos lugares: `app/models/schemas.py` (monolítico) y `app/schemas/` (separados por dominio). Al agregar/modificar schemas, verificar cuál se usa en el endpoint correspondiente.

3. **Múltiples libs de state management instaladas**: Zustand, Jotai, SWR y TanStack Query están todas en package.json. No hay un estándar consolidado — al hacer nuevas features, verificar qué se usa en páginas similares.

4. **Múltiples libs de forms**: react-hook-form + zod y formik + yup coexisten.

5. **Desarrollo local**: la forma recomendada es `docker compose up --build`. No hay Makefile; los comandos sin Docker están en la sección "Comandos de desarrollo".

6. **Prisma NO se usa**: aunque pueda aparecer en devDeps, no hay `schema.prisma` ni configuración. La autenticación es NextAuth con credentials provider que llama al backend.

7. **CORS**: `main.py` permite `localhost:3000`, `frontend:3000` y el valor de la variable `FRONTEND_URL` (para producción).

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

Cada cambio de estado genera un registro en la tabla `movements` para trazabilidad completa.

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
SECRET_KEY            # JWT signing key
ALGORITHM             # JWT algorithm (HS256)
ACCESS_TOKEN_EXPIRE_MINUTES  # Token TTL (default 30)

# Frontend
NEXT_PUBLIC_API_URL   # URL del backend (http://localhost:8000)
NEXTAUTH_URL          # URL del frontend (http://localhost:3000)
NEXTAUTH_SECRET       # Secret para NextAuth

# SMTP (para emails)
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
```
