
"""User schemas."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
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
    role: UserRole = UserRole.VIEWER
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserFilters(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None