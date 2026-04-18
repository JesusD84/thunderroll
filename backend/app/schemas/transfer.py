from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.models import TransferStatus


class TransferBase(BaseModel):
    unit_id: int = Field(..., gt=0)
    dispatched_by_id: Optional[int] = Field(None, gt=0)
    received_by_id: Optional[int] = Field(None, gt=0)
    origin_location_id: Optional[int] = Field(None, gt=0)
    destination_location_id: Optional[int] = Field(None, gt=0)
    status: TransferStatus = TransferStatus.PENDING
    dispatched_at: Optional[datetime] = None
    received_at: Optional[datetime] = None


class TransferCreate(TransferBase):
    pass


class TransferUpdate(BaseModel):
    unit_id: Optional[int] = Field(None, gt=0)
    dispatched_by_id: Optional[int] = Field(None, gt=0)
    received_by_id: Optional[int] = Field(None, gt=0)
    origin_location_id: Optional[int] = Field(None, gt=0)
    destination_location_id: Optional[int] = Field(None, gt=0)
    status: Optional[TransferStatus] = None
    dispatched_at: Optional[datetime] = None
    received_at: Optional[datetime] = None


class TransferFilters(BaseModel):
    unit_id: Optional[int] = None
    status: Optional[TransferStatus] = None
    origin_location_id: Optional[int] = None
    destination_location_id: Optional[int] = None
    dispatched_by_id: Optional[int] = None
    received_by_id: Optional[int] = None


class Transfer(TransferBase):
    id: int

    class Config:
        from_attributes = True


class TransferStats(BaseModel):
    total_transfers: int
    pending_transfers: int
    in_transit_transfers: int
    received_transfers: int
    cancelled: int
    recent_transfers: list[Transfer]
