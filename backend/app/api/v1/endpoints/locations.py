
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.models.models import UserRole, User
from app.schemas.location import Location, LocationCreate, LocationFilters, LocationUpdate
from app.services.auth_service import get_current_active_user, require_role
from app.services.location_service import LocationService

router = APIRouter()

@router.get("/", response_model=List[Location])
def get_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    filters: LocationFilters = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return LocationService.get_locations(db, filters, skip, limit)

@router.post("/", response_model=Location)
def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    return LocationService.create_location(db, location)

@router.get("/{location_id}", response_model=Location)
def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return LocationService.get_location_by_id(db, location_id)

@router.put("/{location_id}", response_model=Location)
def update_location(
    location_id: int,
    location_update: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    return LocationService.update_location(db, location_id, location_update)

@router.delete("/{location_id}")
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    return LocationService.delete_location(db, location_id)