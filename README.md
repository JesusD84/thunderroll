# Thunderroll - Sistema de Trazabilidad de Inventario

Sistema de trazabilidad de inventario para Thunderroll (scooters/motos en Guadalajara). Permite seguir cada unidad desde su llegada a bodega hasta su venta, con importación masiva desde Excel, transferencias entre ubicaciones, reportes y control de acceso por roles.

## Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL. Autenticación JWT con RBAC. Email vía `fastapi-mail`.
- **Frontend**: Next.js 14 (App Router) + TypeScript + TailwindCSS + shadcn/ui. Autenticación con NextAuth (credentials provider contra el backend).
- **Infra**: Docker Compose para desarrollo local. Despliegue en Vercel (frontend) y Render (backend + PostgreSQL).

## Arquitectura

```
+------------------+        +------------------+        +------------------+
|  Next.js (front) | <----> |  FastAPI (back)  | <----> |   PostgreSQL     |
|  Vercel          |  HTTP  |  Render          |  SQL   |   Render         |
+------------------+        +------------------+        +------------------+
```

- El login corre **server-side** en NextAuth y llama al backend usando `BACKEND_URL`.
- Las llamadas del navegador (dashboard, listados) usan `NEXT_PUBLIC_API_URL`.
- Las tablas se crean automáticamente al arrancar el backend (`Base.metadata.create_all`) y se cargan datos demo vía el evento `lifespan`.

## Roles

| Rol | Descripción |
|---|---|
| `ADMIN` | Acceso total |
| `MANAGER` | Gestión de inventario, transferencias y reportes |
| `OPERATOR` | Operación de unidades y transferencias |
| `VIEWER` | Solo lectura |

## Inicio rápido (Docker Compose)

Requisitos: **Docker** y **Docker Compose**.

### 1. Crear el archivo `.env` en la raíz

`docker-compose.yml` lee estas variables para el backend:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@thunderroll.com
SMTP_PASSWORD=changeme
SMTP_FROM=noreply@thunderroll.com
FRONTEND_URL=http://localhost:3000
```

> Los valores SMTP pueden ser placeholders; el backend arranca igual, solo no enviará emails reales.

### 2. Levantar todo

```bash
docker compose up --build
```

### 3. Acceder

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

### 4. Credenciales demo

```
admin@thunderrol.com    / admin123     (ADMIN)
manager@thunderrol.com  / manager123   (MANAGER)
operator@thunderrol.com / operator123  (OPERATOR)
viewer@thunderrol.com   / viewer123    (VIEWER)
```

## Desarrollo local sin Docker

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Variables de entorno del backend (en `backend/.env` o exportadas):

```bash
DATABASE_URL=postgresql://thunderrol:thunderrol123@localhost:5432/thunderrol
SECRET_KEY=tu-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@thunderroll.com
SMTP_PASSWORD=changeme
SMTP_FROM=noreply@thunderroll.com
FRONTEND_URL=http://localhost:3000
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Variables de entorno del frontend (en `frontend/.env.local`):

```bash
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=genera-uno-con-openssl-rand-base64-32
NEXT_PUBLIC_API_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
```

## Testing

### Backend (pytest)

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

Los tests usan SQLite en memoria, así que no requieren PostgreSQL.

### Frontend (Vitest + Playwright)

```bash
cd frontend
npm test            # unit/integration (Vitest)
npm run test:e2e    # end-to-end (Playwright)
```

## CI/CD

### Integración continua (GitHub Actions)

En cada Pull Request hacia `main` corren dos checks:

- **Backend Tests** (`.github/workflows/backend-ci.yml`) — ejecuta `pytest`.
- **Frontend Tests** (`.github/workflows/frontend-ci.yml`) — ejecuta `vitest`.

`main` está protegida: se requiere PR y que ambos checks pasen antes de mergear.

### Despliegue continuo

- **Frontend (Vercel)**: deploy automático. Preview por cada PR, producción al mergear a `main` (`thunderroll.vercel.app`).
- **Backend + DB (Render)**: deploy automático al hacer push a `main`, definido en `render.yaml` (servicio web FastAPI + base de datos PostgreSQL).

Más detalle en `CI_CD_PLAN.md`.

## Estructura del proyecto

```
thunderroll/
├── backend/
│   ├── app/
│   │   ├── api/          # Routers y endpoints (v1)
│   │   ├── core/         # Seguridad y configuración
│   │   ├── database/     # Sesión, engine y seed de datos demo
│   │   ├── models/       # Modelos SQLAlchemy
│   │   ├── schemas/      # Schemas Pydantic
│   │   ├── services/     # Lógica de negocio
│   │   └── main.py       # App FastAPI (CORS, lifespan, routers)
│   ├── tests/            # pytest (SQLite en memoria)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/              # Rutas Next.js (App Router)
│   ├── components/       # Componentes React
│   ├── tests/            # Vitest
│   ├── e2e/              # Playwright
│   ├── package.json
│   ├── vercel.json
│   └── Dockerfile
├── docker-compose.yml
├── render.yaml           # Blueprint de Render (backend + DB)
├── CI_CD_PLAN.md
└── README.md
```

## Flujo de uso

1. **Importar Excel** del proveedor → unidades ingresan a bodega.
2. **Identificar** unidades (motor/chasis) en taller.
3. **Transferir** entre ubicaciones (bodega → taller → sucursal).
4. **Recibir** la transferencia en destino.
5. **Vender** la unidad → queda registrada con fecha de venta.

## Troubleshooting

- **El backend no conecta a la DB localmente**: verifica que PostgreSQL esté arriba y que `DATABASE_URL` apunte al host correcto. Con Docker Compose se gestiona solo.
- **Login da "Credenciales inválidas" en producción**: asegúrate de que `BACKEND_URL` (no solo `NEXT_PUBLIC_API_URL`) esté configurada en Vercel apuntando al backend de Render.
- **Errores de CORS desde el navegador**: el backend permite el origen de `FRONTEND_URL`; verifica que esa variable tenga el dominio correcto del frontend.
- **Backend lento en el primer request**: el plan free de Render duerme el servicio tras inactividad; el primer request puede tardar ~30-50s en despertar.
