
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.models import models, schemas
from app.schemas.unit import Unit, UnitCreate, UnitUpdate, UnitFilters
from app.models.models import UserRole
from app.services.auth_service import get_current_active_user, require_role
from app.services.unit_service import UnitService

router = APIRouter()

@router.get("/", response_model=List[Unit])
def get_units(
    filters: UnitFilters = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return UnitService.get_units(db, filters, skip, limit)

@router.post("/", response_model=Unit)
def create_unit(
    unit: UnitCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    return UnitService.create_unit(db, unit)

@router.get("/stats")
def get_unit_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return UnitService.get_stats(db)

@router.get("/{unit_id}", response_model=Unit)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return UnitService.get_unit_by_id(db, unit_id)

@router.put("/{unit_id}", response_model=Unit)
def update_unit(
    unit_id: int,
    unit_update: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    return UnitService.update_unit(db, unit_id, unit_update, current_user.id)

@router.delete("/{unit_id}")
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    return UnitService.delete_unit(db, unit_id)

@router.get("/{unit_id}/transfers", response_model=List[schemas.Transfer])
def get_unit_transfers(
    unit_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return UnitService.get_unit_transfers(db, unit_id, skip, limit)

@router.post("/{unit_id}/move")
def move_unit(
    unit_id: int,
    transfer: schemas.TransferCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    return UnitService.move_unit(db, unit_id, transfer, current_user.id)
