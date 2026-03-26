
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"

class UnitStatus(str, enum.Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    IN_TRANSIT = "in_transit"

class TransferType(str, enum.Enum):
    IMPORT = "import"
    SALE = "sale"
    TRANSFER = "transfer"
    RETURN = "return"
    DAMAGED = "damaged"
    MAINTENANCE = "maintenance"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    transfers = relationship("Transfer", back_populates="user")
    imports = relationship("Import", back_populates="user")

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    units = relationship("Unit", back_populates="current_location")
    transfers_from = relationship("Transfer", foreign_keys="Transfer.from_location_id", back_populates="from_location")
    transfers_to = relationship("Transfer", foreign_keys="Transfer.to_location_id", back_populates="to_location")

class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    engine_number = Column(String(100), unique=True, nullable=False, index=True)
    chassis_number = Column(String(100), unique=True, nullable=False, index=True)
    model = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=False)
    color = Column(String(100), nullable=False)
    current_location_id = Column(Integer, ForeignKey("locations.id"))
    status = Column(Enum(UnitStatus), nullable=False, default=UnitStatus.AVAILABLE)
    sold_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    current_location = relationship("Location", back_populates="units")
    transfers = relationship("Transfer", back_populates="unit")

class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transfer_type = Column(Enum(TransferType), nullable=False)
    from_location_id = Column(Integer, ForeignKey("locations.id"))
    to_location_id = Column(Integer, ForeignKey("locations.id"))
    quantity = Column(Integer, default=1)
    notes = Column(Text)
    Transfer_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    unit = relationship("Unit", back_populates="transfers")
    user = relationship("User", back_populates="transfers")
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])

class Import(Base):
    __tablename__ = "imports"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    total_records = Column(Integer, nullable=False)
    successful_imports = Column(Integer, default=0)
    failed_imports = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="processing")  # processing, completed, failed
    notes = Column(Text)
    import_date = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="imports")
    import_errors = relationship("ImportError", back_populates="import_record")

class ImportError(Base):
    __tablename__ = "import_errors"

    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("imports.id"), nullable=False)
    row_number = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=False)
    raw_data = Column(Text)  # JSON string of the row data
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    import_record = relationship("Import", back_populates="import_errors")