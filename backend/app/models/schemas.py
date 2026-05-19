
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from app.models.models import UnitStatus, TransferStatus
from app.schemas.user import User

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# Location Schemas
class LocationBase(BaseModel):
    name: str
    address: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None

class Location(LocationBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Unit Schemas
class UnitBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    model: str
    brand: str
    color: str
    current_location_id: int
    status: UnitStatus = UnitStatus.WAREHOUSE_UNIDENTIFIED
    notes: Optional[str] = None

class UnitCreate(UnitBase):
    pass

class UnitUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    model: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    current_location_id: Optional[int] = None
    status: Optional[UnitStatus] = None
    sold_date: Optional[datetime] = None
    notes: Optional[str] = None

class Unit(UnitBase):
    id: int
    sold_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    current_location: Optional[Location] = None
    model_config = ConfigDict(from_attributes=True)

# Import Schemas
class ImportBase(BaseModel):
    filename: str
    original_filename: str
    total_records: int
    notes: Optional[str] = None

class ImportCreate(ImportBase):
    pass

class Import(ImportBase):
    id: int
    successful_imports: int
    failed_imports: int
    user_id: int
    status: str
    import_date: datetime
    completed_at: Optional[datetime] = None
    user: Optional[User] = None
    model_config = ConfigDict(from_attributes=True)

# File Upload Schema
class FileUploadResponse(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    upload_date: datetime
    file_path: str

# Pagination
class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_previous: bool
