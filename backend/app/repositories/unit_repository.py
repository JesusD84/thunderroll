from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, func
from app.models.models import Unit, Transfer, UnitStatus, Location
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
    def get_by_engine_or_chassis(
        db: Session, engine_number: str | None, chassis_number: str | None
    ) -> Unit | None:
        conditions = []
        if engine_number is not None:
            conditions.append(Unit.engine_number == engine_number)
        if chassis_number is not None:
            conditions.append(Unit.chassis_number == chassis_number)
        if not conditions:
            return None
        return db.query(Unit).filter(or_(*conditions)).first()

    @staticmethod
    def get_by_engine_or_chassis_excluding(
        db: Session, engine_number: str | None, chassis_number: str | None, exclude_id: int
    ) -> Unit | None:
        conditions = []
        if engine_number is not None:
            conditions.append(Unit.engine_number == engine_number)
        if chassis_number is not None:
            conditions.append(Unit.chassis_number == chassis_number)
        if not conditions:
            return None
        return (
            db.query(Unit)
            .filter(
                and_(
                    Unit.id != exclude_id,
                    or_(*conditions)
                )
            )
            .first()
        )

    @staticmethod
    def create_unit(db: Session, unit_data: UnitCreate) -> Unit:
        payload = unit_data.model_dump()
        if payload.get("current_location_id") is None:
            raise ValueError("current_location_id is required")
        unit = Unit(**payload)
        db.add(unit)
        db.commit()
        db.refresh(unit)
        return UnitRepository.get_unit(db, unit.id)

    @staticmethod
    def update_unit(db: Session, unit: Unit, unit_update: UnitUpdate) -> Unit:
        update_data = unit_update.model_dump(exclude_unset=True)
        if "current_location_id" in update_data and update_data["current_location_id"] is None:
            raise ValueError("current_location_id is required")

        for field, value in update_data.items():
            setattr(unit, field, value)

        db.commit()
        db.refresh(unit)

        return UnitRepository.get_unit(db, unit.id)

    @staticmethod
    def delete_unit(db: Session, unit_id: int) -> None:
        db.query(Transfer).filter(Transfer.unit_id == unit_id).delete()
        db.query(Unit).filter(Unit.id == unit_id).delete()
        db.commit()

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

    @staticmethod
    def get_stats(db: Session) -> dict:
        total_units = db.query(Unit).count()
        in_stock_units = db.query(Unit).filter(Unit.status == UnitStatus.AVAILABLE).count()
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
