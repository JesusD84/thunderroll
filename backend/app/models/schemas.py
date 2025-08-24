
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from app.models.models import UserRole, UnitStatus, MovementType

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    role: UserRole = UserRole.VIEWER

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# Brand Schemas
class BrandBase(BaseModel):
    name: str

class BrandCreate(BrandBase):
    pass

class Brand(BrandBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Model Schemas
class ModelBase(BaseModel):
    name: str
    brand_id: int
    year: Optional[int] = None
    engine_type: Optional[str] = None
    displacement: Optional[str] = None

class ModelCreate(ModelBase):
    pass

class Model(ModelBase):
    id: int
    is_active: bool
    created_at: datetime
    brand: Optional[Brand] = None

    class Config:
        from_attributes = True

# Color Schemas
class ColorBase(BaseModel):
    name: str
    hex_code: Optional[str] = None

class ColorCreate(ColorBase):
    pass

class Color(ColorBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Location Schemas
class LocationBase(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    manager_name: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    manager_name: Optional[str] = None
    is_active: Optional[bool] = None

class Location(LocationBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Unit Schemas
class UnitBase(BaseModel):
    engine_number: str
    chassis_number: str
    model_id: int
    color_id: int
    current_location_id: Optional[int] = None
    status: UnitStatus = UnitStatus.AVAILABLE
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None
    notes: Optional[str] = None

class UnitCreate(UnitBase):
    pass

class UnitUpdate(BaseModel):
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    model_id: Optional[int] = None
    color_id: Optional[int] = None
    current_location_id: Optional[int] = None
    status: Optional[UnitStatus] = None
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None
    sold_date: Optional[datetime] = None
    notes: Optional[str] = None

class Unit(UnitBase):
    id: int
    sold_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model: Optional[Model] = None
    color: Optional[Color] = None
    current_location: Optional[Location] = None

    class Config:
        from_attributes = True

# Movement Schemas
class MovementBase(BaseModel):
    unit_id: int
    movement_type: MovementType
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    quantity: int = 1
    price: Optional[float] = None
    notes: Optional[str] = None
    movement_date: Optional[datetime] = None

class MovementCreate(MovementBase):
    pass

class Movement(MovementBase):
    id: int
    user_id: int
    created_at: datetime
    unit: Optional[Unit] = None
    user: Optional[User] = None
    from_location: Optional[Location] = None
    to_location: Optional[Location] = None

    class Config:
        from_attributes = True

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

    class Config:
        from_attributes = True

# Transfer Schemas
class TransferBase(BaseModel):
    from_location_id: int
    to_location_id: int
    notes: Optional[str] = None
    transfer_date: Optional[datetime] = None

class TransferCreate(TransferBase):
    unit_ids: List[int]

class TransferUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    completed_date: Optional[datetime] = None

class Transfer(TransferBase):
    id: int
    user_id: int
    status: str
    total_units: int
    completed_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    from_location: Optional[Location] = None
    to_location: Optional[Location] = None
    user: Optional[User] = None

    class Config:
        from_attributes = True

# Setting Schemas
class SettingBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    data_type: str = "string"

class SettingCreate(SettingBase):
    pass

class SettingUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    data_type: Optional[str] = None
    is_active: Optional[bool] = None

class Setting(SettingBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Dashboard/Reports Schemas
class DashboardStats(BaseModel):
    total_units: int
    available_units: int
    sold_units: int
    in_transit_units: int
    total_locations: int
    recent_movements: List[Movement]
    inventory_by_location: List[dict]
    sales_by_month: List[dict]

class InventoryReport(BaseModel):
    units: List[Unit]
    total_units: int
    by_status: dict
    by_location: dict
    by_brand: dict
    by_model: dict

class MovementReport(BaseModel):
    movements: List[Movement]
    total_movements: int
    by_type: dict
    by_month: dict
    by_user: dict

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
