
"""Transfer schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.transfer import TransferStatus


class TransferBase(BaseModel):
    """Base transfer schema."""
    unit_id: UUID
    from_location_id: int
    to_location_id: int
    eta: datetime | None = None
    reason: str | None = None


class TransferCreate(TransferBase):
    """Transfer creation schema."""
    pass


class TransferReceive(BaseModel):
    """Transfer receive schema."""
    received_by_id: int


class Transfer(TransferBase):
    """Transfer response schema."""
    id: int
    created_by_id: int
    created_at: datetime
    received_by_id: int | None = None
    received_at: datetime | None = None
    status: TransferStatus
    
    # Related objects
    unit: dict | None = None
    from_location: dict | None = None
    to_location: dict | None = None
    created_by: dict | None = None
    received_by: dict | None = None
    
    class Config:
        from_attributes = True
