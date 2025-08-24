
"""Shipment model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Shipment(Base):
    """Shipment model for tracking supplier deliveries."""
    
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_code = Column(String(50), nullable=False, unique=True, index=True)
    supplier_invoice = Column(String(100), nullable=False)
    imported_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    imported_by = relationship("User", back_populates="shipments")
    units = relationship("Unit", back_populates="shipment")
    
    def __repr__(self):
        return f"<Shipment(id={self.id}, batch_code='{self.batch_code}')>"
