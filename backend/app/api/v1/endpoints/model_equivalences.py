"""Admin CRUD for manufacturer->internal model equivalences (TR-05)."""

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import schemas
from app.models.models import UserRole, User
from app.services.auth_service import get_current_active_user, require_role
from app.services import model_equivalence_service as service

router = APIRouter()


@router.get("/", response_model=List[schemas.ModelEquivalence])
def list_equivalences(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_equivalences(db, skip=skip, limit=limit)


@router.get("/unmapped", response_model=List[str])
def list_unmapped_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Models currently in inventory that still have no equivalence."""
    return service.list_unmapped_models(db)


@router.post("/", response_model=schemas.ModelEquivalence, status_code=201)
def create_equivalence(
    payload: schemas.ModelEquivalenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER])),
):
    return service.create_equivalence(db, payload)


@router.get("/{equivalence_id}", response_model=schemas.ModelEquivalence)
def get_equivalence(
    equivalence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return service.get_equivalence(db, equivalence_id)


@router.put("/{equivalence_id}", response_model=schemas.ModelEquivalence)
def update_equivalence(
    equivalence_id: int,
    payload: schemas.ModelEquivalenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER])),
):
    return service.update_equivalence(db, equivalence_id, payload)


@router.delete("/{equivalence_id}")
def delete_equivalence(
    equivalence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    return service.delete_equivalence(db, equivalence_id)
