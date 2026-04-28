
"""Unit management service."""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, UTC

from app.models.models import Unit, Transfer, UnitStatus, TransferStatus
from app.schemas.unit import UnitCreate, UnitFilters, UnitUpdate
from app.models.schemas import TransferCreate
from app.repositories.unit_repository import UnitRepository
from app.services.transfer_service import TransferService


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

        old_location_id = unit.current_location_id
        old_status = unit.status

        updated_unit = UnitRepository.update_unit(db, unit, unit_update)

        if "current_location_id" in update_data and update_data["current_location_id"] != old_location_id:
            TransferService.create_unit_transfer_record(
                db=db,
                unit_id=unit.id,
                user_id=user_id,
                origin_location_id=old_location_id,
                destination_location_id=update_data["current_location_id"],
                status=TransferStatus.IN_TRANSIT,
                dispatched_at=datetime.now(UTC),
            )

        if "status" in update_data and update_data["status"] != old_status:
            transfer_status = TransferStatus.RECEIVED if update_data["status"] == UnitStatus.SOLD else TransferStatus.PENDING
            TransferService.create_unit_transfer_record(
                db=db,
                unit_id=unit.id,
                user_id=user_id,
                status=transfer_status,
                received_at=datetime.now(UTC) if transfer_status == TransferStatus.RECEIVED else None,
            )

        return updated_unit

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

    @staticmethod
    def transfer_unit(db: Session, unit_id: int, transfer_data: TransferCreate, user_id: int) -> Unit:
        return TransferService.transfer_unit_with_status_update(db, unit_id, transfer_data, user_id)

    @staticmethod
    def get_active_transfer(db: Session, unit_id: int) -> Transfer:
        return TransferService.get_active_transfer_for_unit(db, unit_id)
