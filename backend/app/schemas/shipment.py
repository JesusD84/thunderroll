
"""Shipment schemas."""

from datetime import datetime
from pydantic import BaseModel, Field


class ShipmentBase(BaseModel):
    """Base shipment schema."""
    batch_code: str = Field(..., min_length=1, max_length=50)
    supplier_invoice: str = Field(..., min_length=1, max_length=100)


class ShipmentCreate(ShipmentBase):
    """Shipment creation schema."""
    pass


class Shipment(ShipmentBase):
    """Shipment response schema."""
    id: int
    imported_by_id: int
    imported_at: datetime
    
    class Config:
        from_attributes = True
