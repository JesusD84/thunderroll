from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import models
from app.models.models import UserRole
from app.schemas import User, UserCreate, UserUpdate
from app.services.auth_service import get_current_active_user, require_role
from app.services.user_service import UserService

router = APIRouter()

@router.get("/", response_model=List[User])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    return db.query(models.User).offset(skip).limit(limit).all()

@router.post("/", response_model=User, status_code=201)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    return UserService.create_user(db, user, current_user)


@router.get("/me", response_model=User)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=User)
async def update_users_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    return UserService.update_current_user(db, current_user, user_update)
