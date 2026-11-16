"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.models import UserRole


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

    email: EmailStr | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    # Solo un ADMIN puede fijarla (reseteo de contraseña). La contraseña nunca
    # se escribe tal cual: el servicio guarda siempre el hash.
    password: str | None = Field(None, min_length=8, max_length=100)


class UserSelfUpdate(BaseModel):
    """Self-service edit payload (PUT /user/me).

    Only the fields a user may change on their own account are accepted:
    ``first_name`` and ``last_name``.

    The account identifiers (``email``, ``username``) are administrator-only
    too: they are what the account signs in with, and correcting them
    invalidates the session (the JWT carries the username). ``role`` and
    ``is_active`` are administrator-only as well. ``extra="forbid"`` turns
    any attempt to set them - or to send a field that does not exist at all
    - into a 422, instead of letting it reach the setattr-based persistence
    layer.
    """

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def _reject_null_on_not_nullable_columns(self) -> "UserSelfUpdate":
        """A NOT NULL column may not be set to null.

        Without this, ``{"first_name": null}`` would reach the ORM and fail as
        an IntegrityError (500) instead of a validation error (422).
        """
        for field in ("first_name", "last_name"):
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
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class UserFilters(BaseModel):
    email: str | None = None
    username: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
