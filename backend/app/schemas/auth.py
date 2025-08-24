
"""Authentication schemas."""

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""
    user_id: int | None = None


class UserLogin(BaseModel):
    """User login request schema."""
    email: EmailStr
    password: str
