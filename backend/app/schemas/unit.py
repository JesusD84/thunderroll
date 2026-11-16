from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.models import UnitStatus
from app.schemas.location import Location


class UnitBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    engine_number: str | None = Field(None, max_length=100)
    chassis_number: str | None = Field(None, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    brand: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., min_length=1, max_length=100)
    current_location_id: int = Field(..., gt=0)
    status: UnitStatus = UnitStatus.WAREHOUSE_UNIDENTIFIED
    notes: str | None = None

    @field_validator("engine_number", "chassis_number", mode="before")
    @classmethod
    def normalize_optional_identifier(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = str(v).strip().upper()
        return value or None

    @field_validator("model", "brand", "color", mode="before")
    @classmethod
    def strip_and_upper(cls, v: str) -> str:
        return v.strip().upper()

class UnitCreate(UnitBase):
    pass

class UnitUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")

    engine_number: str | None = Field(None, max_length=100)
    chassis_number: str | None = Field(None, max_length=100)
    model: str | None = Field(None, min_length=1, max_length=100)
    brand: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, min_length=1, max_length=100)
    current_location_id: int | None = Field(None, gt=0)
    status: UnitStatus | None = None
    sold_date: datetime | None = None
    notes: str | None = None

    @field_validator("engine_number", "chassis_number", mode="before")
    @classmethod
    def normalize_optional_identifier_update(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = str(v).strip().upper()
        return value or None

    @field_validator("model", "brand", "color", mode="before")
    @classmethod
    def strip_and_upper(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v.strip().upper()

class UnitSell(BaseModel):
    notes: str | None = Field(None, max_length=500)


class UnitFilters(BaseModel):
    status: UnitStatus | None = None
    location_id: int | None = None
    search: str | None = None

class Unit(UnitBase):
    id: int
    sold_date: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    model: str | None = None
    brand: str | None = None
    color: str | None = None
    current_location: Location | None = None
    model_config = ConfigDict(from_attributes=True)
