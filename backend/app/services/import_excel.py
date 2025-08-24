
"""Excel import service."""

from datetime import datetime
from typing import List, Dict, Any
from io import BytesIO
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, UploadFile

from app.models.location import Location, LocationType
from app.models.shipment import Shipment
from app.models.unit import Unit
from app.models.unit_event import UnitEvent, EventType
from app.schemas.shipment import ShipmentCreate


class ImportService:
    """Service for importing Excel files from suppliers."""
    
    @staticmethod
    async def import_excel(
        db: AsyncSession,
        file: UploadFile,
        shipment_data: ShipmentCreate,
        user_id: int,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Import units from Excel file."""
        
        # Validate file
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be Excel format (.xlsx or .xls)"
            )
        
        # Read Excel file
        try:
            content = await file.read()
            df = pd.read_excel(BytesIO(content))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading Excel file: {str(e)}"
            )
        
        # Validate columns
        required_columns = ['frame number', 'motor number', 'color']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # Clean and validate data
        errors = []
        valid_rows = []
        
        for index, row in df.iterrows():
            row_errors = ImportService._validate_row(row, index + 2)  # +2 for header and 0-based index
            
            if row_errors:
                errors.extend(row_errors)
            else:
                valid_rows.append({
                    'chassis_number': str(row['frame number']).strip(),
                    'engine_number': int(row['motor number']),
                    'color': str(row['color']).strip().lower(),
                    'brand': 'Thunderrol',  # Default brand from specs
                    'model': 'TR-2025',     # Default model from specs
                })
        
        # Check for duplicates within file
        chassis_numbers = [row['chassis_number'] for row in valid_rows]
        engine_numbers = [row['engine_number'] for row in valid_rows]
        
        if len(set(chassis_numbers)) != len(chassis_numbers):
            errors.append("Duplicate chassis numbers found in file")
        
        if len(set(engine_numbers)) != len(engine_numbers):
            errors.append("Duplicate engine numbers found in file")
        
        # Check for existing units in database
        if valid_rows:
            await ImportService._check_existing_units(db, valid_rows, errors)
        
        # Return errors if any
        if errors:
            return {
                "success": False,
                "errors": errors,
                "valid_units": len(valid_rows),
                "total_rows": len(df)
            }
        
        # If dry run, return success without creating units
        if dry_run:
            return {
                "success": True,
                "message": "Dry run completed successfully",
                "units_to_import": len(valid_rows),
                "preview": valid_rows[:5]  # Preview first 5 units
            }
        
        # Create shipment
        shipment = await ImportService._create_shipment(db, shipment_data, user_id)
        
        # Get bodega location
        bodega_result = await db.execute(
            select(Location).where(Location.type == LocationType.BODEGA)
        )
        bodega = bodega_result.scalar_one_or_none()
        
        if not bodega:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bodega location not found"
            )
        
        # Create units
        created_units = []
        for row_data in valid_rows:
            unit = Unit(
                brand=row_data['brand'],
                model=row_data['model'],
                color=row_data['color'],
                chassis_number=row_data['chassis_number'],
                engine_number=row_data['engine_number'],
                supplier_invoice=shipment_data.supplier_invoice,
                shipment_id=shipment.id,
                location_id=bodega.id,
                last_updated_by_id=user_id
            )
            db.add(unit)
            created_units.append(unit)
        
        # Flush to get IDs
        await db.flush()
        
        # Create audit events
        for unit in created_units:
            event = UnitEvent(
                unit_id=unit.id,
                event_type=EventType.IMPORTED,
                after={
                    "brand": unit.brand,
                    "model": unit.model,
                    "color": unit.color,
                    "chassis_number": unit.chassis_number,
                    "engine_number": unit.engine_number,
                    "status": unit.status.value,
                    "location_id": unit.location_id
                },
                user_id=user_id,
                reason=f"Imported from Excel file: {file.filename}"
            )
            db.add(event)
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Successfully imported {len(created_units)} units",
            "shipment_id": shipment.id,
            "units_created": len(created_units)
        }
    
    @staticmethod
    def _validate_row(row: pd.Series, row_number: int) -> List[str]:
        """Validate a single row from the Excel file."""
        errors = []
        
        # Check frame number
        if pd.isna(row['frame number']):
            errors.append(f"Row {row_number}: Frame number is missing")
        else:
            frame_number = str(row['frame number']).strip()
            if not frame_number.startswith('HXY') or len(frame_number) != 12:
                errors.append(f"Row {row_number}: Invalid frame number format (should be HXY + 9 digits)")
        
        # Check motor number
        if pd.isna(row['motor number']):
            errors.append(f"Row {row_number}: Motor number is missing")
        else:
            try:
                motor_number = int(row['motor number'])
                if len(str(motor_number)) != 14:
                    errors.append(f"Row {row_number}: Motor number should be 14 digits")
            except (ValueError, TypeError):
                errors.append(f"Row {row_number}: Motor number must be numeric")
        
        # Check color
        if pd.isna(row['color']):
            errors.append(f"Row {row_number}: Color is missing")
        else:
            color = str(row['color']).strip().lower()
            valid_colors = ['red', 'black', 'green', 'pink', 'grey', 'blue', 'white', 'yellow', 'orange', 'purple']
            if color not in valid_colors:
                errors.append(f"Row {row_number}: Invalid color '{color}'. Valid colors: {valid_colors}")
        
        return errors
    
    @staticmethod
    async def _check_existing_units(db: AsyncSession, valid_rows: List[Dict], errors: List[str]):
        """Check for existing units with same chassis or engine numbers."""
        chassis_numbers = [row['chassis_number'] for row in valid_rows]
        engine_numbers = [row['engine_number'] for row in valid_rows]
        
        # Check chassis numbers
        chassis_result = await db.execute(
            select(Unit.chassis_number).where(Unit.chassis_number.in_(chassis_numbers))
        )
        existing_chassis = [row[0] for row in chassis_result.fetchall()]
        
        if existing_chassis:
            errors.append(f"Chassis numbers already exist in database: {existing_chassis}")
        
        # Check engine numbers
        engine_result = await db.execute(
            select(Unit.engine_number).where(Unit.engine_number.in_(engine_numbers))
        )
        existing_engines = [row[0] for row in engine_result.fetchall()]
        
        if existing_engines:
            errors.append(f"Engine numbers already exist in database: {existing_engines}")
    
    @staticmethod
    async def _create_shipment(
        db: AsyncSession, 
        shipment_data: ShipmentCreate, 
        user_id: int
    ) -> Shipment:
        """Create a new shipment record."""
        # Check if shipment already exists
        result = await db.execute(
            select(Shipment).where(Shipment.batch_code == shipment_data.batch_code)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shipment with batch code '{shipment_data.batch_code}' already exists"
            )
        
        shipment = Shipment(
            batch_code=shipment_data.batch_code,
            supplier_invoice=shipment_data.supplier_invoice,
            imported_by_id=user_id
        )
        
        db.add(shipment)
        await db.flush()
        
        return shipment
