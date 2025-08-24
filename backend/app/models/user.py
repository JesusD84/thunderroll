
"""User model."""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "ADMIN"
    INVENTARIO = "INVENTARIO"
    TALLER = "TALLER"
    VENTAS = "VENTAS"


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    shipments = relationship("Shipment", back_populates="imported_by")
    unit_events = relationship("UnitEvent", back_populates="user")
    units_updated = relationship("Unit", back_populates="last_updated_by", foreign_keys="[Unit.last_updated_by_id]")
    transfers_created = relationship("Transfer", back_populates="created_by", foreign_keys="[Transfer.created_by_id]")
    transfers_received = relationship("Transfer", back_populates="received_by", foreign_keys="[Transfer.received_by_id]")
    sales = relationship("Sale", back_populates="sold_by")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
