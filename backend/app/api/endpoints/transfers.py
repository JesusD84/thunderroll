
"""Transfer management endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_taller, require_inventario
from app.schemas.transfer import Transfer, TransferCreate, TransferReceive
from app.services.transfer import TransferService
from app.models.transfer import TransferStatus

router = APIRouter()


@router.post("", response_model=Transfer)
async def create_transfer(
    transfer_data: TransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_inventario)
):
    """Create a new transfer between locations."""
    transfer = await TransferService.create_transfer(
        db=db,
        transfer_data=transfer_data,
        user_id=current_user.id
    )
    return transfer


@router.get("", response_model=List[Transfer])
async def get_transfers(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_inventario)
):
    """Get transfers with optional status filtering."""
    
    # Convert status string to enum if provided
    transfer_status = None
    if status:
        try:
            transfer_status = TransferStatus(status)
        except ValueError:
            from fastapi import HTTPException, status as http_status
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    skip = (page - 1) * size
    transfers = await TransferService.get_transfers(
        db=db,
        status=transfer_status,
        skip=skip,
        limit=size
    )
    
    return transfers


@router.post("/{transfer_id}/receive", response_model=Transfer)
async def receive_transfer(
    transfer_id: int,
    receive_data: TransferReceive,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_inventario)
):
    """Receive a transfer at destination location."""
    transfer = await TransferService.receive_transfer(
        db=db,
        transfer_id=transfer_id,
        receive_data=receive_data
    )
    return transfer
