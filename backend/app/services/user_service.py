from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.user_repository import UserRepository
from app.services.auth_service import get_password_hash


class UserService:

    @staticmethod
    def create_user(db: Session, user_data: UserCreate, creator: User) -> User:
        # A Manager may only onboard Operator accounts; only an Admin can grant
        # Admin/Manager roles.
        if creator.role == UserRole.MANAGER and user_data.role != UserRole.OPERATOR:
            raise HTTPException(
                status_code=403,
                detail="Managers can only create users with the Operator role",
            )

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

    @staticmethod
    def _get_user_or_404(db: Session, user_id: int) -> User:
        db_user = UserRepository.get_user_by_id(db, user_id)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return db_user

    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate, admin: User) -> User:
        db_user = UserService._get_user_or_404(db, user_id)
        changes = user_update.model_dump(exclude_unset=True)

        # An admin cannot lock themselves out of the system.
        if db_user.id == admin.id:
            if changes.get("role", admin.role) != UserRole.ADMIN:
                raise HTTPException(status_code=400, detail="You cannot remove your own Admin role")
            if changes.get("is_active", True) is False:
                raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

        if "email" in changes and changes["email"] != db_user.email:
            if UserRepository.get_user_by_email(db, email=changes["email"]):
                raise HTTPException(status_code=400, detail="Email already registered")

        if "username" in changes and changes["username"] != db_user.username:
            if UserRepository.get_user_by_username(db, username=changes["username"]):
                raise HTTPException(status_code=400, detail="Username already registered")

        return UserRepository.update_user(db, db_user, user_update)

    @staticmethod
    def delete_user(db: Session, user_id: int, admin: User) -> None:
        db_user = UserService._get_user_or_404(db, user_id)

        if db_user.id == admin.id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account")

        # Transfers and imports keep a reference to the user for traceability.
        # Deleting them would break that history, so the account must be deactivated instead.
        if db_user.dispatched_transfers or db_user.received_transfers or db_user.imports:
            raise HTTPException(
                status_code=409,
                detail="User has transfers or imports on record; deactivate the account instead",
            )

        UserRepository.delete_user(db, db_user)
