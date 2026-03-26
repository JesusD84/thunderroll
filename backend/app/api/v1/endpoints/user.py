from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import models
from app.schemas import User, UserCreate, UserUpdate
from app.services.auth_service import get_current_active_user
from app.services.user_service import UserService

router = APIRouter()

@router.post("/register", response_model=User)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    return UserService.register_user(db, user)


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
