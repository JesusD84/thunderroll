
"""Common schemas for API responses."""

from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response schema."""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    
    
class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: str | None = None
    request_id: str | None = None


class SuccessResponse(BaseModel):
    """Success response schema."""
    message: str
    data: dict | None = None
