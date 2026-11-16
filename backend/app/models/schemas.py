from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import TransferStatus, UnitStatus
from app.schemas.user import User


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Location Schemas
class LocationBase(BaseModel):
    name: str
    address: str | None = None


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    address: str | None = None


class Location(LocationBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Unit Schemas
class UnitBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    engine_number: str | None = None
    chassis_number: str | None = None
    model: str
    brand: str
    color: str
    current_location_id: int
    status: UnitStatus = UnitStatus.WAREHOUSE_UNIDENTIFIED
    notes: str | None = None


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")

    engine_number: str | None = None
    chassis_number: str | None = None
    model: str | None = None
    brand: str | None = None
    color: str | None = None
    current_location_id: int | None = None
    status: UnitStatus | None = None
    sold_date: datetime | None = None
    notes: str | None = None


class Unit(UnitBase):
    id: int
    sold_date: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    model: str | None = None
    brand: str | None = None
    color: str | None = None
    batch_period: str | None = None
    product_type: str | None = None
    current_location: Location | None = None
    model_config = ConfigDict(from_attributes=True)


# Transfer Schemas
class TransferBase(BaseModel):
    unit_id: int
    dispatched_by_id: int | None = None
    received_by_id: int | None = None
    origin_location_id: int | None = None
    destination_location_id: int | None = None
    status: TransferStatus = TransferStatus.PENDING
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


class TransferCreate(TransferBase):
    model_config = ConfigDict(extra="forbid")


class Transfer(TransferBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# Import Schemas
class ImportBase(BaseModel):
    filename: str
    original_filename: str
    total_records: int
    notes: str | None = None


class ImportCreate(ImportBase):
    pass


class Import(ImportBase):
    id: int
    successful_imports: int
    failed_imports: int
    user_id: int
    status: str
    batch_period: str | None = None
    product_type: str | None = None
    import_date: datetime
    completed_at: datetime | None = None
    user: User | None = None
    model_config = ConfigDict(from_attributes=True)


# Model Equivalence Schemas (manufacturer model -> internal model)
class ModelEquivalenceBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    manufacturer_model: str
    internal_model: str
    notes: str | None = None


class ModelEquivalenceCreate(ModelEquivalenceBase):
    pass


class ModelEquivalenceUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")

    manufacturer_model: str | None = None
    internal_model: str | None = None
    notes: str | None = None


class ModelEquivalence(ModelEquivalenceBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
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
    items: list[dict]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_previous: bool
