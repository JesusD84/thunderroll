
"""Unit schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.unit import UnitStatus


class UnitBase(BaseModel):
    """Base unit schema."""
    brand: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., min_length=1, max_length=30)
    supplier_invoice: str = Field(..., min_length=1, max_length=100)


class UnitCreate(UnitBase):
    """Unit creation schema."""
    shipment_id: int
    notes: str | None = None


class UnitUpdate(BaseModel):
    """Unit update schema."""
    brand: str | None = Field(None, min_length=1, max_length=50)
    model: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, min_length=1, max_length=30)
    engine_number: int | None = None
    chassis_number: str | None = Field(None, min_length=1, max_length=20)
    notes: str | None = None
    assigned_branch_id: int | None = None


class UnitFilter(BaseModel):
    """Unit filtering schema."""
    status: UnitStatus | None = None
    location_id: int | None = None
    shipment_id: int | None = None
    brand: str | None = None
    model: str | None = None
    engine_number: int | None = None
    chassis_number: str | None = None
    query: str | None = None  # General search query
    
    
class UnitIdentification(BaseModel):
    """Unit identification matching schema."""
    engine_number: int = Field(..., description="Engine number to match")
    chassis_number: str = Field(..., min_length=1, max_length=20, description="Chassis number to match")
    shipment_id: int | None = Field(None, description="Optional shipment to search within")


class Unit(UnitBase):
    """Unit response schema."""
    id: UUID
    engine_number: int | None = None
    chassis_number: str | None = None
    shipment_id: int
    status: UnitStatus
    location_id: int
    assigned_branch_id: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    last_updated_by_id: int
    
    # Related objects
    location: dict | None = None
    assigned_branch: dict | None = None
    shipment: dict | None = None
    last_updated_by: dict | None = None
    
    class Config:
        from_attributes = True
