
import os
import json
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole, UnitStatus, TransferStatus
from app.services.auth_service import get_current_active_user, require_role
from app.services.import_parser import (
    CANONICAL_FIELDS,
    apply_manual_mapping,
    excel_engine_for,
    parse_workbook,
)
from app.services.model_equivalence_service import resolve_internal_model

router = APIRouter()

# Persistence defaults for descriptive fields the supplier may omit. The parser
# resolves frame/motor/color/model; brand is never present in supplier
# inventories and color/model can be blank, yet Unit requires them NOT NULL.
DEFAULT_BRAND = "Sin especificar"
DEFAULT_COLOR = "Sin especificar"
DEFAULT_MODEL = "Sin especificar"


def _parse_column_mapping(raw: Optional[str]) -> dict:
    """Parse the optional manual column->field mapping sent on the upload form.

    Expects a JSON object like ``{"NO": "model", "Color": "color"}`` mapping a
    source column name to a canonical field. Returns ``{}`` when absent. Raises a
    400 on malformed JSON, the wrong shape, or an unknown canonical field (TR-07).
    """
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="column_mapping must be valid JSON")
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


@router.get("/", response_model=List[schemas.Import])
def get_imports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    imports = db.query(models.Import).order_by(models.Import.import_date.desc()) \
                .offset(skip).limit(limit).all()
    return imports

@router.get("/{import_id}", response_model=schemas.Import)
def get_import(
    import_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    import_record = db.query(models.Import).filter(models.Import.id == import_id).first()
    if not import_record:
        raise HTTPException(status_code=404, detail="Import record not found")
    return import_record

@router.get("/{import_id}/errors")
def get_import_errors(
    import_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    errors = db.query(models.ImportError).filter(models.ImportError.import_id == import_id) \
               .offset(skip).limit(limit).all()
    return errors

@router.post("/upload")
async def upload_inventory_file(
    file: UploadFile = File(...),
    batch_period: Optional[str] = Form(None),
    product_type: Optional[str] = Form(None),
    column_mapping: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only Excel (.xlsx, .xls) and CSV files are supported."
        )

    # Batch metadata sent by the supplier outside the file (TR-06).
    batch_period = (batch_period or "").strip() or None
    product_type = (product_type or "").strip() or None

    # Optional user-confirmed column->field mapping that overrides auto-detection
    # (TR-07). Validated up front so a bad mapping fails before any persistence.
    manual_mapping = _parse_column_mapping(column_mapping)
    
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    
    # Save file
    file_path = f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Create import record
    import_record = models.Import(
        filename=file_path,
        original_filename=file.filename,
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
        result = await process_inventory_file(
            file_path,
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
            "failed_imports": result["failed_imports"]
        }
        
    except Exception as e:
        import_record.status = "failed"
        import_record.notes = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

async def process_inventory_file(
    file_path: str,
    import_id: int,
    db: Session,
    batch_period: Optional[str] = None,
    product_type: Optional[str] = None,
    column_mapping: Optional[dict] = None,
    dispatched_by_id: Optional[int] = None,
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
    """
    filename = os.path.basename(file_path)
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        result = parse_workbook(content, filename)
    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")

    # Apply the user-confirmed mapping (if any) over the auto-detected one.
    if column_mapping:
        apply_manual_mapping(result, column_mapping)

    if not result.tables:
        raise Exception("No data rows found in file")

    # At least one sheet must expose an identifier column, otherwise we cannot
    # tell units apart (e.g. a no-header file mapped only positionally).
    if not any(("frame" in t.field_map or "motor" in t.field_map) for t in result.tables):
        raise Exception(
            "No identifier columns found (expected a frame/chassis or motor/engine column)"
        )

    # Get or create default location
    default_location = db.query(models.Location).filter(models.Location.name == "Almacén Principal").first()
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
        # there) and then to a placeholder; brand is never supplied.
        manufacturer_model = _text_or_default(
            canonical.get("model"), sheet_row.sheet or DEFAULT_MODEL
        )
        # Translate the manufacturer model to the client's internal model when
        # an equivalence exists; otherwise keep the manufacturer name as-is so
        # the import never blocks (TR-05).
        model_name = resolve_internal_model(db, manufacturer_model) or manufacturer_model
        candidates.append({
            "row_number": row_number,
            "sheet": sheet_row.sheet,
            "canonical": canonical,
            "engine_number": motor or None,
            "chassis_number": frame or None,
            "model": model_name,
            "color": _text_or_default(canonical.get("color"), DEFAULT_COLOR),
        })

    total_records = len(candidates)

    # --- Duplicate detection: one query for existing identifiers in the DB. ---
    engine_values = [c["engine_number"] for c in candidates if c["engine_number"]]
    chassis_values = [c["chassis_number"] for c in candidates if c["chassis_number"]]
    existing_engines = {
        e for (e,) in db.query(models.Unit.engine_number)
        .filter(models.Unit.engine_number.in_(engine_values)).all()
    } if engine_values else set()
    existing_chassis = {
        c for (c,) in db.query(models.Unit.chassis_number)
        .filter(models.Unit.chassis_number.in_(chassis_values)).all()
    } if chassis_values else set()

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
            error_records.append(models.ImportError(
                import_id=import_id,
                row_number=c["row_number"],
                error_message=f"{sheet_label}{dup_message}",
                raw_data=json.dumps(c["canonical"], default=str),
            ))
            continue

        if engine_number is not None:
            seen_engines.add(engine_number)
        if chassis_number is not None:
            seen_chassis.add(chassis_number)

        units.append(models.Unit(
            engine_number=engine_number,
            chassis_number=chassis_number,
            model=c["model"],
            brand=DEFAULT_BRAND,
            color=c["color"],
            batch_period=batch_period,
            product_type=product_type,
            current_location_id=default_location.id,
            status=UnitStatus.AVAILABLE,
        ))

    # --- Persist the whole batch in a single transaction. --------------------
    # Valid units and their inbound transfers are inserted together; per-row
    # errors are written in the same commit. A failure here rolls everything
    # back and is surfaced to the caller (which marks the import as failed).
    try:
        db.add_all(units)
        db.flush()  # assign unit IDs without ending the transaction
        now = datetime.now(UTC)
        db.add_all([
            models.Transfer(
                unit_id=unit.id,
                dispatched_by_id=dispatched_by_id,
                destination_location_id=default_location.id,
                status=TransferStatus.RECEIVED,
                dispatched_at=now,
                received_at=now,
            )
            for unit in units
        ])
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
async def preview_inventory_file(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(None),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    """Preview an uploaded file for assisted mapping, without persisting anything.

    Returns, per sheet, the raw detected columns and the proposed column->field
    mapping; a flattened canonical preview; and a list of invalid rows (no
    identifier or duplicate frame/motor) so the user can fix issues before
    importing. An optional ``column_mapping`` (same JSON shape as ``/upload``)
    is applied so the user can preview the effect of a manual mapping (TR-07).
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only Excel (.xlsx, .xls) and CSV files are supported."
        )

    manual_mapping = _parse_column_mapping(column_mapping)

    try:
        content = await file.read()
        result = parse_workbook(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    if manual_mapping:
        apply_manual_mapping(result, manual_mapping)

    # Per-sheet summary: raw columns + proposed mapping (column -> field|null).
    sheets = []
    detected_fields: set[str] = set()
    for table in result.tables:
        detected_fields.update(table.field_map.keys())
        field_by_column = {col: fld for fld, col in table.field_map.items()}
        sheets.append({
            "sheet": table.sheet,
            "has_header": table.has_header,
            "columns": table.columns,
            # Proposed mapping in both directions for convenience.
            "column_mapping": {col: field_by_column.get(col) for col in table.columns},
            "mapped_fields": table.field_map,
            "rows": len(table.rows),
        })

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
                invalid_rows.append({
                    "sheet": sheet_row.sheet,
                    "row": index,
                    "reasons": reasons,
                    "data": {k: str(v) for k, v in canonical.items()},
                })
            continue

        if len(preview_data) < 10:
            preview_data.append({"sheet": sheet_row.sheet, **canonical})

    has_identifier = bool(detected_fields & {"frame", "motor"})
    return {
        "filename": file.filename,
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
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    import_record = db.query(models.Import).filter(models.Import.id == import_id).first()
    if not import_record:
        raise HTTPException(status_code=404, detail="Import record not found")
    
    # Delete associated errors
    db.query(models.ImportError).filter(models.ImportError.import_id == import_id).delete()
    
    # Delete file if exists
    if os.path.exists(import_record.filename):
        os.remove(import_record.filename)
    
    # Delete import record
    db.delete(import_record)
    db.commit()
    
    return {"message": "Import record deleted successfully"}
