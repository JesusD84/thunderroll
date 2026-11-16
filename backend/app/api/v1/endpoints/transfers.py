from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import User, UserRole
from app.schemas.transfer import (
    Transfer,
    TransferCreate,
    TransferFilters,
    TransferStats,
    TransferUpdate,
    UnitTransferRequest,
)
from app.services.auth_service import get_current_active_user, require_role
from app.services.transfer_service import TransferService

router = APIRouter()


@router.get("/stats", response_model=TransferStats)
def get_transfer_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    return TransferService.get_transfer_stats(db)


@router.get("/", response_model=list[Transfer])
def get_transfers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    filters: TransferFilters = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return TransferService.get_transfers(db, filters, skip, limit)


@router.post("/", response_model=Transfer)
def create_transfer(
    transfer: TransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])
    ),
):
    """Dispatch a unit.

    An Operator may only dispatch: the attribution of the dispatch (who sent
    it, when) is written by the server from the session, so a body that tries
    to set it is rejected with 422.
    """
    payload = transfer
    if current_user.role == UserRole.OPERATOR:
        payload = TransferService.restrict_create_for_operator(transfer, current_user)
    return TransferService.create_transfer(db, payload)


@router.post("/unit/{unit_id}")
def transfer_unit(
    unit_id: int,
    transfer: UnitTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])
    ),
):
    """Dispatch (or sell, when no destination) a single unit from its detail page."""
    return TransferService.transfer_unit_with_status_update(
        db, unit_id, transfer, current_user.id
    )


@router.get("/unit/{unit_id}/active", response_model=Transfer)
def get_active_transfer_for_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return TransferService.get_active_transfer_for_unit(db, unit_id)


@router.get("/{transfer_id}", response_model=Transfer)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return TransferService.get_transfer_by_id(db, transfer_id)


@router.put("/{transfer_id}", response_model=Transfer)
def update_transfer(
    transfer_id: int,
    transfer_update: TransferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])
    ),
):
    """Update a transfer.

    An Operator may only confirm the arrival: the dispatch record (who sent
    the unit, when, from where to where) must not be rewritten by the role
    that receives, so such a body is rejected with 422.
    """
    payload = transfer_update
    if current_user.role == UserRole.OPERATOR:
        payload = TransferService.restrict_update_for_operator(transfer_update)
    return TransferService.update_transfer(db, transfer_id, payload)


@router.delete("/{transfer_id}")
def delete_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    return TransferService.delete_transfer(db, transfer_id)
