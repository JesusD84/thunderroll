
"""Catalog endpoints for reference data."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_db, get_current_user, require_admin
from app.schemas.location import Location, LocationCreate, LocationUpdate
from app.schemas.user import User
from app.models.location import Location as LocationModel
from app.models.user import User as UserModel

router = APIRouter()


@router.get("/locations", response_model=List[Location])
async def get_locations(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all active locations."""
    result = await db.execute(
        select(LocationModel).where(LocationModel.active == True).order_by(LocationModel.name)
    )
    locations = result.scalars().all()
    return list(locations)


@router.post("/locations", response_model=Location)
async def create_location(
    location_data: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Create a new location (ADMIN only)."""
    location = LocationModel(**location_data.model_dump())
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


@router.patch("/locations/{location_id}", response_model=Location)
async def update_location(
    location_id: int,
    location_update: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Update location (ADMIN only)."""
    result = await db.execute(
        select(LocationModel).where(LocationModel.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    # Update fields
    update_data = location_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)
    
    await db.commit()
    await db.refresh(location)
    return location


@router.get("/users", response_model=List[User])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Get all users (ADMIN only - limited by role)."""
    result = await db.execute(
        select(UserModel).order_by(UserModel.name)
    )
    users = result.scalars().all()
    return list(users)
