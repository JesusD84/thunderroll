from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole
from app.schemas.unit import Unit, UnitCreate, UnitFilters, UnitSell, UnitUpdate
from app.services.auth_service import get_current_active_user, require_role
from app.services.sale_service import SaleService
from app.services.unit_service import UnitService

router = APIRouter()


@router.get("/", response_model=list[Unit])
def get_units(
    response: Response,
    filters: UnitFilters = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    response.headers["X-Total-Count"] = str(UnitService.count_units(db, filters))
    return UnitService.get_units(db, filters, skip, limit)


@router.post("/", response_model=Unit)
def create_unit(
    unit: UnitCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    return UnitService.create_unit(db, unit)


@router.get("/stats")
def get_unit_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    return UnitService.get_stats(db)


@router.get("/{unit_id}", response_model=Unit)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    return UnitService.get_unit_by_id(db, unit_id)


@router.put("/{unit_id}", response_model=Unit)
def update_unit(
    unit_id: int,
    unit_update: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER])
    ),
):
    """Edit the descriptive fields of a unit.

    The state of a unit (status, sold_date, location) does not change here:
    it belongs to the transfers and to the sales.
    """
    return UnitService.update_unit(db, unit_id, unit_update)


@router.delete("/{unit_id}")
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN])),
):
    return UnitService.delete_unit(db, unit_id)


@router.get("/{unit_id}/transfers", response_model=list[schemas.Transfer])
def get_unit_transfers(
    unit_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    return UnitService.get_unit_transfers(db, unit_id, skip, limit)


@router.post("/{unit_id}/sell", response_model=Unit)
def sell_unit(
    unit_id: int,
    payload: UnitSell | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(
        require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])
    ),
):
    """Sell a unit.

    This is the only door to a sale: it stamps ``sold_date``, writes the
    record of the sale in the history and refuses a unit that is already
    sold or that is still on the road.
    """
    notes = payload.notes if payload else None
    return SaleService.sell_unit(db, unit_id, current_user.id, notes)
