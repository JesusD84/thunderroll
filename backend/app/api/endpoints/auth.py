
"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.schemas.auth import Token, UserLogin
from app.schemas.user import User
from app.services.auth import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password to get access token."""
    user = await AuthService.authenticate_user(db, credentials)
    tokens = await AuthService.create_tokens(user)
    return tokens


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """Get current authenticated user information."""
    return current_user
