# Ramp-up de Producto — Thunderoll

> Documento de onboarding para quien entra al proyecto desde el lado del **cliente y el negocio**.
> Si buscas el lado técnico (stack, arquitectura, cómo correr el código), ver [`RAMPEO_TECNICO.md`](./RAMPEO_TECNICO.md).

---

## 1. Qué es Thunderoll

Empresa de scooters y motos con operación en **Guadalajara, Jalisco**. Compra scooters a proveedores (que
vienen en inglés y chino), los recibe en bodega, los mueve entre sucursales y los vende.

**Thunderoll no fabrica**: comercializa. Eso explica todo el diseño del sistema — la dificultad real no es
"vender", es **saber en todo momento qué unidad es, dónde está y en qué estado**.

## 2. Qué problema resuelve el sistema

El problema que el sistema ataca es tener el inventario fuera del sistema: en hojas de cálculo y
conversaciones sueltas. Eso genera tres problemas concretos:

| Problema | Cómo lo resuelve el sistema |
|---|---|
| *"¿Ya llegó la moto que pidió la sucursal?"* | Cada unidad tiene un estado y una ubicación actual consultable |
| *"¿Qué pasó con esta unidad si desapareció?"* | Cada movimiento queda registrado como transferencia con origen, destino, quién despachó y quién recibió |
| *"¿Cuántas unidades tengo y cuántas vendí?"* | Reportes con conteos por ubicación, marca, mes y exportación a Excel |

El sistema **no reemplaza al ERP contable** ni a la facturación. Es control de inventario y trazabilidad
operativa.

## 3. Quién lo usa — y qué hace cada uno

El sistema tiene tres roles. No es decoración: cada rol refleja quién tiene el control físico de las cosas.

### Administrador
- Control total: usuarios, ubicaciones, inventario, reportes
- Es el único que puede **borrar** un historial de importación o una equivalencia
- Da de alta a Manager y Operativo desde Configuración → Usuarios

### Manager (Gerencia / Control de inventario)
- **Importa los Excel del proveedor** — es su tarea central
- Administra el CRUD de equivalencias de modelo
- Ve todos los reportes y las transferencias
- Crea cuentas de Operativo

### Operativo (el que está en bodega o sucursal)
- **Ve** las unidades y dónde están
- **Despacha y recibe** transferencias (movimiento físico de la moto)
- **Marca una unidad como vendida** — ojo: lo hace desde el botón "Vender" de la ficha de la unidad, que
  llama a `POST /transfers/unit/{id}` con destino vacío. **No** usa `PUT /units/{id}`, que está reservado a
  ADMIN y MANAGER
- No ve el dashboard, ni importaciones, ni equivalencias, ni reportes, ni configuración

> **Para el dev:** el gating de la UI vive en `frontend/lib/auth.ts` (`getPermissions`) y **es el espejo**
> de `require_role()` del backend. Si agregas un permiso, cámbialo en los dos lados o la UI va a prometer
> algo que la API rechaza.

## 4. El corazón del sistema: el ciclo de vida de una unidad

```
                    Importar Excel
                          │
                          ▼
              ┌───────────────────────┐
              │       AVAILABLE       │ ← entra directo a bodega, ya identificada
              └───────────┬───────────┘
                          │ se transfiere a otra ubicación
                          ▼
   Almacén Principal ──▶ ┌─────────────┐
              ┌───────────│  IN_TRANSIT │ ← va en camino
              │          └──────┬──────┘
              │                 │ se recibe en destino ("Confirmar Llegada")
              │                 ▼
              │          ┌────────────┐
              └─────────▶│  AVAILABLE │ ← ahora disponible en la sucursal
                         └──────┬─────┘
                                │ se marca como vendida
                                ▼
                         ┌────────────┐
                         │    SOLD    │ + sold_date
                         └────────────┘
```

> `WAREHOUSE_UNIDENTIFIED` es el estado **por defecto** de una unidad creada a mano sin especificar el
> status. **El import nunca lo usa**: toda unidad importada entra como `AVAILABLE` en "Almacén Principal"
> (esa ubicación se crea sola si no existe).

**Cada cambio de estado deja rastro en dos sitios**: el `status` de la unidad **y** una fila en la tabla
`transfers`. La trazabilidad completa se reconstruye con ambos. *No existe una tabla de "movimientos"*
— si alguna vez la buscas, no está, y no debería estar.

> La ficha de la unidad sí rotula ese bloque como **"Historial de Movimientos"**. Es solo una etiqueta de
> la UI: por debajo son filas de `transfers`.

### Transferencias
Una transferencia registra el movimiento de **una** unidad (no hay tabla pivote, no hay carga masiva).

En el flujo de la UI, la transferencia **nace `PENDING`** (así la deja el schema) y el siguiente paso es
**`RECEIVED`**: se crea desde el formulario "Nueva Transferencia" y luego se pulsa **"Confirmar Llegada"**.
El estado `IN_TRANSIT` es el de la **unidad** mientras viaja (y el de la transferencia en el flujo de
despacho desde la ficha de la unidad).

Al recibir en destino, la unidad pasa a `AVAILABLE` y su `current_location_id` se actualiza al destino.

> `CANCELLED` existe como estado en el modelo y el backend lo soporta vía `PUT /transfers/{id}`, pero
> **no hay ninguna acción en la UI que cancele una transferencia**. No prometas esa capacidad al cliente.

## 5. El módulo de importaciones — por qué es el corazón

Es la funcionalidad más complicada del sistema y merece explicación de negocio, no técnica.

### El problema real
El proveedor **no manda un formato estándar**. Manda archivos que cambian de un lote a otro:

- Cabeceras en inglés, en español o en chino (`车架` = frame, `电机` = motor, `型号` = modelo)
- Archivos sin fila de cabecera
- Un archivo con **varias hojas**, algunas de adorno
- Columnas basura (índices, leyendas de color, celdas fusionadas)
- Números de serie guardados como número, que Excel convierte en `3.52e+14` o en `352...0.0`

Si el sistema exigiera un formato perfecto, el proveedor dejaría de entregar el archivo completo y se
perderían unidades. La tolerancia del parser es lo que hace que la herramienta sea usable en la práctica.

### La decisión de diseño
El import **nunca se bloquea por filas malas**. La estrategia es:

1. **Preview** (`POST /imports/preview`): el backend analiza el archivo y devuelve qué detectó — columnas
   reconocidas, hojas, filas inválidas, advertencias. **No escribe nada en la base de datos.**
2. **Mapeo asistido**: el usuario ve las columnas detectadas y puede corregir a mano cualquier columna que
   el sistema no entendió (ej: "esto que dice `NO` es el modelo"). Se re-previsualiza.
3. **Import** (`POST /imports/upload`): se persiste. Las filas válidas se escriben en **una sola
   transacción** (todo o nada); las filas inválidas se registran como errores por fila y **no cancelan**
   el resto.

> **Alcance del preview**: el preview solo detecta filas **sin identificador** y duplicados **dentro del
> mismo archivo**. Un serial que ya existe en la base solo se detecta al importar, y esa fila acaba en el
> historial de errores. El preview devuelve además una muestra de las primeras 10 filas válidas y lista
> como máximo 100 filas inválidas (el total sí viene completo, en `invalid_rows_count`).
>
> **Trampa a conocer**: una fila sin `frame` ni `motor` se descarta **en silencio** al importar — no sale
> en el historial de errores (solo se registran los duplicados). Por eso el total del import puede ser
> menor que el número de filas que viste en el preview.

Resultado: el cliente sube un archivo "basura" y aun así entra la gran mayoría de las unidades, con un
informe claro de qué falló y por qué.

### Campos canónicos
El sistema normaliza todo a cinco campos:

| Campo canónico | Qué es | Sinónimos que reconoce el parser | Columna en la BD |
|---|---|---|---|
| `frame` | Número de chasis / VIN | frame, chassis, chasis, vin, 车架 | `chassis_number` |
| `motor` | Número de motor | motor, engine, 电机, 发动机 | `engine_number` |
| `color` | Color | color, colour, 颜色 | `color` |
| `model` | Modelo | model, modelo, 型号, 车型 | `model` |
| `brand` | Marca | marca, brand, 品牌 | `brand` |

> El parser habla con `frame`/`motor`; la base de datos guarda `chassis_number`/`engine_number`. La
> traducción ocurre al importar. Si buscas `frame` en la base de datos, no lo vas a encontrar.

Si falta `marca` o `color` en el archivo, se guarda `"Sin especificar"`. El `model` cae primero al **nombre
de la hoja** (los proveedores suelen poner el modelo ahí) y solo después a ese placeholder.

**Todos son texto**, nunca números: un número de serie de 15 dígitos debe sobrevivir intacto.

### Metadata del lote
El proveedor manda el periodo del lote **fuera del archivo** (ej. `"2026-ABRIL"`) y se captura en el form
como `batch_period`. El backend **no valida el formato**: solo recorta espacios, así que el ejemplo es
ilustrativo, no un formato impuesto.

`product_type` existe en backend y BD pero **actualmente está desactivado en la UI**: el frontend
simplemente no lo envía, así que llega `None`.

## 6. Equivalencias de modelo

El proveedor llama a sus productos de una forma (`X3`, `xiaodou`, `diaoyu`, `TY-D530`) y Thunderoll usa
nombres internos distintos para lo mismo.

La tabla `model_equivalences` mapea **nombre del fabricante → modelo interno del cliente**. Durante el
import, si hay equivalencia, se usa el nombre interno; si no la hay, **se conserva el nombre del
fabricante** y el import sigue adelante (no se bloquea).

La pantalla **Equivalencias** permite:
- CRUD de equivalencias
- Ver la lista de **modelos sin equivalencia** (`GET /model-equivalences/unmapped`) y crear la
  equivalencia desde ahí con el modelo prellenado

## 7. Qué ve el cliente

**Dashboard** (ADMIN y MANAGER) — totales de unidades (total / disponibles / vendidas / en tránsito),
inventario por ubicación, inventario por marca, ventas por mes, transferencias recientes, imports recientes.

**Reportes** — inventario, transferencias y ventas, cada uno con **exportación a Excel**.

**Unidades** — listado con filtro server-side y paginación, detalle con el historial de transferencias,
alta manual.

**Transferencias** — grid con ID, Unidad, Ruta (origen → destino), Estado, Fecha, Completada y Creado Por.
La acción disponible es **"Confirmar Llegada"** sobre transferencias `PENDING` o `IN_TRANSIT`; al
confirmar, la unidad queda `AVAILABLE` en el destino.

**Configuración** — dos secciones: **Ubicaciones** y **Usuarios**.

**Equivalencias** — pantalla propia en el menú (no dentro de Configuración): CRUD + modelos sin
equivalencia.

## 8. Glosario

| Término | Significado |
|---|---|
| **Unidad** | Una moto/scooter individual. El objeto central del sistema |
| **Transferencia** | Movimiento de una unidad entre dos ubicaciones |
| **Ubicación** | Bodega, taller o sucursal |
| **Frame / chasis** | Identificador único del chasis |
| **Motor** | Identificador único del motor |
| **Batch period** | Periodo del lote de importación, ej. `"2026-ABRIL"` |
| **Import** | Un archivo del proveedor procesado, con su historial de errores |
| **Equivalencia** | Traducción nombre de fabricante → modelo interno |
| **Unidad sin identificar** (`WAREHOUSE_UNIDENTIFIED`) | Estado por defecto de una unidad creada a mano sin especificar status. El import nunca lo usa |
| **"Sin especificar"** | Texto que se guarda cuando al proveedor le falta un campo (marca, color o modelo) |

## 9. Límites actuales del sistema (sé honesto con el cliente)

Cosas que **no** hace hoy, para no prometer lo que no existe:

- **No hay tabla de movimientos**: la trazabilidad se reconstruye desde transferencias + estado
- **No hay carga masiva de transferencias**: una unidad por transferencia
- **No se puede cancelar una transferencia desde la UI**: `CANCELLED` existe en el modelo pero no hay acción
- **Las filas sin motor ni chasis se descartan en silencio al importar** y no aparecen en el historial de
  errores (solo se registran los duplicados)
- **`product_type` está capturado en backend pero desactivado en la UI**
- **El backend no acepta "ignorar columna"** en el mapeo manual: el frontend ofrece la opción "Sin mapear",
  pero esa columna simplemente no viaja en el payload, así que el backend la vuelve a auto-detectar
- **No hay venta con precio, factura ni cliente**: la venta es un estado (`SOLD` + fecha). No es un POS
- **Alembic no corre en el deploy**: las tablas se crean con `create_all` al arrancar el backend. Las
  migraciones existen en el repo pero están fuera del flujo de despliegue actual
- **El seed es mínimo**: solo crea la cuenta admin bootstrap. El cliente crea sus ubicaciones y usuarios
  reales; no hay datos demo de inventario

## 10. Referencia rápida — dónde está cada cosa

| Necesitas… | Está en… |
|---|---|
| Lógica de negocio | `backend/app/services/` |
| Rutas de la API | `backend/app/api/v1/endpoints/` |
| Modelos de datos | `backend/app/models/models.py` |
| Pantallas | `frontend/app/` |
| Helpers y cliente API | `frontend/lib/` |
| Componentes UI | `frontend/components/ui/` (shadcn/ui) |
| Seguimiento del módulo de imports | `frontend/IMPORTS_MODULE_TASKS.md` |
| Contexto técnico completo | [`RAMPEO_TECNICO.md`](./RAMPEO_TECNICO.md) · [`claude.md`](../claude.md) · [`AGENTS.md`](../AGENTS.md) |
