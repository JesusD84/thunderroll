
"""Unit model."""

import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, BigInteger, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class UnitStatus(str, Enum):
    """Unit status enumeration following state machine."""
    EN_BODEGA_NO_IDENTIFICADA = "EN_BODEGA_NO_IDENTIFICADA"
    IDENTIFICADA_EN_TALLER = "IDENTIFICADA_EN_TALLER" 
    EN_TRANSITO_TALLER_SUCURSAL = "EN_TRANSITO_TALLER_SUCURSAL"
    EN_TRANSITO_SUCURSAL_SUCURSAL = "EN_TRANSITO_SUCURSAL_SUCURSAL"
    EN_SUCURSAL_DISPONIBLE = "EN_SUCURSAL_DISPONIBLE"
    RESERVADA = "RESERVADA"
    VENDIDA = "VENDIDA"


class Unit(Base):
    """Unit model for inventory items (scooters/motorcycles)."""
    
    __tablename__ = "units"
    
    # Primary key as UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Basic product information
    brand = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    color = Column(String(30), nullable=False)
    
    # Identification numbers - unique when not null
    engine_number = Column(BigInteger, unique=True, nullable=True, index=True)
    chassis_number = Column(String(20), unique=True, nullable=True, index=True)
    
    # Shipment information
    supplier_invoice = Column(String(100), nullable=False)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    
    # Status and location
    status = Column(SQLEnum(UnitStatus), nullable=False, default=UnitStatus.EN_BODEGA_NO_IDENTIFICADA)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    assigned_branch_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    shipment = relationship("Shipment", back_populates="units")
    location = relationship("Location", back_populates="units", foreign_keys=[location_id])
    assigned_branch = relationship("Location", back_populates="assigned_units", foreign_keys=[assigned_branch_id])
    last_updated_by = relationship("User", back_populates="units_updated", foreign_keys=[last_updated_by_id])
    events = relationship("UnitEvent", back_populates="unit", order_by="UnitEvent.timestamp.desc()")
    transfers = relationship("Transfer", back_populates="unit")
    sale = relationship("Sale", back_populates="unit", uselist=False)
    
    def __repr__(self):
        return f"<Unit(id={self.id}, brand='{self.brand}', model='{self.model}', status='{self.status}')>"
