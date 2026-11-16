from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.models import User
from app.schemas.user import UserCreate, UserUpdate


# Attributes that must never be written through the generic setattr loop:
# the primary key and the password hash. Passwords are hashed and assigned
# explicitly by the service, and ``id`` is not something a payload may move.
PROTECTED_FIELDS = frozenset({"id", "hashed_password"})


class UserRepository:

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User | None:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def create_user(db: Session, user_data: UserCreate, hashed_password: str) -> User:
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_user(db: Session, db_user: User, user_update: BaseModel) -> User:
        update_data = user_update.model_dump(exclude_unset=True)
        # ``password`` is never a column: it is hashed by the service before
        # reaching this point. Setting it here would shadow a non-mapped
        # attribute instead of updating ``hashed_password``.
        update_data.pop("password", None)
        # Only real columns are written, and never the primary key or the
        # password hash: this loop must not be able to reach an attribute the
        # caller did not intend to change, whatever the schema allows.
        writable = {column.name for column in User.__table__.columns} - PROTECTED_FIELDS
        for field, value in update_data.items():
            if field not in writable:
                continue
            setattr(db_user, field, value)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def delete_user(db: Session, db_user: User) -> None:
        db.delete(db_user)
        db.commit()
