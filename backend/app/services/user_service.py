from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.user_repository import UserRepository
from app.services.auth_service import get_password_hash


class UserService:

    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        # Check if email already exists
        db_user = UserRepository.get_user_by_email(db, email=user_data.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Check if username already exists
        db_user = UserRepository.get_user_by_username(db, username=user_data.username)
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        # Create new user with hashed password
        hashed_password = get_password_hash(user_data.password)
        return UserRepository.create_user(db, user_data, hashed_password)

    @staticmethod
    def update_current_user(db: Session, current_user: User, user_update: UserUpdate) -> User:
        return UserRepository.update_user(db, current_user, user_update)
