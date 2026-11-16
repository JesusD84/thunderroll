# Ramp-up Técnico — Thunderoll

> Documento de onboarding para un **developer junior** que entra al proyecto y **no ha trabajado antes**
> con estas tecnologías. Asumo que sabes programar, pero que Python/FastAPI, SQLAlchemy, Next.js, TypeScript,
> Docker, JWT y testing de frontend son terreno nuevo.
>
> Si lo que quieres es entender el negocio, ver [`RAMPEO_PRODUCTO.md`](./RAMPEO_PRODUCTO.md).

---

## 0. La idea en 60 segundos

```
┌─────────────────────────┐         ┌─────────────────────────┐         ┌──────────────┐
│  Navegador del usuario  │  HTTP   │   Next.js (frontend)    │  HTTP   │  FastAPI     │
│                         │ ──────▶ │   Vercel                │ ──────▶ │  Render      │
│  (Tailwind + shadcn/ui) │         │   :3000                 │         │  :8000       │
└─────────────────────────┘         └─────────────────────────┘         └──────┬───────┘
             ▲                                ▲                                │
             │                                │                                │ SQL (psycopg2)
             │  pages are server-rendered,   │  "use client" = runs in      │
             └─ but data is fetched in      │  the browser                 ▼
                the browser after login     │                        ┌──────────────┐
                                            │                        │  PostgreSQL  │
                                            └────────────────────────│  15 / Neon  │
                                             login happens server-  └──────────────┘
                                             side via NextAuth
```

Tres piezas, dos deploys, una base de datos. El frontend es una app de Next.js con App Router (renderizado
en servidor + hydrate en el cliente); el backend es una API REST de FastAPI; PostgreSQL guarda todo.

**En local** la base corre en el contenedor `postgres` de Docker Compose. **En producción** la base vive en
**Neon** y Render solo hospeda la API (§2.13).

**Regla mental:** el frontend nunca habla con la base de datos, y el backend nunca renderiza HTML. Se
comunican solo por HTTP con JSON.

---

## 1. Día 1 — levantarlo todo

### Opción A: Docker (la que usa el equipo)

```bash
cp .env.example .env      # las variables viven en la raíz, no en backend/ ni frontend/
docker compose up --build
```

- Frontend → http://localhost:3000
- API + Swagger → http://localhost:8000/docs ← **esta es tu mejor amiga las primeras semanas**
- Login → `admin@thunderoll.com` / `admin123`

Docker Compose levanta **tres** servicios: `postgres` (con healthcheck), `backend` y `frontend`. El
backend espera a que Postgres esté sano antes de arrancar. Los volúmenes `postgres_data` y
`backend_imports` persisten entre reinicios.

### Opción B: local (para iterar rápido en el backend)

```bash
# Postgres en Docker, el resto local
docker compose up -d postgres

cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx pytest-mock   # ← NO vienen en requirements.txt
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

> **Ojo con los tests**: `backend/requirements.txt` **no incluye `pytest` ni `httpx`**, y `conftest.py` importa
> `httpx`. Si te saltas esa segunda línea, `pytest tests/` falla con *command not found*. El CI los instala
> por separado (ver `.github/workflows/backend-ci.yml`). Alternativa: `pip install -e ".[dev]"` (el extra
> `[dev]` de `backend/pyproject.toml`).

> `--legacy-peer-deps`: con npm ≥ 10 y el lockfile versionado, `npm install` resuelve solo. Si ves
> `ERESOLVE`, usa `npm install --legacy-peer-deps`. El CI lo usa por compatibilidad con versiones antiguas.

> **Ojo con `DATABASE_URL`**: `backend/app/database/database.py` hace `load_dotenv()` y sube el `.env` de la
> raíz. Ese archivo puede apuntar a un host que solo existe *dentro* de la red de Docker (p. ej. `db:5432`).
> Para correr el backend **fuera** de Docker necesitas que apunte a `localhost:5432`; dentro de Docker no
> importa, porque `docker-compose.yml` sobrescribe la variable para el servicio `backend`.

### El `.env` de la raíz
Un solo archivo con todo. Docker Compose lo inyecta en los tres servicios. Dos variables que se confunden
constantemente:

| Variable | Quién la usa | Para qué |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | El **navegador** | URL del backend para las llamadas del cliente |
| `BACKEND_URL` | El **servidor** Next.js | URL del backend para el login de NextAuth |

**Checklist del `.env`** — `docker-compose.yml` interpola estas variables. Si alguna falta, Compose pasa una
**cadena vacía** (no un valor por defecto). Ojo: el efecto **depende de la variable** y no siempre es un crash
visible:

| Variable vacía | Qué pasa |
|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 💥 `ValueError: invalid literal for int()` **al importar** `auth_service` → el backend no arranca |
| `ALGORITHM` | 💥 `JWSError: Algorithm not supported` **al hacer login** (no al arrancar) |
| `SECRET_KEY` | 😬 **No falla**: firma tokens con una clave vacía. Fallo de seguridad silencioso |
| `BACKEND_URL` | 😬 Cae al fallback `http://localhost:8000`, que dentro del contenedor no es el backend → el login falla |

Verifícalo antes de subir nada:

```bash
docker compose config | grep -E "SECRET_KEY|ALGORITHM|ACCESS_TOKEN|BACKEND_URL"
```

Las que **deben** estar (ver `docker-compose.yml` y `.env.example`):

| Variable | Valor en local |
|---|---|
| `SECRET_KEY` | algo random (`openssl rand -base64 32`) |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `FRONTEND_URL` | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |
| `BACKEND_URL` | `http://backend:8000` ← **nombre del servicio**, no localhost |
| `NEXTAUTH_URL` | `http://localhost:3000` |
| `NEXTAUTH_SECRET` | lo que sea, pero no vacío |
| `SMTP_*` | placeholders si no vas a enviar correos |

> Cuidado: el `.env` local puede tener variables con nombre **legacy** (`JWT_SECRET_KEY`,
> `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`) que el código **no lee**. Las que importan son las de la tabla.

### Qué pasa cuando arranca el backend
En `backend/app/main.py`, el `lifespan` corre al arrancar:
1. `Base.metadata.create_all(engine)` → crea las tablas que falten
2. `create_demo_data()` → si la tabla `users` está vacía, crea **solo** la cuenta admin bootstrap

Nada más. No hay ubicaciones, unidades ni usuarios de ejemplo: el cliente arma su propio inventario real.

---

## 2. Las tecnologías, explicadas por su rol **en este proyecto**

### 2.1 Python + FastAPI (backend)

**FastAPI** = framework web para APIs. Recibe HTTP, devuelve JSON.

```python
@router.get("/{unit_id}", response_model=Unit)
def get_unit(unit_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    return UnitService.get_unit_by_id(db, unit_id)
```

Lo que tienes que entender de esa firma:

| Parte | Significado |
|---|---|
| `@router.get(...)` | "Este método maneja GET en esa ruta". El prefijo (`/api/v1/units`) lo pone `api/v1/router.py` |
| `unit_id: int` | Es un **path parameter**: se toma de la URL (`/api/v1/units/42`). Si no es int → 422 automático. Los **query params** (`skip`, `limit`, `search`, `status`) van aparte, en el `?` |
| `Depends(get_db)` | **Inyección de dependencias**: FastAPI llama a `get_db()`, te pasa la sesión y la cierra al terminar |
| `response_model=Unit` | Valida y filtra la respuesta según el schema de Pydantic. También genera el OpenAPI |
| `HTTPException(404, "Unit not found")` | El error de negocio del backend |

**Dependency Injection** es el patrón central del proyecto. `get_db`, `get_current_user` y `require_role(...)`
son dependencias. Combinarlas es lo que te da auth + permisos sin repetir código:

```python
current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
```

### 2.2 SQLAlchemy — y el detalle que sorprende

SQLAlchemy mapea clases Python a tablas. El modelo:

```python
class Unit(Base):
    __tablename__ = "units"
    id = Column(Integer, primary_key=True, index=True)
    engine_number = Column(String(100), unique=True, nullable=True)
    ...
    current_location = relationship("Location", foreign_keys=[current_location_id])
```

Y el uso:

```python
unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
```

> ### ⚠️ La base de datos es **SÍNCRONA**
> El backend usa `psycopg2-binary` y sesiones **sync**. `db.query(...)` es una llamada bloqueante normal de
> Python. **No hay `await`, no hay `AsyncSession`, no hay `async def` con DB.** Hay `async def` en algunos
> endpoints (p. ej. upload de archivo, que hace `await file.read()`), pero **toda la capa de datos es sync**.
>
> Si escribes `await db.query(...)` vas a romper cosas. Y si usas `asyncio` para "mejorar" la DB, rompes
> el modelo de tests (que también es sync).

### 2.3 Pydantic v2 — los schemas

Pydantic valida y convierte datos. En FastAPI hay **dos capas**:

- **Request**: lo que el cliente manda, se valida contra un schema
- **Response**: lo que vuelve, se serializa contra `response_model`

```python
class UnitCreate(BaseModel):
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    model: str
    ...

# En el service:
update_data = unit_update.model_dump(exclude_unset=True)
```

`model_dump(exclude_unset=True)` → solo los campos que el cliente **realmente envió**. Es clave para no
sobrescribir con `None`.

> ### ⚠️ Los schemas están duplicados
> Existen en `app/models/schemas.py` (monolítico) **y** en `app/schemas/` (por dominio: `unit.py`,
> `transfer.py`, `auth.py`…). Los endpoints usan **ambos**. Antes de crear un schema nuevo, mira cuál
> está usando ese endpoint; si no lo sabes, `grep` el nombre del schema en el endpoint.

### 2.4 JWT y passwords

- **Login**: `POST /api/v1/auth/login` espera **form-urlencoded** (`username`, `password`), no JSON. Usa
  `OAuth2PasswordRequestForm` de FastAPI.
- El servidor verifica el password con **bcrypt** (`passlib` + `Security.get_password_hash`) y devuelve un
  **JWT** firmado con `SECRET_KEY` (HS256). El JWT lleva `sub` = **id del usuario** (no el username), `typ`
  = `access`, `ver` = `users.token_version` y `exp`.
- Cada request autenticado manda `Authorization: Bearer <token>`.
- `get_current_user` valida el tipo del token, busca al usuario **por id** y compara la versión → 401 si el
  token está revocado. `require_role([...])` además verifica el rol → 403 si no aplica.

**El token expira** (TTL en `ACCESS_TOKEN_EXPIRE_MINUTES`: 60 min). Cuando expira, el backend responde 401 y
el frontend intenta **renovar el token** con el `refresh_token` (7 días) antes de cerrar sesión (ver §3.4).

### 2.5 pandas + openpyxl/xlrd — el parser de Excel

`backend/app/services/import_parser.py` es la pieza más técnica del repo. Usa **pandas** para leer el
archivo como DataFrame y lo normaliza.

```python
# Fragmento de _read_raw_sheets() en backend/app/services/import_parser.py
raw = pd.read_excel(excel_source, engine=excel_engine_for(filename), sheet_name=None, header=None, dtype=object)
```

Claves para entenderlo:

- `header=None` → pandas **no** asume que la fila 1 es la cabecera. Se lee todo como datos y luego el
  parser busca la fila de cabecera real (`detect_header_row`: escanea las primeras 10 filas buscando ≥2
  palabras clave).
- `sheet_name=None` → devuelve **todas** las hojas como un dict. Las hojas sin datos se saltan.
- `dtype=object` → evita que pandas infiera tipos y destruya seriales largos.
- `engine=...` → `.xls` necesita `xlrd`, `.xlsx` necesita `openpyxl`. Se elige explícitamente.
- **Los CSV no pasan por aquí**: tienen su propia rama con `pd.read_csv(..., header=None, dtype=object)` y
  se exponen como un pseudo-sheet llamado `"csv"`.
- `normalize_id_value()` → convierte el número de serie a **string exacto**: un entero de 15 dígitos
  sigue siendo un string de 15 dígitos, nunca `3.52e+14` ni `352...0.0`.
- `FORWARD_FILL_FIELDS = ("model",)` → rellena hacia abajo celdas de **modelo** en bloques con celdas
  fusionadas. **Nunca** se hace con `frame`/`motor`: un frame vacío significa "no hay", no "repite el de arriba".

> ### ⚠️ El parser habla un idioma distinto al modelo de datos
> El parser trabaja con **campos canónicos** (`frame`, `motor`, `color`, `model`, `brand`), pero la tabla
> `units` usa otros nombres. La traducción ocurre al persistir:
>
> | Campo canónico (parser) | Columna en `units` |
> |---|---|
> | `frame` | `chassis_number` |
> | `motor` | `engine_number` |
> | `color` | `color` |
> | `model` | `model` |
> | `brand` | `brand` |
>
> Si buscas `frame` en la base de datos no lo vas a encontrar. Y `engine_number` / `chassis_number` son
> **nullable** (una unidad puede llegar solo con motor, o solo con chasis).

El parser no sabe nada de la base de datos: es puro. Por eso se testea sin levantar FastAPI.

### 2.6 Next.js 14 App Router

Next.js = framework de React con renderizado en servidor. La versión "App Router" organiza el proyecto por
**carpetas que son rutas**:

```
frontend/app/
├── page.tsx                 → ruta "/"        (dashboard)
├── units/page.tsx           → ruta "/units"
├── units/[id]/page.tsx      → ruta "/units/42"  ← [id] es un parámetro dinámico
├── imports/page.tsx         → ruta "/imports"
├── api/auth/[...nextauth]/route.ts  → endpoint HTTP del propio frontend
└── layout.tsx               → wrapper de TODAS las páginas (navbar, providers)
```

**Server vs Client Component** — el concepto que más cuesta al principio:

| | Server Component (default) | Client Component |
|---|---|---|
| Cómo se marca | nada | `'use client'` **arriba del archivo** |
| Dónde corre | en el servidor | en el navegador |
| Puede usar `useState`/`useEffect` | ❌ | ✅ |
| Puede leer `process.env` secreto | ✅ | ❌ |
| Puede ver `session.accessToken` | ❌ (no hay sesión en el server de la app) | ✅ |

En este proyecto **casi todas las páginas son client components** porque los datos se piden al backend
*desde el navegador* con el token del usuario. La excepción notable: `app/api/auth/[...nextauth]/route.ts`
es server, porque el login contra el backend debe usar `BACKEND_URL` (no expuesto al navegador).

### 2.7 TypeScript

Es JavaScript con tipos. La diferencia práctica en este repo:

```typescript
// En frontend/lib/imports.ts
export interface ImportPreviewResponse {
  filename: string;
  sheets: SheetPreview[];
  detected_fields: CanonicalField[];
  preview_data: PreviewRow[];
  invalid_rows: InvalidRow[];
  invalid_rows_count: number;
  issues: Issue[];
  validation: Validation;
}
```

El tipado te salva justo en el punto más frágil del proyecto: **el contrato entre frontend y backend**.
Si cambias un campo en el schema de Pydantic, TypeScript te avisa de qué pantallas se rompieron.

> Ojo: `frontend/lib/types.ts` **no** contiene los tipos del contrato de imports — es código muerto que
> quedó del template de shadcn (`Expense`, `EXPENSE_CATEGORIES`…) y no lo importa nadie. Los tipos del
> contrato de importaciones viven en **`frontend/lib/imports.ts`**.

`tsconfig.json` tiene `strict: true`. Cuidado: `noImplicitAny` hace que un `catch (err)` mal tipado sea
error. Usan `(session as any).accessToken` en varios sitios por legibilidad.

> ### ⚠️ Gotcha: la API normaliza a MAYÚSCULAS
> Los schemas de `app/schemas/unit.py` tienen validadores que convierten a mayúsculas `model`, `brand`,
> `color` y los identificadores. Eso pasa en **dos** momentos:
>
> - **Al crear** por API (`POST /units`): se guarda en mayúsculas.
> - **Al leer** (`GET /units`): el schema de respuesta vuelve a aplicar el validador, así que **la API
>   siempre muestra mayúsculas**, aunque en la base esté en minúsculas.
>
> **El import es la excepción**: escribe directo al modelo (`models.Unit(...)`) sin pasar por el schema, así
> que guarda el texto tal cual viene del archivo. Consecuencia práctica: la BD puede tener `x3 pro`
> mientras la API devuelve `X3 PRO`. Y como la detección de duplicados compara con `IN (...)` (sensible a
> mayúsculas), importar `abc123` cuando ya existe `ABC123` **no lo detecta como duplicado**.

### 2.8 TailwindCSS + shadcn/ui

- **Tailwind** = CSS con clases utilitarias: `className="flex items-center gap-2 px-4 py-2"`. No hay
  archivos `.css` por componente.
- **shadcn/ui** = componentes accesibles (Radix UI) + estilos Tailwind, **copiados a tu repo** en
  `components/ui/`. No es una librería que importas: son archivos tuyos que puedes editar.

```bash
# Si necesitas un componente nuevo, cópialo de shadcn/ui y adapta los estilos al tema del proyecto.
npx shadcn@latest add <componente>
```

Los iconos son **lucide-react**: `<Truck className="h-4 w-4" />`.

### 2.9 NextAuth v4

Maneja la sesión del usuario **en el frontend**, pero **NO** valida passwords: delega eso al backend.

El archivo clave es `frontend/app/api/auth/[...nextauth]/route.ts`:

```typescript
const loginRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: params.toString(),
});
const { access_token, refresh_token, expires_in } = await loginRes.json();
// ...y un GET a /api/v1/user/me para traer id, email, nombre y role
```

Luego guarda `role`, `accessToken`, `refreshToken` y `accessTokenExpiresAt` **dentro del JWT de NextAuth**
(callbacks `jwt` y `session`), con `strategy: 'jwt'` (sin base de datos de sesiones).

En el cliente:

```typescript
const { data: session } = useSession();
const token = (session as { accessToken?: string } | null)?.accessToken;
```

El tipo de sesión está extendido en `frontend/types/next-auth.d.ts` para que `role`, `accessToken` y
`accessTokenExpiresAt` estén tipados.

### 2.10 Por qué `fetch` + `useState` y no React Query

Están instalados Zustand, Jotai, SWR y TanStack Query, pero **el patrón del repo es `fetch` + `useState`**:

```typescript
const [data, setData] = useState<T | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);

useEffect(() => { /* fetch + setData/setError/setLoading */ }, []);
```

**No introduzcas otra librería de state.** Sigue el patrón aunque te parezca old-school: es lo que el resto
del código entiende.

### 2.11 Docker Compose

`docker-compose.yml` define servicios con `environment`, `volumes`, `depends_on` y `ports`. El
`docker-compose.override.yml` (sin `version:`) pisa el `frontend` para desarrollo: monta el código en
vivo (hot reload) con `npm run dev` en vez del build de producción.

### 2.12 Testing

**Backend (pytest)**: `backend/tests/conftest.py` monta todo.

- Base **SQLite en memoria** (`sqlite:///:memory:`) con `StaticPool` → una sola conexión compartida
- `app.dependency_overrides[get_db] = override_get_db` → **esto** es lo que hace que los tests usen la DB
  de test en vez de la real. Es la pieza clave.
- `AsyncClient(transport=ASGITransport(app=app))` → pruebas de endpoints sin levantar un servidor
- Fixtures: `test_users`, `test_locations`, `auth_headers` (ya con el token), `sold_unit_with_history`

```bash
cd backend && pytest tests/ -v          # 23 archivos de test (344 tests)
```

> Recuerda: `pytest` y `httpx` **no** vienen en `requirements.txt`. Instálalos aparte (ver §1) o usa
> `pip install -e ".[dev]"`.

**Frontend (Vitest + Testing Library)**: `frontend/tests/`, con `jsdom` como entorno y `tests/setup.ts`
como setup. Mockeas `fetch` o usas `msw`.

```bash
cd frontend && npm test                 # vitest run
```

**E2E (Playwright)**: `frontend/e2e/` — `auth.spec.ts`, `imports.spec.ts`, `responsive.spec.ts`,
`smoke.spec.ts`. El de imports **alimenta los 4 Excel reales** (en `backend/tests/fixtures/samples/`) al
input de archivo y mockea `/preview` y `/upload` con `page.route`.

> Los 4 samples reales son la oro del repo. Son archivos del proveedor que rompen de todas las formas
> posibles (chino, sin cabecera, `.xls` legacy, celdas fusionadas). Cuando toques el parser, **córrelos**.

### 2.13 CI/CD

| Pieza | Qué hace |
|---|---|
| `.github/workflows/backend-ci.yml` | En cada PR a `main`: Python 3.11, `pytest tests/ -v` |
| `.github/workflows/frontend-ci.yml` | En cada PR a `main`: Node 22, `npm test` |
| Vercel | Preview por PR, producción al mergear a `main` → `thunderoll.vercel.app` |
| Render (`render.yaml`) | **Solo el backend** (web service `thunderroll-backend`, plan free) |
| Neon | **La base de datos**: PostgreSQL serverless. Ya **no** está en Render — la DB free de Render se suspendía y luego se borraba |

> Ojo con esto: `README.md` y `claude.md` todavía dicen "Render (backend + PostgreSQL)". La realidad es que
> Render hospeda **solo la API** y la base vive en **Neon** (ver `CI_CD_PLAN.md` → "Migración de DB a Neon").
> El `DATABASE_URL` de producción se setea en el dashboard de Render, no en el repo.

`main` está protegida: sin PR y sin los dos checks en verde, no hay merge.

---

## 3. Los patrones del repo (esto es lo que te va a morder si no los sabes)

### 3.1 Repository → Service → Router

```
endpoints/units.py        ← HTTP: parsea params, llama al service, devuelve
   ↓
services/unit_service.py  ← reglas de negocio, orquestación
   ↓
repositories/unit_repository.py  ← queries a la DB, una por operación
```

El service es donde vive la lógica; el repository solo habla SQL; el endpoint solo habla HTTP.

### 3.2 Los permisos están duplicados a propósito

| Backend | Frontend |
|---|---|
| `require_role([UserRole.ADMIN, UserRole.MANAGER])` | `getPermissions(role).manageEquivalences` |

`frontend/lib/auth.ts` es el **espejo** del backend. Si agregas un permiso, lo agregas en los dos lados.
El backend manda (es la autoridad), la UI solo esconde botones.

### 3.3 El cliente HTTP: `lib/api.ts`

Hay **dos estilos** en el repo y ambos son válidos:

**Estilo A — `apiFetch`** (el que usa `lib/imports.ts`): el **path es relativo** (`/api/v1/imports`) y es
`apiFetch` quien le antepone `API_URL`; el token se inyecta solo y los errores se normalizan en `ApiError`.

```typescript
const res = await apiFetch<ImportPreviewResponse>(`${IMPORTS_BASE}/preview`, {
  token,
  body: formData,          // multipart: el body va crudo, sin Content-Type manual
});
```

**Estilo B — `sessionAwareFetch` directo** (el que usan páginas como `app/units/page.tsx`): tú armas la
URL con `URLSearchParams` y el header Bearer.

```typescript
const params = new URLSearchParams({ skip: String((page - 1) * PAGE_SIZE), limit: String(PAGE_SIZE) });
if (searchTerm) params.set('search', searchTerm);

const res = await sessionAwareFetch(`${API_URL}/api/v1/units/?${params.toString()}`, {
  headers: { 'Authorization': `Bearer ${token}` },
});
if (!res.ok) throw new Error('No se pudieron cargar las unidades');

const data = await res.json();
setUnits(data);
setTotalCount(Number(res.headers.get('X-Total-Count') ?? data.length));  // ← el total vive en un header
```

Detalle del segundo estilo: el **total de unidades no viene en el body**, viene en el header
`X-Total-Count` (el backend lo pone con `response.headers[...]`, y CORS lo expone con
`expose_headers=["X-Total-Count"]`).

`apiFetch` normaliza los errores: si la respuesta no es `ok`, lanza `ApiError` con el `detail` que mandó
FastAPI. Los catch de las páginas hacen:

```typescript
catch (err) {
  const message = err instanceof ApiError ? err.message : 'Error genérico';
}
```

### 3.4 El manejo del 401 — el patrón más particular del repo

Cuando el JWT expira, el backend responde 401. Antes del PR #73 el frontend se quedaba en un bucle de
errores (la sesión de NextAuth seguía marcada como activa). La solución (`lib/session-expiry.ts` +
`lib/api.ts`):

```typescript
export async function sessionAwareFetch(input, init, { skipSessionExpiry = false } = {}) {
  const response = await fetch(input, init);
  if (response.status === 401 && !skipSessionExpiry) {
    const freshToken = await refreshAccessToken();   // renueva el token de acceso
    if (freshToken && freshToken !== usedToken) {
      const retried = await fetch(input, withBearerToken(init, freshToken));
      if (retried.status !== 401) return retried;     // ← un reintento, y sale
    }
    void handleSessionExpired();          // cierra sesión + redirige a /login
    return new Promise<Response>(() => {}); // ← promesa que NUNCA resuelve
  }
  return response;
}
```

Tres detalles que parecen rarezas pero son intencionales:

1. **La promesa que nunca resuelve**: hace que los `finally` de los callers no corran y que la página no
   renderice el error mientras navega away. El comentario en el código lo dice.
2. **`handleSessionExpired()` es single-flight**: N requests 401 simultáneos → un solo `signOut()` y una
   sola navegación.
3. **El reintento antes de cerrar sesión**: el access token dura 60 min, mucho menos que la sesión de
   NextAuth. Sin este paso, todo usuario sería expulsado cada hora. El refresco tiene dos capas:
   - **Proactiva (server-side)**: el callback `jwt` de NextAuth corre en cada lectura de
     `/api/auth/session`; si el token expira en menos de 60 s, pide uno nuevo a `POST /api/v1/auth/refresh`
     (`lib/backend-auth.ts`) y actualiza la cookie de sesión (que va cifrada).
   - **Reactiva (client-side)**: ante un 401, `lib/api.ts` llama a `refreshAccessToken()`
     (`lib/session-refresh.ts`, single-flight) → `getSession()` → reintenta **una vez** con el token nuevo.

   Si el `refresh_token` ya no vale (cambió la contraseña, el rol o se dio de baja la cuenta), el backend
   responde 401 y cae al flujo de sesión expirada de siempre.

`safeCallbackUrl()` bloquea redirects externos (`//evil.com`, `/login`) → solo acepta rutas relativas
internas.

> **Regla**: toda request autenticada va por `apiFetch` / `sessionAwareFetch`. No llames `fetch()` pelado en
> una página. Hoy **ninguna** lo hace: los únicos dos `fetch()` del frontend son el wrapper de `lib/api.ts`
> y el route handler de NextAuth (que es server-side y por diseño no lleva el token del usuario).

### 3.5 Estados de UI consistentes

`components/ui/states.tsx` define `LoadingState` (con `role="status"`), `EmptyState` y `ErrorState`
(con `role="alert"`). Úsalos en lugar de inventar spinners nuevos. Y `sonner` para los toasts.

---

## 4. Anatomía de una request — para perderle el miedo

### `GET /api/v1/units?search=abc&skip=0&limit=25`

```
Navegador
  │  sessionAwareFetch('/api/v1/units/?skip=0&limit=25', { headers: { Authorization: 'Bearer …' } })
  ▼
frontend/app/units/page.tsx
  │  arma el query con URLSearchParams y lee X-Total-Count
  ▼
backend/app/api/v1/endpoints/units.py::get_units
  │  Depends(get_db)            → sesión de DB
  │  Depends(get_current_active_user) → decodifica JWT, busca el usuario
  │  filters: UnitFilters = Depends()  → valida los query params
  │  response.headers['X-Total-Count'] = count_units(...)
  ▼
UnitService.get_units → UnitRepository.get_units → db.query(...)
  ▼
JSON + header X-Total-Count → frontend → setData(...) → tabla renderizada
```

### `POST /api/v1/imports/upload` (multipart)

```
Wizard /imports
  │  FormData: file + batch_period + column_mapping (JSON string)
  ▼
POST /api/v1/imports/upload
  ├─ valida extensión (.xlsx/.xls/.csv) → 400 si no es un tipo soportado
  ├─ guarda el archivo con nombre del servidor (uuid4 + extensión validada)
  │  en <backend>/var/imports (o IMPORT_STORAGE_DIR): ruta NO servida por la API
  ├─ límite de tamaño (MAX_UPLOAD_SIZE_MB, 10 MB por defecto) leído por bloques
  │  → 413 si el archivo lo rebasa
  ├─ crea el registro Import (status="processing") y lo commitea
  ├─ parse_workbook(path, filename)          ← services/import_parser.py
  │    ├─ CSV: utf-8-sig y, si falla, cp1252 (Excel en español)
  │    ├─ límite de filas por hoja (MAX_IMPORT_ROWS_PER_SHEET, 20000) → 422
  │    └─ límite de hojas (MAX_IMPORT_SHEETS, 50) → 422
  ├─ apply_manual_mapping(result, mapping)    ← override del mapeo manual
  ├─ crea "Almacén Principal" si no existe (commit aparte)
  ├─ pass 1: normaliza filas (sin escribir en DB)
  │           y descarta en silencio las que no tienen frame NI motor
  ├─ detecta duplicados (2 queries contra units: engine_number y chassis_number)
  ├─ pass 2: valida cada fila → units[] + error_records[]
  └─ UNA transacción para el lote: add_all(units) + flush + transfers + errors + commit
       → actualiza el registro Import (successful/failed) y lo commitea
       → devuelve { successful_imports, failed_imports, import_id }
```

> El endpoint es **síncrono** (`def`, no `async def`): pandas y SQLAlchemy sync son
> trabajo pesado y FastAPI corre los endpoints `def` en su threadpool, en vez de
> bloquear el event loop.
>
> Los errores del archivo son tipados y con mensaje para el usuario (400 tipo de
> archivo, 413 tamaño, 422 contenido). Cualquier fallo inesperado responde un 500
> genérico con un `request_id`; el texto crudo de la excepción nunca sale del
> servidor (queda en el log).

**Ojo con el alcance de "una sola transacción"**: es cierto para el **lote** (unidades + transferencias +
errores van juntos: o entra todo, o no entra nada). Pero el registro `Import` se commitea **por separado**
antes y después, y la ubicación por defecto también. Si el lote falla, el `Import` queda con
`status="failed"` y la nota del error — que es justamente lo que se quiere.

**Y ojo con las filas que no llegan a ser unidades**: una fila sin `frame` **ni** `motor` se descarta en
silencio (`continue`), *antes* de contarse en `total_records`. **No genera `import_errors`.** Solo los
duplicados sí. Consecuencia: el `total_records` del import puede ser menor que el número de filas que
viste en el preview, y las filas sin identificador no aparecen en el historial de errores.

---

## 5. Tour guiado del código (en este orden)

| # | Archivo | Qué aprendes |
|---|---|---|
| 1 | `backend/app/main.py` | App, CORS, lifespan, montaje de routers |
| 2 | `backend/app/api/v1/router.py` | El mapa de rutas completo (8 routers) |
| 3 | `backend/app/models/models.py` | Los 7 modelos y los 3 enums |
| 4 | `backend/app/services/auth_service.py` | JWT, bcrypt, `require_role` |
| 5 | `backend/app/api/v1/endpoints/units.py` + `services/unit_service.py` | Endpoint → service → repository |
| 6 | `backend/app/services/import_parser.py` | La pieza más técnica: lee con cuidado |
| 7 | `backend/app/api/v1/endpoints/imports.py` | El pipeline de importación completo |
| 8 | `frontend/app/layout.tsx` + `components/Navigation.tsx` | Shell del app y menú por rol |
| 9 | `frontend/app/api/auth/[...nextauth]/route.ts` | Cómo el login llega al backend |
| 10 | `frontend/lib/api.ts` + `lib/auth.ts` + `lib/session-expiry.ts` + `lib/session-refresh.ts` | Cliente HTTP, permisos, expiración, refresco de token |
| 11 | `frontend/app/imports/page.tsx` + `components/imports/` | El wizard, paso a paso |
| 12 | `backend/tests/conftest.py` | Cómo se testea sin DB real |

---

## 6. "Quiero hacer X, ¿dónde lo hago?"

| Quiero… | Backend | Frontend |
|---|---|---|
| Agregar un campo a una unidad | `models/models.py` + `schemas/unit.py` | `lib/imports.ts` (si es del contrato de imports) + la tabla de `app/units/` |
| Agregar un endpoint | `api/v1/endpoints/*.py` + router en `api/v1/router.py` | `lib/*.ts` (wrapper tipado) |
| Cambiar la lógica de una transferencia | `services/transfer_service.py` | `app/transfers/page.tsx` |
| Cambiar cómo se parsea el Excel | `services/import_parser.py` | `components/imports/PreviewResult.tsx` |
| Agregar un permiso/rol | `services/auth_service.py` (`require_role`) + `models/models.py` (enum) | `lib/auth.ts` (`getPermissions`) + `components/Navigation.tsx` |
| Cambiar un reporte | `services/report.py` | `app/reports/page.tsx` |
| Agregar una ubicación | `endpoints/locations.py` | `app/settings/page.tsx` |

---

## 7. Errores que vas a ver (y qué significan)

| Error | Causa típica | Fix |
|---|---|---|
| `ValueError: invalid literal for int() with base 10: ''` al arrancar el backend | Falta `ACCESS_TOKEN_EXPIRE_MINUTES` en el `.env` de la raíz. Compose pasa **cadena vacía** y `int("")` truena al importar `auth_service` | Agrega la variable al `.env` (ver §1) — `docker compose config` te dice cuáles faltan |
| Login falla dentro de Docker | `BACKEND_URL` vacío o mal puesto: el login server-side de NextAuth debe apuntar a `http://backend:8000` (nombre del servicio), no a `localhost` | `BACKEND_URL=http://backend:8000` en el `.env` de la raíz |
| `422 Unprocessable Entity` | El body/query no cumple el schema de Pydantic | Mira el `detail` en la respuesta: te dice campo y esperado |
| `401` | JWT expirado o inválido | El frontend debería cerrar sesión; si no, revisa `sessionAwareFetch` |
| `403` | Rol insuficiente | `require_role` — el usuario necesita otro rol, no un fix de código |
| `500` en login en producción | Síntoma típico: `BACKEND_URL` no configurada o mal puesta en Vercel | No es `NEXT_PUBLIC_API_URL` — son distintas. Revisa también que el backend de Render esté despierto (plan free duerme ~30-50 s) |
| `CORS error` | `FRONTEND_URL` no apunta al origen real | Incluir el dominio de preview de Vercel en `ALLOWED_ORIGINS` |
| `no such column: units.<campo>` | La DB de producción (Neon) no tiene la columna | El deploy **no corre Alembic**: hay que resolver la migración a mano |
| `ModuleNotFoundError: xlrd` | Falta dependencia para `.xls` | `xlrd` está en requirements; reinstala el venv |

---

## 8. Tu primer PR — el flujo exacto

```bash
git checkout -b feat/mi-cambio        # una rama por tarea
# ... código + tests ...
cd backend && pytest tests/ -v          # deben pasar
cd ../frontend && npm test              # deben pasar
git add -A && git commit -m "feat(x): descripción clara del cambio"
git push -u origin feat/mi-cambio
gh pr create --fill                    # abre el PR contra main
```

Después: CI corre los dos checks. Si están verdes y `main` está actualizada, hay merge. **Nunca push
directo a `main`** — está protegida.

**Antes de abrir el PR:**
- ¿Hay test para lo que cambié?
- ¿Los dos checks pasan?
- ¿El commit dice *qué* cambió y *por qué*?
- ¿Actualicé `frontend/IMPORTS_MODULE_TASKS.md` si toqué el módulo de imports?

---

## 9. Glosario técnico rápido

| Término | Qué es |
|---|---|
| **Endpoint** | Un método HTTP en una ruta (`GET /api/v1/units`) |
| **Router** | El archivo que agrupa endpoints (`api/v1/endpoints/units.py`) |
| **Dependency / `Depends()`** | Función que FastAPI ejecuta y cuyo resultado inyecta en el endpoint |
| **Schema (Pydantic)** | La forma y las reglas de los datos de entrada/salida |
| **Model (SQLAlchemy)** | La clase Python que mapea a una tabla |
| **Migration (Alembic)** | El script versionado que cambia el esquema. **No corre en deploy** |
| **Session** | La sesión de DB; una por request, se cierra sola |
| **Commit** | Confirma los cambios en la DB. `rollback` los deshace |
| **Client Component** | Componente React que corre en el navegador (`'use client'`) |
| **Server Component** | Componente que corre en el servidor (default en App Router) |
| **Hook** | Función que React usa para compartir estado/lógica (`useState`, `useEffect`, `useAuth`) |
| **JWT** | Token firmado con la info del usuario y una fecha de expiración |
| **CORS** | La política que decide qué orígenes del navegador pueden llamar a la API |
| **Fixture (pytest)** | Datos de prueba preparados y reutilizables |
| **Mock** | Sustituto de algo real en un test (ej. `fetch`) |
| **Static** | Generado en build time; **sin** datos del usuario (vs. dinámico) |
| **Server Action / Route Handler** | Endpoint HTTP dentro del propio frontend (`app/api/.../route.ts`) |

---

## 10. Recursos para seguir

- **Swagger** — http://localhost:8000/docs: la referencia viva de la API. Pruébalo antes de escribir código.
- **Next.js docs** — https://nextjs.org/docs (App Router: `/docs/app`)
- **FastAPI docs** — https://fastapi.tiangolo.com/tutorial/
- **SQLAlchemy 2.0** — https://docs.sqlalchemy.org/en/20/ (ojo: es la API 2.0, con `select()`, pero este
  repo usa el estilo `Query` clásico heredado — sigue el estilo del repo)
- **Tailwind** — https://tailwindcss.com/docs
- **shadcn/ui** — https://ui.shadcn.com/docs
- **NextAuth** — https://next-auth.js.org/getting-started/introduction
- **Vitest** — https://vitest.dev/guide/
- **Playwright** — https://playwright.dev/docs/intro

---

## 11. Mapa final del repo

```
thunderroll/
├── AGENTS.md                  ← contexto del proyecto (léelo primero)
├── claude.md                  ← referencia técnica extendida
├── docs/
│   ├── RAMPEO_PRODUCTO.md     ← este repo, lado negocio
│   └── RAMPEO_TECNICO.md      ← este repo, lado técnico
├── backend/
│   ├── app/
│   │   ├── main.py            ← app, CORS, lifespan
│   │   ├── api/v1/            ← router.py + endpoints/
│   │   ├── core/               ← security.py (bcrypt), cors.py, rate_limit.py, config.py
│   │   ├── database/          ← database.py (engine/session), seed.py
│   │   ├── models/            ← models.py (SQLAlchemy) + schemas.py
│   │   ├── schemas/           ← schemas por dominio
│   │   ├── repositories/      ← queries
│   │   └── services/          ← lógica de negocio (import_parser.py es el clave)
│   ├── migrations/            ← Alembic (NO corre en deploy)
│   └── tests/                 ← 23 test files + fixtures/samples/ (4 Excel reales)
├── frontend/
│   ├── app/                   ← rutas (App Router)
│   │   └── api/auth/          ← NextAuth route handler
│   ├── components/            ← Navigation.tsx, imports/, ui/ (shadcn)
│   ├── lib/                   ← api.ts, auth.ts, imports.ts, session-expiry.ts, session-refresh.ts, backend-auth.ts (+ types.ts: boilerplate sin uso)
│   ├── tests/                 ← Vitest
│   └── e2e/                   ← Playwright
├── docker-compose.yml
├── render.yaml                ← solo el backend (la DB vive en Neon)
└── .env.example
```
