# Frontend Test Plan — Thunderroll

## Stack

| Capa | Tecnología |
|---|---|
| Framework | Next.js 14 (App Router) |
| UI | React 18, Tailwind CSS, shadcn/ui (Radix) |
| Auth | NextAuth.js v4 (Credentials + JWT) |
| Data | SWR, fetch nativo al backend |
| Forms | react-hook-form + zod |
| Charts | Recharts |
| Tests | **Vitest + React Testing Library + Playwright** (propuesto) |

## Estructura actual

```
frontend/
├── app/
│   ├── login/          # Login page
│   ├── page.tsx        # Dashboard (stats, charts)
│   ├── units/          # Lista + new + [id]
│   ├── transfers/      # Lista + crear transferencia
│   ├── imports/        # Excel/CSV import con preview
│   ├── reports/        # Inventory/transfers/sales + export
│   └── settings/       # Locations CRUD + Users list
├── components/
│   ├── Navigation.tsx  # Top nav + auth redirect
│   ├── providers/      # SessionProvider (NextAuth)
│   └── ui/             # 11 shadcn/ui components
└── 0 tests actuales
```

---

## Fase 0 — Infraestructura de testing

**Objetivo:** Instalar y configurar Vitest, React Testing Library (RTL) y Playwright.

### 0a. Instalar dependencias

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitejs/plugin-react
npm install -D @playwright/test
npx playwright install
```

### 0b. Configurar Vitest (`vitest.config.ts`)

- jsdom environment
- path alias `@/` → `./`
- setup file para `@testing-library/jest-dom`

### 0c. Configurar Playwright (`playwright.config.ts`)

- Base URL `http://localhost:3000`
- Projects: chromium, firefox, webkit
- Web server: `npm run dev` (auto-start)

### 0d. Agregar scripts a `package.json`

```json
{
  "test": "vitest run",
  "test:watch": "vitest",
  "test:e2e": "playwright test",
  "test:e2e:ui": "playwright test --ui"
}
```

**Estimado:** 4-6 tests de infra

---

## Fase 1 — UI Components (unit tests con RTL)

**Objetivo:** Testear los 11 componentes shadcn/ui en aislamiento.

### 1a. Componentes de display

| Componente | Tests |
|---|---|
| `Badge` | renderiza children, aplica variantes (default, secondary, destructive, outline) |
| `Card` | renderiza CardHeader/CardContent/CardTitle/CardDescription |
| `Alert` | renderiza título, descripción, variante destructive |
| `Table` | renderiza headers, rows, cuerpo vacío |

### 1b. Componentes de input

| Componente | Tests |
|---|---|
| `Button` | renderiza children, onClick, variantes, disabled state, loading state |
| `Input` | renderiza, onChange, placeholder, disabled, type password |
| `Label` | renderiza texto, htmlFor asocia con input |
| `Select` | renderiza trigger, abre opciones, selecciona valor, onChange |

### 1c. Componentes compuestos

| Componente | Tests |
|---|---|
| `Calendar` | renderiza mes actual, navegación entre meses, selección de fecha |
| `DatePicker` | renderiza, abre popover, selecciona fecha, muestra fecha formateada |
| `Popover` | abre/cierra al click, renderiza contenido |

**Estimado:** 30-40 tests

---

## Fase 2 — Navigation & Auth (unit + integration)

**Objetivo:** Testear el flujo de autenticación y navegación.

### 2a. Navigation component

| Test | Descripción |
|---|---|
| Renderiza links | Todos los items de navegación visibles |
| Link activo | El link de la ruta actual tiene estilo activo |
| Mobile menu | Abre/cierra menú hamburguesa |
| Redirect no auth | Redirige a /login si no hay sesión |
| Logout | Llama a signOut y redirige a /login |
| Oculta en login | No renderiza navegación en /login |

### 2b. Login page

| Test | Descripción |
|---|---|
| Renderiza formulario | Email, password, botón Login |
| Submit exitoso | Llama a signIn con credenciales, redirige a / |
| Error credenciales | Muestra mensaje de error |
| Campos vacíos | Muestra validación |
| Redirect si autenticado | Si ya hay sesión, redirige a / |
| Loading state | Botón deshabilitado durante submit |

### 2c. SessionProvider

| Test | Descripción |
|---|---|
| Renderiza children | Envuelve y renderiza hijos |
| Provee sesión | Mock de useSession disponible en children |

**Estimado:** 15-20 tests

---

## Fase 3 — Dashboard (unit + integration)

**Objetivo:** Testear la página principal de dashboard.

### 3a. Estados de UI

| Test | Descripción |
|---|---|
| Loading | Muestra "Cargando dashboard..." |
| Error | Muestra mensaje de error |
| Sin token | No hace fetch si no hay accessToken |

### 3b. Datos

| Test | Descripción |
|---|---|
| Stats cards | Renderiza total, available, sold, in_transit |
| Inventory by location | Renderiza tabla/lista de ubicaciones |
| Sales by month | Renderiza gráfico o lista de ventas |
| Recent transfers | Renderiza tabla de transfers recientes |
| Recent imports | Renderiza tabla de imports recientes |
| Links de acción | Botones "Nueva Unidad", "Nueva Transferencia" navegan |

**Estimado:** 10-12 tests

---

## Fase 4 — Units Module

**Objetivo:** Testear CRUD de unidades.

### 4a. Units List (`/units`)

| Test | Descripción |
|---|---|
| Loading state | Muestra spinner/loading |
| Lista unidades | Renderiza tabla con unidades del API |
| Búsqueda | Filtra por engine/chassis/model |
| Filtro status | Filtra por AVAILABLE/SOLD/IN_TRANSIT |
| Filtro location | Filtra por ubicación |
| Tabla vacía | Mensaje cuando no hay resultados |
| Link nueva unidad | Botón "+" navega a /units/new |
| Error API | Muestra mensaje de error |

### 4b. New Unit (`/units/new`)

| Test | Descripción |
|---|---|
| Renderiza formulario | Todos los campos visibles |
| Carga locations | Select de ubicaciones populado |
| Submit exitoso | POST al API, redirige a /units |
| Validación campos | Campos requeridos muestran error |
| Error API | Muestra mensaje de error del backend |
| Botón cancelar | Link "Volver" navega a /units |

### 4c. Unit Detail (`/units/[id]`)

| Test | Descripción |
|---|---|
| Carga unidad | Muestra datos de la unidad |
| 404 | Muestra mensaje si unidad no existe |
| Transferencias | Muestra historial de transfers |
| Editar | Botón editar navega a formulario |

**Estimado:** 18-22 tests

---

## Fase 5 — Transfers Module

**Objetivo:** Testear listado y creación de transferencias.

### 5a. Transfers List (`/transfers`)

| Test | Descripción |
|---|---|
| Lista transfers | Tabla con transfers del API |
| Badge status | Colores por estado (PENDING, IN_TRANSIT, RECEIVED) |
| Filtros | Por status, ubicación, fecha |
| Nueva transferencia | Formulario para crear transfer |

### 5b. Create Transfer

| Test | Descripción |
|---|---|
| Select unidad | Carga unidades disponibles |
| Select destino | Carga locations |
| Submit exitoso | POST al API, refresca lista |
| Validación | Misma ubicación origen/destino → error |
| Error API | Muestra mensaje de error |

**Estimado:** 10-12 tests

---

## Fase 6 — Imports Module

**Objetivo:** Testear importación de archivos Excel/CSV.

### 6a. Import Page (`/imports`)

| Test | Descripción |
|---|---|
| Upload file | Selecciona archivo .xlsx/.csv |
| Preview | Muestra preview de datos antes de importar |
| Dry run | Valida sin insertar |
| Errores validación | Muestra filas con errores |
| Import exitoso | Inserta unidades, muestra conteo |
| File inválido | Rechaza .txt/.pdf |
| Columnas faltantes | Muestra error si faltan columnas requeridas |

**Estimado:** 8-10 tests

---

## Fase 7 — Reports Module

**Objetivo:** Testear reportes y exportación Excel.

### 7a. Reports Page (`/reports`)

| Test | Descripción |
|---|---|
| Tabs | Cambia entre inventory/transfers/sales |
| Date filters | DatePicker para dateFrom/dateTo |
| Preview data | Muestra datos del reporte |
| Export Excel | Descarga archivo .xlsx |
| Download filename | Nombre de archivo correcto |
| Error estado | Muestra error si falla el API |

**Estimado:** 8-10 tests

---

## Fase 8 — Settings Module

**Objetivo:** Testear Locations CRUD y Users list.

### 8a. Locations

| Test | Descripción |
|---|---|
| Lista locations | Tabla con locations del API |
| Crear location | Formulario, POST, aparece en lista |
| Editar location | Botón editar, PUT, actualiza lista |
| Eliminar location | DELETE, desaparece de lista |
| Error eliminar con unidades | Muestra error traducido |
| Validación nombre | Nombre vacío → error |

### 8b. Users

| Test | Descripción |
|---|---|
| Lista users | Tabla con usuarios del API |
| Badge rol | Color por rol (ADMIN, MANAGER, etc.) |
| Solo admin | Endpoints restringidos no accesibles para VIEWER |

**Estimado:** 10-12 tests

---

## Fase 9 — E2E Tests (Playwright)

**Objetivo:** Flujos completos de usuario en navegador real.

### 9a. Auth flows

| Test | Descripción |
|---|---|
| Login exitoso | Login → redirect a dashboard |
| Login fallido | Credenciales inválidas → mensaje error |
| Logout | Click logout → redirect a login |
| Ruta protegida | /units sin login → redirect a login |
| Sesión expirada | Token expirado → redirect a login |

### 9b. CRUD flows

| Test | Descripción |
|---|---|
| Crear unidad | Navegar → formulario → submit → ver en lista |
| Crear transferencia | Seleccionar unidad → destino → submit |
| Importar Excel | Subir archivo → preview → confirmar |
| Exportar reporte | Seleccionar filtros → descargar Excel |

### 9c. Responsive

| Test | Descripción |
|---|---|
| Mobile nav | Menú hamburguesa funciona en viewport pequeño |
| Tablas responsive | Scroll horizontal en mobile |

**Estimado:** 12-15 tests

---

## Fase 10 — Use Case Tests (Smoke / Acceptance) 🔥

**Objetivo:** Tests que validan los flujos primordiales de la app de punta a punta.
Si estos tests fallan, **la funcionalidad core está rota** y no se debe deployar.

**Tipo:** Integration tests con RTL + MSW (API real mockeada con datos realistas).
Se ejecutan en CI antes de cada merge a main.

### UC-1: Autenticación

| ID | Test | Qué valida |
|---|---|---|
| UC-1.1 | Login exitoso | Usuario con credenciales válidas → obtiene token JWT → redirige a dashboard |
| UC-1.2 | Login fallido | Credenciales inválidas → error "Credenciales incorrectas" → se queda en /login |
| UC-1.3 | Sesión expirada | Token expirado al llamar API → redirige a /login |
| UC-1.4 | Ruta protegida sin sesión | GET /units sin token → redirige a /login |
| UC-1.5 | Logout | Click logout → limpia sesión → redirige a /login |

### UC-2: Gestión de Inventario (CRUD Unidades)

| ID | Test | Qué valida |
|---|---|---|
| UC-2.1 | Listar unidades | GET /units → tabla con todas las unidades, paginación, badges de status |
| UC-2.2 | Buscar unidad | Escribir "HXY123" en search → tabla filtrada solo con matches |
| UC-2.3 | Filtrar por status | Select "Disponible" → solo unidades AVAILABLE visibles |
| UC-2.4 | Filtrar por ubicación | Select "Bodega Central" → solo unidades en esa ubicación |
| UC-2.5 | Crear unidad | Llenar formulario → POST /units → 201 → aparece en lista |
| UC-2.6 | Crear unidad sin motor | Formulario sin engine_number → status WAREHOUSE_UNIDENTIFIED |
| UC-2.7 | Ver detalle unidad | Click en unidad → /units/[id] → muestra engine, chassis, location, transfers |
| UC-2.8 | Unidad no existe | GET /units/9999 → 404 → mensaje "Unidad no encontrada" |

### UC-3: Transferencias

| ID | Test | Qué valida |
|---|---|---|
| UC-3.1 | Crear transferencia | Seleccionar unidad + destino → POST /transfers → unidad status IN_TRANSIT |
| UC-3.2 | Recibir transferencia | Marcar transfer como RECEIVED → unidad status AVAILABLE en nueva ubicación |
| UC-3.3 | Transfer mismo origen/destino | Misma ubicación → error 400 → mensaje validación |
| UC-3.4 | Transfer unidad inexistente | unit_id=9999 → error 404 |
| UC-3.5 | Listar transfers con filtros | GET /transfers?status=IN_TRANSIT → solo transfers activos |

### UC-4: Importación Masiva

| ID | Test | Qué valida |
|---|---|---|
| UC-4.1 | Importar Excel válido | Subir .xlsx con 10 unidades → preview → confirmar → 10 unidades creadas |
| UC-4.2 | Preview antes de importar | Subir archivo → ver primeras 5 filas → columnas mapeadas correctamente |
| UC-4.3 | Archivo con errores | Subir .xlsx con filas inválidas → errores por fila → unidades válidas se importan |
| UC-4.4 | Archivo sin columnas requeridas | Subir .xlsx sin columna "frame number" → error "Missing required columns" |
| UC-4.5 | Formato no soportado | Subir .pdf → error "Invalid file type" |

### UC-5: Reportes y Exportación

| ID | Test | Qué valida |
|---|---|---|
| UC-5.1 | Dashboard con datos | GET /reports/dashboard → stats cards con números correctos |
| UC-5.2 | Dashboard vacío | Sin unidades → dashboard muestra ceros, no crashea |
| UC-5.3 | Exportar inventario Excel | GET /reports/export/inventory → descarga .xlsx con columnas correctas |
| UC-5.4 | Exportar transfers Excel | GET /reports/export/transfers → descarga .xlsx |
| UC-5.5 | Exportar ventas Excel | GET /reports/export/sales → descarga .xlsx con filtro de fechas |

### UC-6: Administración

| ID | Test | Qué valida |
|---|---|---|
| UC-6.1 | Crear ubicación | POST /locations → aparece en lista de settings |
| UC-6.2 | Eliminar ubicación con unidades | DELETE /locations/1 → error 400 "hay X unidades en esta ubicación" |
| UC-6.3 | Eliminar ubicación vacía | DELETE /locations/99 → 200 → desaparece de lista |
| UC-6.4 | Listar usuarios | GET /users → tabla con roles, badges de admin/manager/viewer |
| UC-6.5 | Viewer no puede crear unidades | Usuario VIEWER → botón "Nueva Unidad" oculto/deshabilitado |
| UC-6.6 | Viewer no puede acceder a settings | GET /settings como VIEWER → redirige o muestra "No autorizado" |

### UC-7: Flujos Completos (End-to-End críticos)

| ID | Test | Qué valida |
|---|---|---|
| UC-7.1 | Ciclo completo unidad | Crear unidad → transferir a sucursal → recibir → vender → aparece en reporte ventas |
| UC-7.2 | Importar y verificar | Importar 5 unidades Excel → verlas en /units → filtrar por ubicación → exportar reporte |
| UC-7.3 | Multi-usuario | Admin crea usuario Operador → Operador hace login → crea unidad → Admin la ve en dashboard |

---

## Resumen

| Fase | Tipo | Tests est. |
|---|---|---|
| 0 | Infra | 4-6 |
| 1 | UI Components | 30-40 |
| 2 | Navigation & Auth | 15-20 |
| 3 | Dashboard | 10-12 |
| 4 | Units | 18-22 |
| 5 | Transfers | 10-12 |
| 6 | Imports | 8-10 |
| 7 | Reports | 8-10 |
| 8 | Settings | 10-12 |
| 9 | E2E (Playwright) | 12-15 |
| **10** | **Use Cases (Smoke)** 🔥 | **32** |
| **Total** | | **157-191** |

---

## Notas

- **Sin tests actuales.** El frontend no tiene ningún test. Se empieza desde cero.
- **Mock de API:** Usar `msw` (Mock Service Worker) para interceptar fetch en tests de RTL.
- **Mock de NextAuth:** Usar helper `mockNextAuth` para simular sesiones en tests unitarios.
- **Playwright:** Solo en Fase 9. Las fases 1-8 son unitarias con Vitest + RTL.
- **Prioridad:** Fases 1-4 cubren el 70% del código frontend (componentes base + units + dashboard).
