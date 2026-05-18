
"""Location schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class LocationBase(BaseModel):
    """Base location schema."""
    name: str = Field(..., min_length=1, max_length=100)
    address: Optional[str] = None


class LocationCreate(LocationBase):
    """Location creation schema."""
    pass


class LocationUpdate(BaseModel):
    """Location update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = None


class Location(LocationBase):
    """Location response schema."""
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LocationFilters(BaseModel):
    """Location filter parameters."""
    name: Optional[str] = None
