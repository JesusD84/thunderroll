
"""Sale model."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Sale(Base):
    """Sale model for tracking sold units."""
    
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False, unique=True)
    receipt = Column(String(100), nullable=False, unique=True)
    
    # Sale information
    sold_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    sold_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Customer information (optional)
    customer_name = Column(String(200), nullable=True)
    
    # Relationships
    unit = relationship("Unit", back_populates="sale")
    sold_by = relationship("User", back_populates="sales")
    branch = relationship("Location", back_populates="sales")
    
    def __repr__(self):
        return f"<Sale(id={self.id}, unit_id={self.unit_id}, receipt='{self.receipt}')>"
