
"""Location schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class LocationBase(BaseModel):
    """Base location schema."""
    name: str = Field(..., min_length=1, max_length=100)
    type: str | None = None
    active: bool = True


class LocationCreate(LocationBase):
    """Location creation schema."""
    pass


class LocationUpdate(BaseModel):
    """Location update schema."""
    name: str | None = Field(None, min_length=1, max_length=100)
    type: str | None = None
    active: bool | None = None


class Location(LocationBase):
    """Location response schema."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
