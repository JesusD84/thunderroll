
"""Sale schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class SaleBase(BaseModel):
    """Base sale schema."""
    receipt: str = Field(..., min_length=1, max_length=100)
    branch_id: int
    customer_name: str | None = Field(None, max_length=200)


class SaleCreate(SaleBase):
    """Sale creation schema."""
    unit_id: UUID
    sold_by_id: int
    sold_at: datetime | None = None


class Sale(SaleBase):
    """Sale response schema."""
    id: int
    unit_id: UUID
    sold_by_id: int
    sold_at: datetime
    
    # Related objects
    unit: dict | None = None
    sold_by: dict | None = None
    branch: dict | None = None
    
    class Config:
        from_attributes = True
