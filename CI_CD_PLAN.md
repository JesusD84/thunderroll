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

Al abrir PR hacia `main`, se ejecutan automáticamente:

### Backend CI
- **Trigger:** cambios en `backend/**`
- Python 3.11 + pip install
- `pytest` con SQLite en memoria (sin Postgres)
- Resultado visible en el PR: ✅ o ❌

### Frontend CI
- **Trigger:** cambios en `frontend/**`
- Node 18 + `npm ci`
- `vitest run` (150 tests)
- `npm run lint`
- `npm run build`
- Resultado visible en el PR: ✅ o ❌

---

## Fase 2: CD — Deploy a QA

Al mergear a `main`, se despliega automáticamente:

| Componente | Plataforma | Plan | Detalle |
|---|---|---|---|
| Frontend (Next.js) | **Vercel** | Free | Auto-detecta Next.js, deploy instantáneo |
| Backend (FastAPI) | **Render** | Free | Web Service desde Dockerfile |
| Base de datos | **Render** | Free | PostgreSQL 1GB (renovable cada 90 días) |

**Limitaciones del free tier:**
- Backend duerme tras 15 min de inactividad → primer request ~30-50s
- DB de Render expira cada 90 días (backupear y recrear)
- 750 horas/mes en Render (suficiente para 1 servicio 24/7)

---

## Fase 3: Branch Protection (opcional)

En GitHub → Settings → Branches → `main`:
- Require a pull request before merging
- Require status checks: `Backend CI`, `Frontend CI`

---

## Archivos del plan

```
.
├── .github/workflows/
│   ├── backend-ci.yml       # pytest en PR
│   └── frontend-ci.yml      # vitest + lint + build en PR
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

### Backend (Render)
```
DATABASE_URL=postgresql://...  (Render lo genera auto)
SECRET_KEY=your-secret-key-here-thunderrol-2024
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend (Vercel)
```
NEXT_PUBLIC_API_URL=https://thunderroll-backend.onrender.com
NEXTAUTH_URL=https://thunderroll.vercel.app
NEXTAUTH_SECRET=your-nextauth-secret-here-thunderrol-2024
```
