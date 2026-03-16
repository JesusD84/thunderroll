
"""Unit management service."""

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.models import Unit
from app.schemas.unit import UnitCreate, UnitFilters
from app.repositories.unit_repository import UnitRepository


class UnitService:
    """Service for unit operations."""

    @staticmethod
    def get_units(db: Session, filters: UnitFilters, skip: int, limit: int) -> list[Unit]:
        return UnitRepository.get_units(db, filters, skip, limit)

    @staticmethod
    def create_unit(db: Session, unit_data: UnitCreate) -> Unit:
        existing = UnitRepository.get_by_engine_or_chassis(
            db, unit_data.engine_number, unit_data.chassis_number
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A unit with this engine number or chassis number already exists"
            )
        return UnitRepository.create_unit(db, unit_data)
