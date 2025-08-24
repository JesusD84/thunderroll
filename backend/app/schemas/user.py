
"""User schemas."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """User update schema."""
    name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    role: UserRole | None = None
    password: str | None = Field(None, min_length=8, max_length=100)


class UserInDB(UserBase):
    """User schema for database operations."""
    id: int
    created_at: datetime
    last_login_at: datetime | None = None
    
    class Config:
        from_attributes = True


class User(UserInDB):
    """User response schema."""
    pass
