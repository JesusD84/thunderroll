# CI/CD Plan — Thunderroll

## Arquitectura

```
GitHub (repo) ──PR──▶ GitHub Actions (tests) ──✅──▶ merge a main
                                                      │
                    ┌─────────────────────────────────┘
                    ▼                    ▼
              Vercel (frontend)    Render (backend + DB)
              vercel.app           onrender.com
```

---

## Fase 1: CI — GitHub Actions

En **todo** PR hacia `main` (y en push a `main`) se ejecutan ambos checks. No hay filtros de path: ambos corren siempre, para poder exigirlos en branch protection sin que queden colgados.

### Backend CI (job: `Backend Tests`)
- Python 3.11 + `pip install -r requirements.txt`
- `pytest` con SQLite en memoria (sin Postgres)
- Variables dummy (SECRET_KEY, SMTP_*, FRONTEND_URL) para que arranque el servicio de email
- Resultado visible en el PR: ✅ o ❌

### Frontend CI (job: `Frontend Tests`)
- Node 22 + `npm install --legacy-peer-deps`
- `npm test` (Vitest)
- Lint y build **no** corren en CI (incompatibilidades con ESLint v9 y `@vitejs/plugin-react`); el build real lo valida Vercel en cada deploy
- Resultado visible en el PR: ✅ o ❌

---

## Fase 2: CD — Deploy a QA

Al mergear a `main`, se despliega automáticamente:

| Componente | Plataforma | Plan | Detalle |
|---|---|---|---|
| Frontend (Next.js) | **Vercel** | Free | Auto-detecta Next.js, deploy instantáneo |
| Backend (FastAPI) | **Render** | Free | Web Service runtime `python` (pip install + uvicorn) vía `render.yaml` |
| Base de datos | **Render** | Free | PostgreSQL 1GB (renovable cada 90 días) |

**Limitaciones del free tier:**
- Backend duerme tras 15 min de inactividad → primer request ~30-50s
- DB de Render expira cada 90 días (backupear y recrear)
- 750 horas/mes en Render (suficiente para 1 servicio 24/7)

---

## Fase 3: Branch Protection (configurada en `main`)

Ya aplicada vía API. Reglas activas:
- **Require a pull request before merging** (0 aprobaciones requeridas, para flujo solo-dev)
- **Require status checks to pass**: `Backend Tests` y `Frontend Tests`
- **Strict**: la rama del PR debe estar actualizada con `main`
- **Require conversation resolution**: resolver comentarios antes de mergear
- **No force pushes / no deletions** sobre `main`
- `enforce_admins: false` (el admin puede hacer bypass en emergencias)

---

## Archivos del plan

```
.
├── .github/workflows/
│   ├── backend-ci.yml       # pytest en PR
│   └── frontend-ci.yml      # vitest en PR
├── render.yaml              # Render Blueprint (backend + DB)
├── vercel.json              # Vercel config (opcional)
└── CI_CD_PLAN.md            # Este documento
```

---

## Setup manual (una sola vez)

### 1. Vercel (frontend)
- Ir a [vercel.com](https://vercel.com) → Login con GitHub
- Importar repo `JesusD84/thunderroll`
- Root Directory: `frontend`
- Framework: Next.js (auto-detectado)
- Deploy

### 2. Render (backend + DB)
- Ir a [render.com](https://render.com) → Login con GitHub
- New → Blueprint → seleccionar repo
- Render lee `render.yaml` y crea los servicios automáticamente

### 3. GitHub Secrets (si aplica)
- Settings → Secrets and variables → Actions
- Agregar secrets necesarios para los workflows

---

## Variables de entorno necesarias

### Backend (Render) — definidas en `render.yaml`
```
DATABASE_URL                 # Render lo inyecta desde la DB del blueprint
SECRET_KEY                   # generado por Render
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
FRONTEND_URL=https://thunderroll.vercel.app   # habilita CORS para el front
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM   # placeholders
```

### Frontend (Vercel)
```
NEXT_PUBLIC_API_URL=https://thunderroll-backend.onrender.com   # llamadas del navegador
BACKEND_URL=https://thunderroll-backend.onrender.com           # login server-side de NextAuth
NEXTAUTH_URL=https://thunderroll.vercel.app
NEXTAUTH_SECRET=...                                            # openssl rand -base64 32
```

> **Importante:** `BACKEND_URL` y `NEXT_PUBLIC_API_URL` son distintas y ambas necesarias. El login de NextAuth corre server-side y usa `BACKEND_URL`; si falta, el login falla con "Credenciales inválidas" aunque el resto funcione.
