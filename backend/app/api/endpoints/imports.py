
"""Import endpoints for Excel files."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_inventario
from app.schemas.shipment import ShipmentCreate
from app.services.import_excel import ImportService

router = APIRouter()


@router.post("/excel", response_model=Dict[str, Any])
async def import_excel(
    file: UploadFile = File(...),
    batch_code: str = Form(...),
    supplier_invoice: str = Form(...),
    dry_run: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_inventario)
):
    """
    Import units from Excel file.
    
    - **file**: Excel file from supplier with frame number, motor number, color columns
    - **batch_code**: Unique batch code for this shipment
    - **supplier_invoice**: Supplier invoice number
    - **dry_run**: If true, validate only without creating units
    """
    
    shipment_data = ShipmentCreate(
        batch_code=batch_code,
        supplier_invoice=supplier_invoice
    )
    
    result = await ImportService.import_excel(
        db=db,
        file=file,
        shipment_data=shipment_data,
        user_id=current_user.id,
        dry_run=dry_run
    )
    
    return result


@router.get("/{import_id}/errors")
async def get_import_errors(
    import_id: int,
    current_user = Depends(require_inventario)
):
    """Get import errors for a specific import (placeholder for future implementation)."""
    # This would be implemented if we stored import results in database
    # For now, errors are returned immediately in the import response
    return {"message": "Import errors are returned immediately in import response"}
