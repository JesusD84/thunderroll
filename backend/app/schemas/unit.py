from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.models import UnitStatus
from  app.models.schemas import Location

class UnitBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    engine_number: str
    chassis_number: str
    model: str
    brand: str
    color: str
    current_location_id: Optional[int] = None
    status: UnitStatus = UnitStatus.AVAILABLE
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