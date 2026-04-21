from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, func
from datetime import datetime, UTC
from app.models.models import Unit, Transfer, TransferStatus, UnitStatus, Location
from app.schemas.unit import UnitCreate, UnitFilters, UnitUpdate


class UnitRepository:

    @staticmethod
    def get_units(db: Session, filters: UnitFilters, skip: int, limit: int) -> list[Unit]:
        query = db.query(Unit).options(selectinload(Unit.current_location))

        if filters.status:
            query = query.filter(Unit.status == filters.status)

        if filters.location_id:
            query = query.filter(Unit.current_location_id == filters.location_id)

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                Unit.engine_number.ilike(search_term) |
                Unit.chassis_number.ilike(search_term) |
                Unit.model.ilike(search_term) |
                Unit.brand.ilike(search_term)
            )

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_unit(db: Session, unit_id: int) -> Unit | None:
        return (
            db.query(Unit)
            .options(selectinload(Unit.current_location))
            .filter(Unit.id == unit_id)
            .one_or_none()
        )

    @staticmethod
    def get_by_engine_or_chassis(db: Session, engine_number: str, chassis_number: str) -> Unit | None:
        return (
            db.query(Unit)
            .filter(
                (Unit.engine_number == engine_number) |
                (Unit.chassis_number == chassis_number)
            )
            .first()
        )

    @staticmethod
    def get_by_engine_or_chassis_excluding(
        db: Session, engine_number: str, chassis_number: str, exclude_id: int
    ) -> Unit | None:
        return (
            db.query(Unit)
            .filter(
                and_(
                    Unit.id != exclude_id,
                    or_(
                        Unit.engine_number == engine_number,
                        Unit.chassis_number == chassis_number
                    )
                )
            )
            .first()
        )

    @staticmethod
    def create_unit(db: Session, unit_data: UnitCreate) -> Unit:
        unit = Unit(**unit_data.model_dump())
        db.add(unit)
        db.commit()
        db.refresh(unit)
        return UnitRepository.get_unit(db, unit.id)

    @staticmethod
    def update_unit(db: Session, unit: Unit, unit_update: UnitUpdate, user_id: int) -> Unit:
        update_data = unit_update.model_dump(exclude_unset=True)
        old_location_id = unit.current_location_id
        old_status = unit.status

        for field, value in update_data.items():
            setattr(unit, field, value)

        db.commit()
        db.refresh(unit)

        if "current_location_id" in update_data and update_data["current_location_id"] != old_location_id:
            db.add(Transfer(
                unit_id=unit.id,
                dispatched_by_id=user_id,
                origin_location_id=old_location_id,
                destination_location_id=update_data["current_location_id"],
                status=TransferStatus.IN_TRANSIT,
                dispatched_at=datetime.now(UTC)
            ))
            db.commit()

        if "status" in update_data and update_data["status"] != old_status:
            transfer_status = TransferStatus.RECEIVED if update_data["status"] == UnitStatus.SOLD else TransferStatus.PENDING
            db.add(Transfer(
                unit_id=unit.id,
                dispatched_by_id=user_id,
                status=transfer_status,
                received_at=datetime.now(UTC) if transfer_status == TransferStatus.RECEIVED else None
            ))
            db.commit()

        return UnitRepository.get_unit(db, unit.id)

    @staticmethod
    def delete_unit(db: Session, unit_id: int) -> None:
        db.query(Transfer).filter(Transfer.unit_id == unit_id).delete()
        db.query(Unit).filter(Unit.id == unit_id).delete()
        db.commit()

    @staticmethod
    def get_stats(db: Session) -> dict:
        total_units = db.query(Unit).count()
        in_stock_units = db.query(Unit).filter(Unit.status == UnitStatus.IN_STOCK).count()
        sold_units = db.query(Unit).filter(Unit.status == UnitStatus.SOLD).count()
        in_transit_units = db.query(Unit).filter(Unit.status == UnitStatus.IN_TRANSIT).count()

        inventory_by_location = (
            db.query(Location.name, func.count(Unit.id).label("count"))
            .join(Unit, Unit.current_location_id == Location.id, isouter=True)
            .group_by(Location.id, Location.name)
            .all()
        )

        return {
            "total_units": total_units,
            "in_stock_units": in_stock_units,
            "sold_units": sold_units,
            "in_transit_units": in_transit_units,
            "inventory_by_location": [
                {"location": loc.name, "count": loc.count}
                for loc in inventory_by_location
            ]
        }

    @staticmethod
    def get_unit_transfers(db: Session, unit_id: int, skip: int, limit: int) -> list[Transfer]:
        return (
            db.query(Transfer)
            .options(
                selectinload(Transfer.dispatched_by),
                selectinload(Transfer.received_by),
                selectinload(Transfer.origin_location),
                selectinload(Transfer.destination_location)
            )
            .filter(Transfer.unit_id == unit_id)
            .order_by(Transfer.dispatched_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
