
"""User schemas."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from app.models.models import UserRole
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    role: UserRole
    

class UserCreate(UserBase):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    role: UserRole
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    """Admin edit payload (PUT /user/{user_id}).

    ``extra="forbid"``: the body may only carry the fields declared here, so
    nothing else can reach the setattr-based persistence layer.
    """

    model_config = ConfigDict(extra="forbid")

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    # Solo un ADMIN puede fijarla (reseteo de contraseña). La contraseña nunca
    # se escribe tal cual: el servicio guarda siempre el hash.
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class UserSelfUpdate(BaseModel):
    """Self-service edit payload (PUT /user/me).

    Only the fields a user may change on their own account are accepted:
    ``first_name``/``last_name`` and the account identifiers ``email``/
    ``username`` (the account owner is the one who can correct them).

    ``role`` and ``is_active`` are administrator-only and are deliberately
    absent here. ``extra="forbid"`` turns any attempt to set them - or to
    send a field that does not exist at all - into a 422, instead of letting
    it reach the setattr-based persistence layer.
    """

    model_config = ConfigDict(extra="forbid")

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def _reject_null_on_not_nullable_columns(self) -> "UserSelfUpdate":
        """A NOT NULL column may not be set to null.

        Without this, ``{"first_name": null}`` would reach the ORM and fail as
        an IntegrityError (500) instead of a validation error (422).
        """
        for field in ("email", "username", "first_name", "last_name"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class PasswordChange(BaseModel):
    """Cambio de contraseña propia: exige la actual para no dejar al usuario
    fuera de su cuenta si alguien más tiene su sesión."""

    current_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class UserFilters(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
