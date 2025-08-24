
"""Transfer model."""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class TransferStatus(str, Enum):
    """Transfer status enumeration."""
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class Transfer(Base):
    """Transfer model for unit movements between locations."""
    
    __tablename__ = "transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    
    # Location information
    from_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    to_location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    
    # Transfer timing
    eta = Column(DateTime, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Reception information
    received_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    received_at = Column(DateTime, nullable=True)
    
    # Status and notes
    status = Column(SQLEnum(TransferStatus), default=TransferStatus.PENDING, nullable=False)
    reason = Column(Text, nullable=True)
    
    # Relationships
    unit = relationship("Unit", back_populates="transfers")
    from_location = relationship("Location", back_populates="transfers_from", foreign_keys=[from_location_id])
    to_location = relationship("Location", back_populates="transfers_to", foreign_keys=[to_location_id])
    created_by = relationship("User", back_populates="transfers_created", foreign_keys=[created_by_id])
    received_by = relationship("User", back_populates="transfers_received", foreign_keys=[received_by_id])
    
    def __repr__(self):
        return f"<Transfer(id={self.id}, unit_id={self.unit_id}, status='{self.status}')>"
