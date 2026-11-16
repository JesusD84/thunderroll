from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import User, UserRole
from app.schemas.user import PasswordChange, UserCreate, UserSelfUpdate, UserUpdate
from app.repositories.user_repository import UserRepository
from app.services.auth_service import get_password_hash, verify_password


# The only attributes a user may change on their own account. ``role`` and
# ``is_active`` are administrator-only and never appear here: the self-update
# schema already forbids them, and this allowlist is the second line of
# defense in case that schema is ever widened by mistake.
SELF_UPDATE_FIELDS = frozenset({"email", "username", "first_name", "last_name"})


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
    def update_current_user(
        db: Session, current_user: User, user_update: UserSelfUpdate
    ) -> User:
        """Apply a self-service edit to the caller's own account.

        The payload is validated against ``UserSelfUpdate``, which forbids
        ``role``, ``is_active`` and any unknown field. On top of that, only
        the fields in ``SELF_UPDATE_FIELDS`` are ever written, so a future
        change to the schema cannot turn into a privilege escalation.
        """
        changes = {
            field: value
            for field, value in user_update.model_dump(exclude_unset=True).items()
            if field in SELF_UPDATE_FIELDS
        }

        # A NOT NULL column may not be nulled out: reject it as a bad request
        # instead of letting the ORM raise (which would surface as a 500).
        for field, value in changes.items():
            if value is None:
                raise HTTPException(status_code=422, detail=f"{field} cannot be null")

        # Same uniqueness rules as the admin edit flow, so a duplicate email
        # or username is a 400 and never a 500 from the unique index.
        if "email" in changes and changes["email"] != current_user.email:
            if UserRepository.get_user_by_email(db, email=changes["email"]):
                raise HTTPException(status_code=400, detail="Email already registered")

        if "username" in changes and changes["username"] != current_user.username:
            if UserRepository.get_user_by_username(db, username=changes["username"]):
                raise HTTPException(status_code=400, detail="Username already registered")

        try:
            return UserRepository.update_user(db, current_user, user_update)
        except IntegrityError as exc:
            # Lost the race against a concurrent registration of the same
            # email/username: the unique index rejected the write.
            db.rollback()
            raise HTTPException(
                status_code=400, detail="Email or username already registered"
            ) from exc

    @staticmethod
    def change_own_password(db: Session, current_user: User, payload: PasswordChange) -> None:
        """Change the caller's own password.

        The current password is required: a stolen session alone must not be
        enough to lock the legitimate user out of the account.
        """
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")

        if payload.current_password == payload.new_password:
            raise HTTPException(
                status_code=400,
                detail="La nueva contraseña debe ser distinta de la actual",
            )

        current_user.hashed_password = get_password_hash(payload.new_password)
        db.commit()
        db.refresh(current_user)

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
        # ``password`` is handled here, never written as a plain attribute:
        # the column is ``hashed_password``.
        new_password = changes.pop("password", None)

        # A NOT NULL column may not be nulled out: reject it as a bad request
        # instead of letting the ORM raise (which would surface as a 500).
        for field, value in changes.items():
            if value is None and field in ("email", "username", "first_name", "last_name"):
                raise HTTPException(status_code=422, detail=f"{field} cannot be null")

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

        if new_password is not None:
            db_user.hashed_password = get_password_hash(new_password)

        try:
            return UserRepository.update_user(db, db_user, user_update)
        except IntegrityError as exc:
            # The unique index on email/username rejected the write (a race
            # against a concurrent registration): 400, never a 500.
            db.rollback()
            raise HTTPException(
                status_code=400, detail="Email or username already registered"
            ) from exc

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
