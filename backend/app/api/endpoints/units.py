
"""Unit management endpoints."""

from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_inventario, require_taller, get_current_user
from app.schemas.unit import Unit, UnitCreate, UnitUpdate, UnitFilter, UnitIdentification
from app.schemas.unit_event import UnitEvent
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.unit import UnitService
from app.models.location import LocationType
from app.models.unit import Unit as UnitModel
from sqlalchemy import select

router = APIRouter()


@router.post("", response_model=Unit)
async def create_unit(
    unit_data: UnitCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_inventario)
):
    """Create a new unit manually."""
    # Get bodega location for new units
    from app.models.location import Location
    result = await db.execute(
        select(Location).where(Location.type == LocationType.BODEGA)
    )
    bodega = result.scalar_one_or_none()
    
    if not bodega:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bodega location not found"
        )
    
    unit = await UnitService.create_unit(
        db=db,
        unit_data=unit_data,
        location_id=bodega.id,
        user_id=current_user.id
    )
    return unit


@router.get("", response_model=PaginatedResponse[Unit])
async def get_units(
    status: Optional[str] = Query(None),
    location_id: Optional[int] = Query(None),
    shipment_id: Optional[int] = Query(None),
    brand: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    engine_number: Optional[int] = Query(None),
    chassis_number: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get units with filtering and pagination."""
    # Convert status string to enum if provided
    unit_status = None
    if status:
        from app.models.unit import UnitStatus
        try:
            unit_status = UnitStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    filters = UnitFilter(
        status=unit_status,
        location_id=location_id,
        shipment_id=shipment_id,
        brand=brand,
        model=model,
        engine_number=engine_number,
        chassis_number=chassis_number,
        query=query
    )
    
    skip = (page - 1) * size
    units, total = await UnitService.get_units(db, filters, skip, size)
    
    pages = (total + size - 1) // size  # Ceiling division
    
    return PaginatedResponse(
        items=units,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/{unit_id}", response_model=Unit)
async def get_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get unit by ID with complete information."""
    unit = await UnitService.get_unit_by_id(db, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    return unit


@router.get("/{unit_id}/events", response_model=List[UnitEvent])
async def get_unit_events(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get unit event timeline for audit trail."""
    unit = await UnitService.get_unit_by_id(db, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )
    return unit.events


@router.patch("/{unit_id}", response_model=Unit)
async def update_unit(
    unit_id: UUID,
    unit_update: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_inventario)
):
    """Update unit information."""
    unit = await UnitService.update_unit(
        db=db,
        unit_id=unit_id,
        unit_update=unit_update,
        user_id=current_user.id
    )
    return unit


@router.post("/match-identification", response_model=Unit)
async def match_identification(
    identification: UnitIdentification,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_taller)
):
    """Match engine and chassis numbers to identify a unit in taller."""
    unit = await UnitService.match_identification(
        db=db,
        identification=identification,
        user_id=current_user.id
    )
    return unit
