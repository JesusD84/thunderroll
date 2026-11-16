import json
import logging
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import TransferStatus, UnitStatus, UserRole
from app.services.auth_service import require_role
from app.services.color_mapping import normalize_color
from app.services.import_parser import (
    CANONICAL_FIELDS,
    apply_manual_mapping,
    parse_workbook,
)
from app.services.model_equivalence_service import resolve_internal_model
from app.services.upload_service import (
    ImportValidationError,
    UnreadableFileError,
    UploadError,
    read_upload,
    resolve_stored_path,
    save_upload,
    validate_filename,
)

router = APIRouter()

logger = logging.getLogger(__name__)

# Excepciones que significan "este archivo no se puede leer" (problema del
# usuario que se resuelve con un 422) frente a cualquier otra cosa (que es un
# fallo inesperado y se responde con un 500 genérico).
FILE_READ_ERRORS = (zipfile.BadZipFile, UnicodeDecodeError, ValueError)

# Persistence defaults for descriptive fields the supplier may omit. The parser
# resolves frame/motor/color/model/brand; brand, color and model can be blank
# (or the column absent), yet Unit requires them NOT NULL.
DEFAULT_BRAND = "Sin especificar"
DEFAULT_COLOR = "Sin especificar"
DEFAULT_MODEL = "Sin especificar"


def _parse_column_mapping(raw: str | None) -> dict:
    """Parse the optional manual column->field mapping sent on the upload form.

    Expects a JSON object like ``{"NO": "model", "Color": "color"}`` mapping a
    source column name to a canonical field. Returns ``{}`` when absent. Raises a
    400 on malformed JSON, the wrong shape, or an unknown canonical field (TR-07).
    """
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="column_mapping must be valid JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=400,
            detail="column_mapping must be a JSON object of column -> field",
        )
    mapping: dict[str, str] = {}
    for column, field_name in parsed.items():
        if not isinstance(field_name, str) or field_name not in CANONICAL_FIELDS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid field '{field_name}' for column '{column}'. "
                    f"Valid fields: {', '.join(CANONICAL_FIELDS)}."
                ),
            )
        mapping[str(column)] = field_name
    return mapping


def _text_or_default(value, default: str) -> str:
    """Coerce a parser cell value to a non-empty string, or fall back."""
    if value is None:
        return default
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return default
    return text


def _http_error(exc: UploadError) -> HTTPException:
    """Translate a typed upload error into its HTTP response.

    The message shown to the user is the one written for them; the cause is
    never exposed.
    """
    return HTTPException(status_code=exc.status_code, detail=exc.user_message)


def _internal_error(exc: Exception) -> HTTPException:
    """Build the generic 500 for an unexpected failure.

    The raw exception text never reaches the client: it goes to the server log
    together with a request id that the user can quote when reporting the
    problem.
    """
    request_id = uuid4().hex
    logger.exception(
        "Unexpected error while processing an import (request_id=%s)", request_id
    )
    return HTTPException(
        status_code=500,
        detail=(
            "Error interno al procesar el archivo. Vuelve a intentarlo y, si "
            f"el problema sigue, comparte esta referencia: {request_id}"
        ),
    )


def _mark_failed(db: Session, import_record: models.Import, message: str) -> None:
    """Mark the import as failed, keeping a safe note for the history."""
    import_record.status = "failed"
    import_record.notes = message
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not mark the import as failed")


@router.get("/", response_model=list[schemas.Import])
def get_imports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    imports = (
        db.query(models.Import)
        .order_by(models.Import.import_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return imports


@router.get("/{import_id}", response_model=schemas.Import)
def get_import(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    import_record = (
        db.query(models.Import).filter(models.Import.id == import_id).first()
    )
    if not import_record:
        raise HTTPException(status_code=404, detail="Import record not found")
    return import_record


@router.get("/{import_id}/errors")
def get_import_errors(
    import_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    errors = (
        db.query(models.ImportError)
        .filter(models.ImportError.import_id == import_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return errors


@router.post("/upload")
def upload_inventory_file(
    file: UploadFile = File(...),
    batch_period: str | None = Form(None),
    product_type: str | None = Form(None),
    column_mapping: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    """Store an inventory file and import it.

    The endpoint is deliberately **synchronous**: the heavy work (pandas +
    sync SQLAlchemy) must not block the event loop, and FastAPI runs ``def``
    endpoints in its threadpool.

    The file is stored with a server-generated name (``uuid4`` + the validated
    extension) inside a directory that no route serves; the name sent by the
    client is kept only as metadata.
    """
    # The client-provided name is only metadata: it never touches the disk.
    try:
        original_name, extension = validate_filename(file.filename)
    except UploadError as exc:
        raise _http_error(exc) from exc

    # Batch metadata sent by the supplier outside the file (TR-06).
    batch_period = (batch_period or "").strip() or None
    product_type = (product_type or "").strip() or None

    # Optional user-confirmed column->field mapping that overrides auto-detection
    # (TR-07). Validated up front so a bad mapping fails before any persistence.
    manual_mapping = _parse_column_mapping(column_mapping)

    # Store the file, reading it in chunks: an oversized upload is cut off
    # while it is being copied, not after it is fully in memory.
    try:
        file.file.seek(0)
        stored_path = save_upload(file.file, extension)
    except UploadError as exc:
        raise _http_error(exc) from exc
    except Exception as exc:
        error = _internal_error(exc)
        raise error from exc

    # Create import record. `filename` holds the stored file name (not a
    # path); the server never sends the storage location to the client.
    import_record = models.Import(
        filename=stored_path.name,
        original_filename=original_name,
        total_records=0,
        user_id=current_user.id,
        status="processing",
        batch_period=batch_period,
        product_type=product_type,
    )
    db.add(import_record)
    db.commit()
    db.refresh(import_record)

    # Process file
    try:
        result = process_inventory_file(
            stored_path,
            import_record.id,
            db,
            batch_period=batch_period,
            product_type=product_type,
            column_mapping=manual_mapping,
            dispatched_by_id=current_user.id,
        )

        # Update import record
        import_record.total_records = result["total_records"]
        import_record.successful_imports = result["successful_imports"]
        import_record.failed_imports = result["failed_imports"]
        import_record.status = "completed"
        import_record.completed_at = datetime.now(UTC)

        db.commit()

        return {
            "import_id": import_record.id,
            "message": f"File processed successfully. {result['successful_imports']} units imported, {result['failed_imports']} failed.",
            "total_records": result["total_records"],
            "successful_imports": result["successful_imports"],
            "failed_imports": result["failed_imports"],
        }

    except UploadError as exc:
        _mark_failed(db, import_record, exc.user_message)
        raise _http_error(exc) from exc
    except Exception as exc:
        error = _internal_error(exc)
        _mark_failed(db, import_record, error.detail)
        raise error from exc


def process_inventory_file(
    file_path: Path,
    import_id: int,
    db: Session,
    batch_period: str | None = None,
    product_type: str | None = None,
    column_mapping: dict | None = None,
    dispatched_by_id: int | None = None,
):
    """Process an uploaded inventory file and import units.

    Uses the schema-tolerant parser (``parse_workbook``) so heterogeneous
    supplier layouts (English/Chinese headers, multiple sheets, junk columns,
    merged cells, numeric serials) resolve to the canonical frame/motor/color/
    model fields before persistence. A row is a unit when it has a frame OR a
    motor; per-row failures are logged and never abort the whole import (TR-04f).

    ``batch_period`` and ``product_type`` are the batch metadata captured at
    upload time and stamped onto every created unit (TR-06).

    ``column_mapping`` is an optional user-confirmed column->field mapping that
    overrides the automatic detection before rows are read (TR-07).

    Persistence is batched (TR-08): rows are validated in a single pass, then the
    valid units and their inbound transfers are inserted in one transaction
    (``add_all`` + single ``commit``) instead of committing per row. Invalid rows
    (duplicate identifiers in the DB or within the file) are recorded in
    ``ImportError`` with their row number and raw data, without aborting the
    valid rows. ``dispatched_by_id`` is the authenticated user that owns the
    inbound transfers (no longer hardcoded).

    Problems with the *file* are raised as typed errors (400/413/422) with a
    message for the user; anything unexpected is left to the caller, which
    turns it into a generic 500 with a request id.
    """
    filename = file_path.name
    try:
        result = parse_workbook(file_path, filename)
    except UploadError:
        raise
    except FILE_READ_ERRORS as exc:
        # The file itself is broken (not a valid xlsx/csv, bad encoding...):
        # that is something the user can fix, so it is a 422 with a message.
        raise UnreadableFileError(
            "No se pudo leer el archivo. Verifica que sea un Excel (.xlsx, .xls) "
            "o un CSV válido."
        ) from exc

    # Apply the user-confirmed mapping (if any) over the auto-detected one.
    if column_mapping:
        apply_manual_mapping(result, column_mapping)

    if not result.tables:
        raise ImportValidationError("El archivo no contiene filas de datos.")

    # At least one sheet must expose an identifier column, otherwise we cannot
    # tell units apart (e.g. a no-header file mapped only positionally).
    if not any(
        ("frame" in t.field_map or "motor" in t.field_map) for t in result.tables
    ):
        raise ImportValidationError(
            "No se encontró ninguna columna de identificador (chasis/frame o "
            "motor/engine). Revisa el mapeo de columnas del archivo."
        )

    # Get or create default location
    default_location = (
        db.query(models.Location)
        .filter(models.Location.name == "Almacén Principal")
        .first()
    )
    if not default_location:
        default_location = models.Location(
            name="Almacén Principal",
            address="Guadalajara, Jalisco Mexico",
        )
        db.add(default_location)
        db.commit()
        db.refresh(default_location)

    # --- Pass 1: turn every unit-candidate row into a normalized record. -----
    # No DB writes happen here; we only read (model equivalence lookups) and
    # collect what we need so the actual insert can be done in one batch.
    candidates: list[dict] = []
    row_number = 0
    for sheet_row in result.iter_rows():
        # Skip rows from sheets that never mapped an identifier column.
        if "frame" not in sheet_row.field_map and "motor" not in sheet_row.field_map:
            continue

        canonical = sheet_row.canonical()
        frame = canonical.get("frame", "") or ""
        motor = canonical.get("motor", "") or ""
        # A row with neither identifier is not a unit (blank/spacer row).
        if not frame and not motor:
            continue

        row_number += 1
        # Model falls back to the sheet name (suppliers often put the model
        # there) and then to a placeholder.
        manufacturer_model = _text_or_default(
            canonical.get("model"), sheet_row.sheet or DEFAULT_MODEL
        )
        # Translate the manufacturer model to the client's internal model when
        # an equivalence exists; otherwise keep the manufacturer name as-is so
        # the import never blocks (TR-05).
        model_name = (
            resolve_internal_model(db, manufacturer_model) or manufacturer_model
        )
        candidates.append(
            {
                "row_number": row_number,
                "sheet": sheet_row.sheet,
                "canonical": canonical,
                "engine_number": motor or None,
                "chassis_number": frame or None,
                "model": model_name,
                "brand": _text_or_default(canonical.get("brand"), DEFAULT_BRAND),
                "color": normalize_color(
                    _text_or_default(canonical.get("color"), DEFAULT_COLOR)
                ),
            }
        )

    total_records = len(candidates)

    # --- Duplicate detection: one query for existing identifiers in the DB. ---
    engine_values = [c["engine_number"] for c in candidates if c["engine_number"]]
    chassis_values = [c["chassis_number"] for c in candidates if c["chassis_number"]]
    existing_engines = (
        {
            e
            for (e,) in db.query(models.Unit.engine_number)
            .filter(models.Unit.engine_number.in_(engine_values))
            .all()
        }
        if engine_values
        else set()
    )
    existing_chassis = (
        {
            c
            for (c,) in db.query(models.Unit.chassis_number)
            .filter(models.Unit.chassis_number.in_(chassis_values))
            .all()
        }
        if chassis_values
        else set()
    )

    # --- Pass 2: validate each candidate and build the batch. ----------------
    seen_engines: set = set()
    seen_chassis: set = set()
    units: list[models.Unit] = []
    error_records: list[models.ImportError] = []

    for c in candidates:
        engine_number = c["engine_number"]
        chassis_number = c["chassis_number"]

        # Reject identifiers already in the DB or seen earlier in this same file.
        dup_message = None
        if engine_number is not None and (
            engine_number in existing_engines or engine_number in seen_engines
        ):
            dup_message = f"Unit with engine number {engine_number} already exists"
        elif chassis_number is not None and (
            chassis_number in existing_chassis or chassis_number in seen_chassis
        ):
            dup_message = f"Unit with chassis number {chassis_number} already exists"

        if dup_message:
            sheet_label = f"[{c['sheet']}] " if c["sheet"] else ""
            error_records.append(
                models.ImportError(
                    import_id=import_id,
                    row_number=c["row_number"],
                    error_message=f"{sheet_label}{dup_message}",
                    raw_data=json.dumps(c["canonical"], default=str),
                )
            )
            continue

        if engine_number is not None:
            seen_engines.add(engine_number)
        if chassis_number is not None:
            seen_chassis.add(chassis_number)

        units.append(
            models.Unit(
                engine_number=engine_number,
                chassis_number=chassis_number,
                model=c["model"],
                brand=c["brand"],
                color=c["color"],
                batch_period=batch_period,
                product_type=product_type,
                current_location_id=default_location.id,
                status=UnitStatus.AVAILABLE,
            )
        )

    # --- Persist the whole batch in a single transaction. --------------------
    # Valid units and their inbound transfers are inserted together; per-row
    # errors are written in the same commit. A failure here rolls everything
    # back and is surfaced to the caller (which marks the import as failed).
    try:
        db.add_all(units)
        db.flush()  # assign unit IDs without ending the transaction
        now = datetime.now(UTC)
        db.add_all(
            [
                models.Transfer(
                    unit_id=unit.id,
                    dispatched_by_id=dispatched_by_id,
                    destination_location_id=default_location.id,
                    status=TransferStatus.RECEIVED,
                    dispatched_at=now,
                    received_at=now,
                )
                for unit in units
            ]
        )
        db.add_all(error_records)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "total_records": total_records,
        "successful_imports": len(units),
        "failed_imports": len(error_records),
    }


# Cap how many invalid rows the preview reports so a wholly-broken file does
# not produce an unbounded payload.
_MAX_INVALID_PREVIEW_ROWS = 100


@router.post("/preview")
def preview_inventory_file(
    file: UploadFile = File(...),
    column_mapping: str | None = Form(None),
    current_user: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    """Preview an uploaded file for assisted mapping, without persisting anything.

    Returns, per sheet, the raw detected columns and the proposed column->field
    mapping; a flattened canonical preview; and a list of invalid rows (no
    identifier or duplicate frame/motor) so the user can fix issues before
    importing. An optional ``column_mapping`` (same JSON shape as ``/upload``)
    is applied so the user can preview the effect of a manual mapping (TR-07).

    Synchronous on purpose: pandas runs in FastAPI's threadpool instead of
    blocking the event loop.
    """
    try:
        original_name, _extension = validate_filename(file.filename)
    except UploadError as exc:
        raise _http_error(exc) from exc

    manual_mapping = _parse_column_mapping(column_mapping)

    try:
        # Read in chunks and stop as soon as the file is too big: an oversized
        # file is never loaded whole.
        file.file.seek(0)
        content = read_upload(file.file)
        result = parse_workbook(content, original_name)
    except UploadError as exc:
        raise _http_error(exc) from exc
    except Exception as exc:
        raise _internal_error(exc) from exc

    if manual_mapping:
        apply_manual_mapping(result, manual_mapping)

    # Per-sheet summary: raw columns + proposed mapping (column -> field|null).
    sheets = []
    detected_fields: set[str] = set()
    for table in result.tables:
        detected_fields.update(table.field_map.keys())
        field_by_column = {col: fld for fld, col in table.field_map.items()}
        sheets.append(
            {
                "sheet": table.sheet,
                "has_header": table.has_header,
                "columns": table.columns,
                # Proposed mapping in both directions for convenience.
                "column_mapping": {
                    col: field_by_column.get(col) for col in table.columns
                },
                "mapped_fields": table.field_map,
                "rows": len(table.rows),
            }
        )

    # Single pass over every row: build the bounded preview and flag invalid rows.
    preview_data: list[dict] = []
    invalid_rows: list[dict] = []
    invalid_count = 0
    seen_identifiers: set[str] = set()
    for index, sheet_row in enumerate(result.iter_rows(), start=1):
        canonical = sheet_row.canonical()
        frame = (canonical.get("frame") or "").strip()
        motor = (canonical.get("motor") or "").strip()

        reasons: list[str] = []
        if not frame and not motor:
            reasons.append("No identifier (frame/chassis or motor/engine) in row")
        else:
            for ident in (frame, motor):
                if ident and ident in seen_identifiers:
                    reasons.append(f"Duplicate identifier '{ident}' within the file")
            seen_identifiers.update(i for i in (frame, motor) if i)

        if reasons:
            invalid_count += 1
            if len(invalid_rows) < _MAX_INVALID_PREVIEW_ROWS:
                invalid_rows.append(
                    {
                        "sheet": sheet_row.sheet,
                        "row": index,
                        "reasons": reasons,
                        "data": {k: str(v) for k, v in canonical.items()},
                    }
                )
            continue

        if len(preview_data) < 10:
            preview_data.append({"sheet": sheet_row.sheet, **canonical})

    has_identifier = bool(detected_fields & {"frame", "motor"})
    return {
        "filename": original_name,
        "sheets": sheets,
        "detected_fields": sorted(detected_fields),
        "preview_data": preview_data,
        "invalid_rows": invalid_rows,
        "invalid_rows_count": invalid_count,
        "issues": [
            {"level": i.level, "message": i.message, "sheet": i.sheet}
            for i in result.issues
        ],
        "validation": {
            "is_valid": has_identifier,
            "message": (
                "File is ready for import"
                if has_identifier
                else "No identifier column (frame/chassis or motor/engine) detected"
            ),
        },
    }


@router.delete("/{import_id}")
def delete_import(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN])),
):
    import_record = (
        db.query(models.Import).filter(models.Import.id == import_id).first()
    )
    if not import_record:
        raise HTTPException(status_code=404, detail="Import record not found")

    # Delete associated errors
    db.query(models.ImportError).filter(
        models.ImportError.import_id == import_id
    ).delete()

    # Delete the stored file, but only if it still lives inside the storage
    # directory: a legacy row that points somewhere else is left alone.
    stored_path = resolve_stored_path(import_record.filename)
    if stored_path is not None and stored_path.is_file():
        try:
            stored_path.unlink()
        except OSError:
            logger.exception("Could not delete the stored file of the import")

    # Delete import record
    db.delete(import_record)
    db.commit()

    return {"message": "Import record deleted successfully"}
