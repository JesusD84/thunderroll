# Thunderoll — Frontend Imports Module (Kanban FR-xx)

Seguimiento local del módulo de importación en el frontend (Next.js App Router, TS).
Convención: **una rama y un PR por tarea**, mensajes de commit descriptivos, tests antes de cada PR.

> Este archivo es de seguimiento local. No es obligatorio subirlo en cada commit de feature.

---

## Decisiones de arquitectura (Fase 2)

- **Data fetching**: `fetch` + `useState` con wrapper centralizado en `lib/api.ts` (coherente con `units`/`transfers`). No se usa React Query/SWR.
- **Flujo**: wizard multipaso en `/imports/new` (archivo+metadata → preview → mapeo asistido → importar) + historial en `/imports`.
- **Toasts**: `sonner` (ya instalado).
- **Tipos**: estrictos; `frame`/`motor` **siempre `string`** (preservar seriales largos, sin notación científica ni `.0`).

### Contrato (recordatorio)

- Campos canónicos: `frame`, `motor`, `color`, `model` (NO `brand`/`engine_number`/`chassis_number`).
- Metadata upload: `batch_period` (ej. "2026-ABRIL") y `product_type` (triciclo/bici eléctrica/scooter), ambos opcionales.
- Archivos soportados: `.xlsx`, `.xls`, `.csv`.
- Preview **no bloquea** import; `invalid_rows` es esperado; import atómico con éxito parcial.
- Base imports: `${API_URL}/api/v1/imports` — `POST /preview`, `POST /upload`, `GET /`, `GET /{id}`, `GET /{id}/errors`, `DELETE /{id}` (solo ADMIN).
- Base equivalencias: `${API_URL}/api/v1/model-equivalences` — CRUD + `GET /unmapped`.
- Auth: `(session as any).accessToken` → header `Authorization: Bearer <token>`.

---

## FR-00 · Análisis y diagnóstico
**Estado:** ✅ DONE

Auditoría de `app/imports/page.tsx` (mock completo), propuesta de arquitectura UI/UX y plan Kanban finalizado.

---

## FR-01 · Cliente API + tipos TS + wrappers UI
**Estado:** ✅ DONE (PR #53) · **Depende de:** FR-00

- `lib/api.ts`: wrapper `fetch` autenticado (inyecta `Bearer`, base `NEXT_PUBLIC_API_URL`, parseo de errores 400/500).
- `lib/imports.ts`: funciones tipadas por endpoint (preview, upload, list, get, errors, delete).
- `lib/types.ts`: `ImportPreviewResponse`, `SheetPreview`, `InvalidRow`, `Issue`, `Validation`, `UploadResult`, `ImportRecord`, `ImportError`, `ModelEquivalence`, `CanonicalField`.
- Wrappers shadcn faltantes: `tabs`, `dialog`, `alert-dialog`, `progress`, `checkbox`, `tooltip`, `skeleton` + toaster `sonner`.
- Tests Vitest del wrapper.

**Acceptance Criteria**
- [x] `apiFetch` adjunta token y normaliza errores.
- [x] Tipos cubren el contrato completo (`frame`/`motor` como `string`).
- [x] Wrappers UI compilan y se integran con Tailwind/shadcn.
- [x] Suite Vitest en verde.

> Nota: la regla genérica `lib/` del `.gitignore` ignoraba `frontend/lib/`; se añadió `!frontend/lib/`. El `<Toaster/>` se montó en `app/layout.tsx`.

---

## FR-02 · Form de upload real
**Estado:** ✅ DONE (PR #55) · **Depende de:** FR-01

- Reemplazar `shipment_batch`/`supplier_invoice` por `batch_period` y `product_type`.
- Selector de archivo `.xlsx/.xls/.csv`; validación cliente (tipo/tamaño).
- Reescribir `tests/imports.test.tsx` (hoy valida el mock).

**Acceptance Criteria**
- [x] Campos del form alineados al contrato.
- [x] `accept` incluye `.csv`.
- [x] Tests actualizados en verde.

> Nota: `batch_period`/`product_type` se capturan aquí pero se envían en el upload (FR-05); `/preview` solo recibe el archivo.

---

## FR-03 · Preview real
**Estado:** ✅ DONE (PR #56) · **Depende de:** FR-02

- `POST /preview`: tabs por hoja (columnas detectadas, mapeo propuesto), `preview_data`, `invalid_rows` + `reasons`, `issues` (level/message/sheet), `validation`.
- **Quitar** el bloqueo de import por errores.

**Acceptance Criteria**
- [x] Render multi-hoja correcto.
- [x] `invalid_rows`/`issues`/`validation` visibles.
- [x] Import nunca se bloquea por filas inválidas.

> Nota: vista previa en `components/imports/PreviewResult.tsx`. El mapeo se muestra de solo lectura; el ajuste interactivo es FR-04.

---

## FR-04 · Mapeo asistido
**Estado:** ✅ DONE (PR #57) · **Depende de:** FR-03

- UI por columna sin mapear → `Select` a `frame/motor/color/model/(ignorar)`.
- Construye `column_mapping` JSON y re-previsualiza.

**Acceptance Criteria**
- [x] `column_mapping` válido enviado a `/preview`.
- [x] Re-preview refleja el mapeo manual.

> Nota: helpers en `lib/imports.ts` (`proposedFieldByColumn`/`effectiveSelection`/`buildColumnMapping`). Limitación: el backend no acepta valor "ignore", así que poner una columna auto-detectada en "Sin mapear" la omite del payload pero el backend la vuelve a auto-detectar.

---

## FR-05 · Import real
**Estado:** ✅ DONE (PR #58) · **Depende de:** FR-04

- `POST /upload` + pantalla de resultado (`successful/failed_imports`, `import_id`, link a errores).
- Manejo de 400/500 con mensajes claros.

**Acceptance Criteria**
- [x] Upload con metadata + `column_mapping`.
- [x] Resultado y errores accesibles.

> Nota: pantalla en `components/imports/ImportResult.tsx`; drill-down de errores con `GET /{id}/errors` desde el resultado. El historial completo es FR-06.

---

## FR-06 · Historial de imports
**Estado:** ✅ DONE (PR #59) · **Depende de:** FR-01

- Lista (`GET /`), detalle (`GET /{id}`), drill-down de errores (`GET /{id}/errors`), borrar (`DELETE /{id}`, ADMIN).

**Acceptance Criteria**
- [x] Lista/detalle/errores funcionando.
- [x] Borrar solo visible/permitido para ADMIN.

> Nota: páginas `app/imports/history/page.tsx` (lista + borrar con `AlertDialog`, gating por `session.user.role === 'admin'`) y `app/imports/[id]/page.tsx` (detalle + tabla de errores). Enlace "Ver historial" añadido al header de `app/imports/page.tsx`. Tests en `tests/imports-history.test.tsx` (6 casos: lista, vacío, borrar admin, ocultar borrar no-admin, detalle+errores, error 404).

---

## FR-07 · Admin de equivalencias de modelos
**Estado:** ✅ DONE (PR #60) · **Depende de:** FR-01

- CRUD `/model-equivalences` + vista `GET /unmapped` (modelos sin equivalencia → crear equivalencia).

**Acceptance Criteria**
- [x] CRUD completo.
- [x] Flujo desde `unmapped` a creación.

> Nota: página `app/model-equivalences/page.tsx` (tabla CRUD con `Dialog` para crear/editar y `AlertDialog` para borrar; sección "Modelos sin equivalencia" con botón que prellena el modelo de fabricante). Gating: crear/editar para ADMIN+MANAGER, borrar solo ADMIN, OPERATOR solo lectura. Errores del backend (400/409) se muestran inline en el formulario. Enlace "Equivalencias" añadido a `Navigation.tsx`. Tests en `tests/model-equivalences.test.tsx` (8 casos).

---

## FR-08 · Estados y UX (transversal)
**Estado:** ✅ DONE (PR #61)

- loading/empty/error consistentes, i18n español, accesibilidad, responsive.

> Nota: componentes reutilizables en `components/ui/states.tsx` (`LoadingState` con `role="status"`/`aria-busy` + label sr-only, `EmptyState` con icono/acción, `ErrorState` con `role="alert"` + botón Reintentar). Aplicados en `imports/history`, `imports/[id]` y `model-equivalences`. Tablas ya responsive (`overflow-auto` en `ui/table`). Tests en `tests/ui-states.test.tsx` (5 casos).

---

## FR-09 · Gating por rol (transversal)
**Estado:** 🔍 EN REVISIÓN

- Ocultar/mostrar acciones según ADMIN/MANAGER/OPERATOR.

> Nota: hook centralizado `lib/auth.ts` (`useAuth` + `getPermissions`/`normalizeRole`). Permisos espejo del backend `require_role`: `manageEquivalences` (ADMIN/MANAGER), `deleteEquivalence`/`deleteImport` (solo ADMIN), `uploadImport` (admin/manager/operator). Refactorizadas `imports/history` y `model-equivalences` para consumir `useAuth` (eliminado el parseo de rol duplicado). Tests en `tests/lib-auth.test.ts` (8 casos).

---

## FR-10 · Tests e2e
**Estado:** ✅ DONE · **Depende de:** FR-05, FR-06, FR-07

- Playwright e2e usando los 4 samples reales (`backend/tests/fixtures/samples/`).

**Acceptance Criteria**
- [x] Flujo upload → preview → import con los 4 samples reales.
- [x] Las filas inválidas no bloquean el import.

> Nota: `e2e/imports.spec.ts` (5 tests, 9s). Alimenta los archivos reales al `input#file` y mockea `POST /preview` y `POST /upload` por `page.route` (patrón de `e2e/auth.spec.ts`); el mock de preview hace eco del filename subido leyéndolo del multipart. Verifica encabezado de preview, validación, campos detectados y pantalla "Importación completada".
>
> Validación manual adicional en producción (Render/Vercel) con los 4 samples reales subidos uno a uno vía UI, incluyendo `jc 电机车架号.xl.xlsx` (98 filas, header duplicado embebido + motor duplicado detectados y omitidos correctamente; 96 unidades importadas, verificadas en `/units` sin duplicados y con el conteo total correcto tras el fix de paginación de FR-units-pagination).

---

## Resumen

| ID | Título | Depende de | Estado |
|---|---|---|---|
| FR-00 | Análisis y diagnóstico | — | ✅ DONE |
| FR-01 | Cliente API + tipos TS + wrappers UI | FR-00 | ✅ DONE (#53) |
| FR-02 | Form de upload real | FR-01 | ✅ DONE (#55) |
| FR-03 | Preview real | FR-02 | ✅ DONE (#56) |
| FR-04 | Mapeo asistido | FR-03 | ✅ DONE (#57) |
| FR-05 | Import real | FR-04 | ✅ DONE (#58) |
| FR-06 | Historial de imports | FR-01 | ✅ DONE (#59) |
| FR-07 | Admin de equivalencias | FR-01 | ✅ DONE (#60) |
| FR-08 | Estados y UX (transversal) | — | ✅ DONE (#61) |
| FR-09 | Gating por rol (transversal) | — | ✅ DONE (#62) |
| FR-10 | Tests e2e | FR-05/06/07 | ✅ DONE |
