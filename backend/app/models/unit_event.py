
"""Unit event model for audit trail."""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class EventType(str, Enum):
    """Event type enumeration for audit trail."""
    CREATED = "CREATED"
    IMPORTED = "IMPORTED"
    IDENTIFIED = "IDENTIFIED"
    TRANSFER_INITIATED = "TRANSFER_INITIATED"
    TRANSFER_RECEIVED = "TRANSFER_RECEIVED"
    STATUS_CHANGED = "STATUS_CHANGED"
    SOLD = "SOLD"
    ADJUSTED = "ADJUSTED"
    NOTE_ADDED = "NOTE_ADDED"


class UnitEvent(Base):
    """Unit event model for complete audit trail."""
    
    __tablename__ = "unit_events"
    
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    event_type = Column(SQLEnum(EventType), nullable=False)
    
    # State snapshots
    before = Column(JSONB, nullable=True)  # Previous state
    after = Column(JSONB, nullable=True)   # New state
    
    # Metadata
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    unit = relationship("Unit", back_populates="events")
    user = relationship("User", back_populates="unit_events")
    
    def __repr__(self):
        return f"<UnitEvent(id={self.id}, unit_id={self.unit_id}, event_type='{self.event_type}')>"
