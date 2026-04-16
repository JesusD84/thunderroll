from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import UserRole, User
from app.schemas.transfer import Transfer, TransferCreate, TransferFilters, TransferUpdate
from app.services.auth_service import get_current_active_user, require_role
from app.services.transfer_service import TransferService

router = APIRouter()


@router.get("/", response_model=List[Transfer])
def get_transfers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    filters: TransferFilters = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return TransferService.get_transfers(db, filters, skip, limit)


@router.post("/", response_model=Transfer)
def create_transfer(
    transfer: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    return TransferService.create_transfer(db, transfer)


@router.get("/{transfer_id}", response_model=Transfer)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return TransferService.get_transfer_by_id(db, transfer_id)


@router.put("/{transfer_id}", response_model=Transfer)
def update_transfer(
    transfer_id: int,
    transfer_update: TransferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    return TransferService.update_transfer(db, transfer_id, transfer_update)


@router.delete("/{transfer_id}")
def delete_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    return TransferService.delete_transfer(db, transfer_id)
