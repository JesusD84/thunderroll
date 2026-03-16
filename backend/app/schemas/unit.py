from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.models import UnitStatus
from  app.models.schemas import Location

class UnitBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    engine_number: str = Field(..., min_length=1, max_length=100)
    chassis_number: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    brand: str = Field(..., min_length=1, max_length=100)
    color: str = Field(..., min_length=1, max_length=100)
    current_location_id: Optional[int] = Field(None, gt=0)
    status: UnitStatus = UnitStatus.AVAILABLE
    notes: Optional[str] = None

    @field_validator("engine_number", "chassis_number", "model", "brand", "color", mode="before")
    @classmethod
    def strip_and_upper(cls, v: str) -> str:
        return v.strip().upper()

class UnitCreate(UnitBase):
    pass

class UnitUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    engine_number: Optional[str] = Field(None, min_length=1, max_length=100)
    chassis_number: Optional[str] = Field(None, min_length=1, max_length=100)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    brand: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, min_length=1, max_length=100)
    current_location_id: Optional[int] = Field(None, gt=0)
    status: Optional[UnitStatus] = None
    sold_date: Optional[datetime] = None
    notes: Optional[str] = None

    @field_validator("engine_number", "chassis_number", "model", "brand", "color", mode="before")
    @classmethod
    def strip_and_upper(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip().upper()

class UnitFilters(BaseModel):
    status: Optional[UnitStatus] = None
    location_id: Optional[int] = None
    search: Optional[str] = None

class Unit(UnitBase):
    id: int
    sold_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model: Optional[str] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    current_location: Optional[Location] = None

    class Config:
        from_attributes = True