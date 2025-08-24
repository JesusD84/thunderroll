
import os
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole, UnitStatus, MovementType
from app.services.auth import get_current_active_user, require_role

router = APIRouter()

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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only Excel (.xlsx, .xls) and CSV files are supported."
        )
    
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
        status="processing"
    )
    db.add(import_record)
    db.commit()
    db.refresh(import_record)
    
    # Process file
    try:
        result = await process_inventory_file(file_path, import_record.id, db)
        
        # Update import record
        import_record.total_records = result["total_records"]
        import_record.successful_imports = result["successful_imports"]
        import_record.failed_imports = result["failed_imports"]
        import_record.status = "completed"
        import_record.completed_at = datetime.utcnow()
        
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

async def process_inventory_file(file_path: str, import_id: int, db: Session):
    """Process uploaded inventory file and import units"""
    
    # Read file
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")
    
    # Expected columns (flexible matching)
    column_mapping = {
        'brand': ['brand', 'marca', 'Brand', 'BRAND'],
        'model': ['model', 'modelo', 'Model', 'MODEL'],
        'color': ['color', 'colour', 'Color', 'COLOR'],
        'engine_number': ['engine_number', 'numero_motor', 'Engine Number', 'ENGINE_NUMBER', 'motor'],
        'chassis_number': ['chassis_number', 'numero_chasis', 'Chassis Number', 'CHASSIS_NUMBER', 'chasis', 'frame']
    }
    
    # Map columns
    mapped_columns = {}
    for key, possible_names in column_mapping.items():
        for col in df.columns:
            if col in possible_names:
                mapped_columns[key] = col
                break
    
    # Validate required columns
    required = ['brand', 'model', 'color', 'engine_number', 'chassis_number']
    missing_columns = [col for col in required if col not in mapped_columns]
    
    if missing_columns:
        raise Exception(f"Missing required columns: {', '.join(missing_columns)}")
    
    total_records = len(df)
    successful_imports = 0
    failed_imports = 0
    
    # Get or create default location
    default_location = db.query(models.Location).filter(models.Location.name == "Almacén Principal").first()
    if not default_location:
        default_location = models.Location(
            name="Almacén Principal",
            address="Guadalajara, Jalisco",
            city="Guadalajara",
            state="Jalisco",
            country="México"
        )
        db.add(default_location)
        db.commit()
        db.refresh(default_location)
    
    # Process each row
    for index, row in df.iterrows():
        try:
            # Extract data
            brand_name = str(row[mapped_columns['brand']]).strip()
            model_name = str(row[mapped_columns['model']]).strip()
            color_name = str(row[mapped_columns['color']]).strip()
            engine_number = str(row[mapped_columns['engine_number']]).strip()
            chassis_number = str(row[mapped_columns['chassis_number']]).strip()
            
            # Validate required fields
            if not all([brand_name, model_name, color_name, engine_number, chassis_number]):
                raise ValueError("Missing required data")
            
            # Check for duplicates
            existing_unit = db.query(models.Unit).filter(
                (models.Unit.engine_number == engine_number) |
                (models.Unit.chassis_number == chassis_number)
            ).first()
            
            if existing_unit:
                raise ValueError(f"Unit with engine number {engine_number} or chassis number {chassis_number} already exists")
            
            # Get or create brand
            brand = db.query(models.Brand).filter(models.Brand.name == brand_name).first()
            if not brand:
                brand = models.Brand(name=brand_name)
                db.add(brand)
                db.commit()
                db.refresh(brand)
            
            # Get or create model
            model = db.query(models.Model).filter(
                (models.Model.name == model_name) & 
                (models.Model.brand_id == brand.id)
            ).first()
            if not model:
                model = models.Model(name=model_name, brand_id=brand.id)
                db.add(model)
                db.commit()
                db.refresh(model)
            
            # Get or create color
            color = db.query(models.Color).filter(models.Color.name == color_name).first()
            if not color:
                color = models.Color(name=color_name)
                db.add(color)
                db.commit()
                db.refresh(color)
            
            # Create unit
            unit = models.Unit(
                engine_number=engine_number,
                chassis_number=chassis_number,
                model_id=model.id,
                color_id=color.id,
                current_location_id=default_location.id,
                status=UnitStatus.AVAILABLE
            )
            db.add(unit)
            db.commit()
            db.refresh(unit)
            
            # Create import movement
            movement = models.Movement(
                unit_id=unit.id,
                user_id=1,  # System user for imports
                movement_type=MovementType.IMPORT,
                to_location_id=default_location.id,
                notes=f"Imported from file: {import_id}"
            )
            db.add(movement)
            db.commit()
            
            successful_imports += 1
            
        except Exception as e:
            failed_imports += 1
            
            # Log error
            error_record = models.ImportError(
                import_id=import_id,
                row_number=index + 1,
                error_message=str(e),
                raw_data=json.dumps(row.to_dict(), default=str)
            )
            db.add(error_record)
            db.commit()
            
            continue
    
    return {
        "total_records": total_records,
        "successful_imports": successful_imports,
        "failed_imports": failed_imports
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
        # Read content
        content = await file.read()
        
        # Read first few rows
        if file.filename.endswith('.csv'):
            import io
            df = pd.read_csv(io.StringIO(content.decode('utf-8')), nrows=5)
        else:
            df = pd.read_excel(io.BytesIO(content), nrows=5)
        
        # Expected columns
        expected_columns = ['brand', 'model', 'color', 'engine_number', 'chassis_number']
        found_columns = []
        missing_columns = []
        
        column_mapping = {
            'brand': ['brand', 'marca', 'Brand', 'BRAND'],
            'model': ['model', 'modelo', 'Model', 'MODEL'],
            'color': ['color', 'colour', 'Color', 'COLOR'],
            'engine_number': ['engine_number', 'numero_motor', 'Engine Number', 'ENGINE_NUMBER', 'motor'],
            'chassis_number': ['chassis_number', 'numero_chasis', 'Chassis Number', 'CHASSIS_NUMBER', 'chasis', 'frame']
        }
        
        for key, possible_names in column_mapping.items():
            found = False
            for col in df.columns:
                if col in possible_names:
                    found_columns.append(f"{key} -> {col}")
                    found = True
                    break
            if not found:
                missing_columns.append(key)
        
        return {
            "filename": file.filename,
            "total_rows": len(df),
            "columns": df.columns.tolist(),
            "preview_data": df.to_dict('records'),
            "column_mapping": {
                "found": found_columns,
                "missing": missing_columns
            },
            "validation": {
                "is_valid": len(missing_columns) == 0,
                "message": "File is ready for import" if len(missing_columns) == 0 else f"Missing columns: {', '.join(missing_columns)}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

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
