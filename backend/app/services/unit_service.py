
"""Unit management service."""

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.models import Unit, Transfer, UnitStatus
from app.schemas.unit import UnitCreate, UnitFilters, UnitUpdate
from app.models.schemas import TransferCreate
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

    @staticmethod
    def get_unit_by_id(db: Session, unit_id: int) -> Unit:
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")
        return unit

    @staticmethod
    def update_unit(db: Session, unit_id: int, unit_update: UnitUpdate, user_id: int) -> Unit:
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        update_data = unit_update.model_dump(exclude_unset=True)
        if "engine_number" in update_data or "chassis_number" in update_data:
            engine_check = update_data.get("engine_number", unit.engine_number)
            chassis_check = update_data.get("chassis_number", unit.chassis_number)
            existing = UnitRepository.get_by_engine_or_chassis_excluding(
                db, engine_check, chassis_check, unit_id
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Another unit with this engine number or chassis number already exists"
                )

        return UnitRepository.update_unit(db, unit, unit_update, user_id)

    @staticmethod
    def delete_unit(db: Session, unit_id: int) -> dict:
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        if unit.status == UnitStatus.IN_TRANSIT:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete unit in transit. The transit should be completed first."
            )

        UnitRepository.delete_unit(db, unit_id)
        return {"message": "Unit deleted successfully"}

    @staticmethod
    def get_stats(db: Session) -> dict:
        return UnitRepository.get_stats(db)

    @staticmethod
    def get_unit_transfers(db: Session, unit_id: int, skip: int, limit: int) -> list[Transfer]:
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")
        return UnitRepository.get_unit_transfers(db, unit_id, skip, limit)
