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
│   │   │   ├── models.py               # SQLAlchemy models (User, Unit, Movement, etc.)
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
│   ├── migrations/                     # Alembic
│   ├── tests/                          # pytest (usa SQLite in-memory async)
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
├── docker-compose.yml
├── Makefile                            # Comandos principales (start, stop, test, migrate, etc.)
├── start.sh / status.sh / test.sh / reset_db.sh
└── .env.example
```

---

## Modelos de datos clave

### Enums
- **UserRole**: `admin`, `manager`, `operator`, `viewer`
- **UnitStatus**: `available`, `sold`, `in_transit`
- **MovementType**: `import`, `sale`, `transfer`, `return`, `damaged`, `maintenance`

### Tablas principales
- **users** — email, username, first_name, last_name, role, hashed_password, is_active
- **locations** — name, address
- **units** — engine_number (unique), chassis_number (unique), model, brand, color, current_location_id, status, sold_date
- **movements** — unit_id, user_id, movement_type, from/to_location_id, notes (auditoría)
- **imports** — filename, total_records, successful/failed_imports, status
- **import_errors** — import_id, row_number, error_message, raw_data
- **transfers** — from/to_location_id, user_id, status (pending/in_transit/completed/cancelled), total_units
- **transfer_units** — transfer_id, unit_id (tabla pivote)

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
make install-backend               # Crear venv + instalar deps
make dev-backend                   # uvicorn --reload en :8000
make migrate                       # alembic upgrade head
make create-migration DESC="msg"   # Nueva migración
make seed-db                       # Poblar datos demo

# Frontend (cwd: frontend/app)
make install-frontend              # yarn/npm install
make dev-frontend                  # next dev en :3000
```

### Testing
```bash
make test                          # Todos los tests
cd backend && pytest tests/ -v     # Solo backend
```

### Linting
```bash
make lint                          # Backend (ruff) + Frontend (eslint)
make format                        # Backend (black) + Frontend (eslint --fix)
```

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

1. **La DB es sync, no async**: Aunque los tests en `conftest.py` usan `aiosqlite` y `AsyncSession`, el app real usa SQLAlchemy sync con `psycopg2-binary`. Hay un mismatch entre test fixtures y el app — los tests probablemente no corren correctamente.

2. **Schemas duplicados**: Pydantic schemas existen en dos lugares: `app/models/schemas.py` (monolítico) y `app/schemas/` (separados por dominio). Al agregar/modificar schemas, verificar cuál se usa en el endpoint correspondiente.

3. **Múltiples libs de state management instaladas**: Zustand, Jotai, SWR y TanStack Query están todas en package.json. No hay un estándar consolidado — al hacer nuevas features, verificar qué se usa en páginas similares.

4. **Múltiples libs de forms**: react-hook-form + zod y formik + yup coexisten.

5. **El frontend cwd del Makefile apunta a `frontend/app`**, no a `frontend/`. Esto puede causar confusión con algunos comandos.

6. **`prisma` está en devDeps pero no hay schema.prisma visible**: El Makefile referencia `prisma generate` y `prisma db seed`, lo cual sugiere que se planeó usar Prisma en el frontend pero puede no estar configurado.

7. **CORS**: Hardcodeado en `main.py` para `localhost:3000` y `frontend:3000`.

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
