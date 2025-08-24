
"""FastAPI dependencies."""

from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import verify_token
from app.db.session import async_session
from app.models.user import User
from app.models.user import UserRole


# HTTP Bearer for JWT tokens
security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    # Verify token
    payload = verify_token(credentials.credentials)
    
    # Extract user ID from token
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    # For now, all users are considered active
    # Add is_active field to User model if needed
    return current_user


def require_role(*allowed_roles: UserRole):
    """Dependency factory to require specific user roles."""
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    
    return role_checker


# Role-specific dependencies
require_admin = require_role(UserRole.ADMIN)
require_inventario = require_role(UserRole.ADMIN, UserRole.INVENTARIO)
require_taller = require_role(UserRole.ADMIN, UserRole.INVENTARIO, UserRole.TALLER)
require_ventas = require_role(UserRole.ADMIN, UserRole.INVENTARIO, UserRole.VENTAS)
