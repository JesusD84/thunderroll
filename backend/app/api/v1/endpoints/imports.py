
import os
import json
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole, UnitStatus, TransferStatus
from app.services.auth_service import get_current_active_user, require_role
from app.services.import_parser import excel_engine_for, parse_workbook
from app.services.model_equivalence_service import resolve_internal_model

router = APIRouter()

# Persistence defaults for descriptive fields the supplier may omit. The parser
# resolves frame/motor/color/model; brand is never present in supplier
# inventories and color/model can be blank, yet Unit requires them NOT NULL.
DEFAULT_BRAND = "Sin especificar"
DEFAULT_COLOR = "Sin especificar"
DEFAULT_MODEL = "Sin especificar"


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
):
    """Process an uploaded inventory file and import units.

    Uses the schema-tolerant parser (``parse_workbook``) so heterogeneous
    supplier layouts (English/Chinese headers, multiple sheets, junk columns,
    merged cells, numeric serials) resolve to the canonical frame/motor/color/
    model fields before persistence. A row is a unit when it has a frame OR a
    motor; per-row failures are logged and never abort the whole import (TR-04f).

    ``batch_period`` and ``product_type`` are the batch metadata captured at
    upload time and stamped onto every created unit (TR-06).
    """
    filename = os.path.basename(file_path)
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        result = parse_workbook(content, filename)
    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")

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

    total_records = 0
    successful_imports = 0
    failed_imports = 0
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
        total_records += 1
        try:
            chassis_number = frame or None
            engine_number = motor or None
            # Model falls back to the sheet name (suppliers often put the model
            # there) and then to a placeholder; brand is never supplied.
            manufacturer_model = _text_or_default(
                canonical.get("model"), sheet_row.sheet or DEFAULT_MODEL
            )
            # Translate the manufacturer model to the client's internal model when
            # an equivalence exists; otherwise keep the manufacturer name as-is so
            # the import never blocks (TR-05).
            model_name = resolve_internal_model(db, manufacturer_model) or manufacturer_model
            color_name = _text_or_default(canonical.get("color"), DEFAULT_COLOR)
            brand_name = DEFAULT_BRAND

            # Check for duplicates on the identifiers that are actually present.
            dup_conditions = []
            if engine_number is not None:
                dup_conditions.append(models.Unit.engine_number == engine_number)
            if chassis_number is not None:
                dup_conditions.append(models.Unit.chassis_number == chassis_number)
            existing_unit = (
                db.query(models.Unit).filter(or_(*dup_conditions)).first()
                if dup_conditions
                else None
            )
            if existing_unit:
                raise ValueError(
                    f"Unit with engine number {engine_number} or chassis number "
                    f"{chassis_number} already exists"
                )

            unit = models.Unit(
                engine_number=engine_number,
                chassis_number=chassis_number,
                model=model_name,
                brand=brand_name,
                color=color_name,
                batch_period=batch_period,
                product_type=product_type,
                current_location_id=default_location.id,
                status=UnitStatus.AVAILABLE,
            )
            db.add(unit)
            db.commit()
            db.refresh(unit)

            transfer = models.Transfer(
                unit_id=unit.id,
                dispatched_by_id=1,
                destination_location_id=default_location.id,
                status=TransferStatus.RECEIVED,
                dispatched_at=datetime.now(UTC),
                received_at=datetime.now(UTC),
            )
            db.add(transfer)
            db.commit()

            successful_imports += 1

        except Exception as e:
            # Roll back the failed unit/transfer so the session stays usable
            # for the remaining rows, then record the per-row error.
            db.rollback()
            failed_imports += 1
            sheet_label = f"[{sheet_row.sheet}] " if sheet_row.sheet else ""
            error_record = models.ImportError(
                import_id=import_id,
                row_number=row_number,
                error_message=f"{sheet_label}{str(e)}",
                raw_data=json.dumps(canonical, default=str),
            )
            db.add(error_record)
            db.commit()
            continue

    return {
        "total_records": total_records,
        "successful_imports": successful_imports,
        "failed_imports": failed_imports,
    }

@router.post("/preview")
async def preview_inventory_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    """Preview the first few rows of an uploaded file for validation"""
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only Excel (.xlsx, .xls) and CSV files are supported."
        )
    
    try:
        content = await file.read()
        result = parse_workbook(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    # Per-sheet mapping summary plus a flattened canonical preview.
    sheets = []
    detected_fields: set[str] = set()
    for table in result.tables:
        detected_fields.update(table.field_map.keys())
        sheets.append({
            "sheet": table.sheet,
            "has_header": table.has_header,
            "mapped_fields": table.field_map,
            "rows": len(table.rows),
        })

    preview_data = []
    for sheet_row in result.iter_rows():
        if len(preview_data) >= 10:
            break
        if "frame" not in sheet_row.field_map and "motor" not in sheet_row.field_map:
            continue
        canonical = sheet_row.canonical()
        if not (canonical.get("frame") or canonical.get("motor")):
            continue
        preview_data.append({"sheet": sheet_row.sheet, **canonical})

    has_identifier = bool(detected_fields & {"frame", "motor"})
    return {
        "filename": file.filename,
        "sheets": sheets,
        "detected_fields": sorted(detected_fields),
        "preview_data": preview_data,
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
