
"""Location model."""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.base import Base


class LocationType(str, Enum):
    """Location type enumeration."""
    BODEGA = "BODEGA"
    TALLER = "TALLER"
    SUCURSAL = "SUCURSAL"


class Location(Base):
    """Location model for warehouses, workshops, and branches."""
    
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    type = Column(SQLEnum(LocationType), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    units = relationship("Unit", back_populates="location", foreign_keys="[Unit.location_id]")
    assigned_units = relationship("Unit", back_populates="assigned_branch", foreign_keys="[Unit.assigned_branch_id]")
    transfers_from = relationship("Transfer", back_populates="from_location", foreign_keys="[Transfer.from_location_id]")
    transfers_to = relationship("Transfer", back_populates="to_location", foreign_keys="[Transfer.to_location_id]")
    sales = relationship("Sale", back_populates="branch")
    
    def __repr__(self):
        return f"<Location(id={self.id}, name='{self.name}', type='{self.type}')>"
