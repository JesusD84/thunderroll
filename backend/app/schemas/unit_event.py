
"""Unit event schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UnitEvent(BaseModel):
    """Unit event response schema."""
    id: int
    unit_id: UUID
    event_type: str
    before: dict | None = None
    after: dict | None = None
    user_id: int
    reason: str | None = None
    timestamp: datetime
    
    # Related objects
    user: dict | None = None
    
    class Config:
        from_attributes = True
