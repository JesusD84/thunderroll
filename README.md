
# Thunderrol - Sistema de Trazabilidad de Inventario

Sistema completo de trazabilidad de inventario para Thunderrol (empresa de scooters/motos en Guadalajara).

## 🚀 Características

- **Backend FastAPI** con PostgreSQL, SQLAlchemy, Alembic
- **Frontend Next.js** con TypeScript, TailwindCSS, shadcn/ui
- **Autenticación JWT** con RBAC (ADMIN, INVENTARIO, TALLER, VENTAS)
- **Trazabilidad completa** de unidades desde bodega hasta venta
- **Importación Excel** del proveedor con validaciones
- **Reportes** CSV/XLSX por fechas
- **Auditoría completa** de todas las operaciones
- **Docker Compose** para despliegue local

## 🏗️ Arquitectura

### Estados de la Máquina
```
EN_BODEGA_NO_IDENTIFICADA → IDENTIFICADA_EN_TALLER → EN_TRANSITO_TALLER_SUCURSAL → EN_SUCURSAL_DISPONIBLE → VENDIDA
```

### Ubicaciones
- **BODEGA**: Almacén principal
- **TALLER**: Centro de identificación y ensamble
- **SUCURSALES**: Centro, Norte, Sur

### Roles de Usuario
- **ADMIN**: Acceso total al sistema
- **INVENTARIO**: Importar, editar, transferir, vender
- **TALLER**: Identificar, transferir taller→sucursal
- **VENTAS**: Ver catálogo, vender, reportes

## 🚦 Inicio Rápido

### Prerrequisitos
- Docker y Docker Compose
- Node.js 18+ (para desarrollo local)
- Python 3.11+ (para desarrollo local)

### 1. Clonar y configurar
```bash
git clone <repo-url>
cd thunderrol
cp .env.example .env
```

### 2. Levantar con Docker
```bash
# Construcción y inicio completo
docker compose up --build

# En segundo plano
docker compose up -d
```

### 3. Acceder a la aplicación
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Adminer**: http://localhost:8080

### 4. Credenciales Demo
```
admin@thunderrol.com / admin123 (ADMIN)
inventario@thunderrol.com / inv123 (INVENTARIO)
taller@thunderrol.com / taller123 (TALLER)
ventas@thunderrol.com / ventas123 (VENTAS)
```

## 🛠️ Desarrollo Local

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Migrar base de datos
alembic upgrade head

# Ejecutar seeds
python -m app.database.seed

# Ejecutar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Base de Datos
```bash
# Nueva migración
cd backend
alembic revision --autogenerate -m "descripción"

# Aplicar migraciones
alembic upgrade head

# Revertir migración
alembic downgrade -1
```

## 🧪 Testing

### Backend (pytest)
```bash
cd backend
make test
# o
pytest tests/ -v
```

### Frontend (Playwright)
```bash
cd frontend
npm run test:e2e
```

### Linting y Formateo
```bash
# Backend
make fmt    # Black formatting
make lint   # Ruff linting
make type   # mypy type checking

# Frontend
npm run lint
npm run type-check
```

## 📊 API Endpoints

### Autenticación
- `POST /auth/login` - Login JWT
- `GET /auth/me` - Perfil usuario

### Unidades
- `GET /units` - Listar con filtros
- `POST /units` - Crear manual
- `GET /units/{id}` - Detalle + timeline
- `PATCH /units/{id}` - Actualizar

### Importación
- `POST /imports/excel` - Subir Excel
- `GET /imports/{id}/errors` - Ver errores

### Identificación
- `POST /units/match-identification` - Match motor/chasis

### Transferencias
- `POST /transfers` - Crear transferencia
- `POST /transfers/{id}/receive` - Recibir

### Ventas
- `POST /units/{id}/sell` - Marcar vendida

### Reportes
- `GET /reports/movements` - Exportar movimientos

### Catálogos
- `GET /locations` - Ubicaciones
- `GET /users` - Usuarios (limitado por rol)

## 📁 Estructura del Proyecto

```
thunderrol/
├── backend/
│   ├── app/
│   │   ├── api/          # API routers
│   │   ├── core/         # Config, security, deps
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── db/           # Database session, seeds
│   │   └── main.py       # FastAPI app
│   ├── migrations/       # Alembic migrations
│   ├── tests/           # pytest tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── app/             # Next.js app router
│   ├── components/      # React components
│   ├── lib/            # Utilities, API client
│   ├── package.json
│   ├── Dockerfile
│   └── next.config.js
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 Configuración de Entorno

Ver `.env.example` para todas las variables disponibles.

### Variables Principales
```bash
# Database
DATABASE_URL=postgresql://thunderrol:password@db:5432/thunderrol

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
ENVIRONMENT=development
DEBUG=true
```

## 📈 Flujo de Uso

1. **Importar Excel** del proveedor → unidades en `EN_BODEGA_NO_IDENTIFICADA`
2. **Identificar en taller** → `IDENTIFICADA_EN_TALLER`
3. **Transferir a sucursal** → `EN_TRANSITO_TALLER_SUCURSAL`
4. **Recibir en sucursal** → `EN_SUCURSAL_DISPONIBLE`
5. **Vender** → `VENDIDA`

## 🔒 Seguridad

- Autenticación JWT con refresh tokens
- RBAC por endpoints
- Passwords hasheados con bcrypt
- CORS configurado
- Validación de datos con Pydantic
- Auditoría completa de operaciones

## 📝 Logs y Monitoreo

- Logs estructurados con loguru
- Request ID para trazabilidad
- Auditoría en `unit_events`
- Métricas básicas en dashboard

## 🐛 Troubleshooting

### Base de datos no conecta
```bash
docker compose logs db
```

### Error de permisos
```bash
sudo chown -R $USER:$USER .
```

### Limpiar Docker
```bash
docker compose down -v
docker system prune -f
```

## 🤝 Contribución

1. Fork del proyecto
2. Crear rama feature
3. Commit cambios
4. Push a la rama
5. Crear Pull Request

## 📄 Licencia

MIT License - ver archivo LICENSE
