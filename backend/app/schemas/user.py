
"""User schemas."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
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
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    # Solo un ADMIN puede fijarla (reseteo de contraseña). La contraseña nunca
    # se escribe tal cual: el servicio guarda siempre el hash.
    password: Optional[str] = Field(None, min_length=8, max_length=100)


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