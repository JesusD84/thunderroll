"""Location schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationBase(BaseModel):
    """Base location schema."""

    name: str = Field(..., min_length=1, max_length=100)
    address: str | None = None


class LocationCreate(LocationBase):
    """Location creation schema."""

    pass


class LocationUpdate(BaseModel):
    """Location update schema.

    ``extra="forbid"``: only the fields declared here are accepted.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=100)
    address: str | None = None


class Location(LocationBase):
    """Location response schema."""

    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LocationFilters(BaseModel):
    """Location filter parameters."""

    name: str | None = None
