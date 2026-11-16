"""Unit management service."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Transfer, Unit, UnitStatus
from app.repositories.location_repository import LocationRepository
from app.repositories.unit_repository import UnitRepository
from app.schemas.unit import UnitCreate, UnitFilters, UnitUpdate


class UnitService:
    """Service for unit operations.

    A unit is a piece of inventory whose state is owned by the lifecycle:
    it changes through a transfer (dispatch, reception, cancellation) or
    through a sale. Editing a unit here only touches its descriptive
    fields; nothing in this module writes ``status``, ``sold_date`` or
    ``current_location_id``.
    """

    @staticmethod
    def get_units(
        db: Session, filters: UnitFilters, skip: int, limit: int
    ) -> list[Unit]:
        return UnitRepository.get_units(db, filters, skip, limit)

    @staticmethod
    def count_units(db: Session, filters: UnitFilters) -> int:
        return UnitRepository.count_units(db, filters)

    @staticmethod
    def create_unit(db: Session, unit_data: UnitCreate) -> Unit:
        if not LocationRepository.get_location(db, unit_data.current_location_id):
            raise HTTPException(status_code=404, detail="Location not found")

        existing = UnitRepository.get_by_engine_or_chassis(
            db, unit_data.engine_number, unit_data.chassis_number
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A unit with this engine number or chassis number already exists",
            )
        try:
            return UnitRepository.create_unit(db, unit_data)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @staticmethod
    def get_unit_by_id(db: Session, unit_id: int) -> Unit:
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")
        return unit

    @staticmethod
    def update_unit(db: Session, unit_id: int, unit_update: UnitUpdate) -> Unit:
        """Edit the descriptive fields of a unit.

        The state of the unit is not touched: it belongs to the transfers
        and to the sales.
        """
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
                    detail="Another unit with this engine number or chassis number already exists",
                )

        try:
            return UnitRepository.update_unit(db, unit, unit_update)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @staticmethod
    def delete_unit(db: Session, unit_id: int) -> dict:
        """Delete a unit that has no history.

        A unit with transfers is never deleted: the trail is what makes the
        inventory trustworthy, so the request is rejected with 409 and the
        transfers stay untouched.
        """
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        if unit.status == UnitStatus.IN_TRANSIT:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete unit in transit. The transit should be completed first.",
            )

        transfer_count = UnitRepository.count_transfers_for_unit(db, unit_id)
        if transfer_count:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot delete a unit with {transfer_count} transfer(s) in "
                    "its history: the traceability trail must be preserved"
                ),
            )

        UnitRepository.delete_unit(db, unit_id)
        return {"message": "Unit deleted successfully"}

    @staticmethod
    def get_stats(db: Session) -> dict:
        return UnitRepository.get_stats(db)

    @staticmethod
    def get_unit_transfers(
        db: Session, unit_id: int, skip: int, limit: int
    ) -> list[Transfer]:
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")
        return UnitRepository.get_unit_transfers(db, unit_id, skip, limit)
