from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_
from app.models.models import Unit, Movement, MovementType, UnitStatus
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
            db.add(Movement(
                unit_id=unit.id,
                user_id=user_id,
                movement_type=MovementType.TRANSFER,
                from_location_id=old_location_id,
                to_location_id=update_data["current_location_id"],
                notes="Unit location updated"
            ))
            db.commit()

        if "status" in update_data and update_data["status"] != old_status:
            movement_type = MovementType.SALE if update_data["status"] == UnitStatus.SOLD else MovementType.TRANSFER
            db.add(Movement(
                unit_id=unit.id,
                user_id=user_id,
                movement_type=movement_type,
                notes=f"Status changed from {old_status} to {update_data['status']}"
            ))
            db.commit()

        return UnitRepository.get_unit(db, unit.id)

    @staticmethod
    def delete_unit(db: Session, unit_id: int) -> None:
        db.query(Movement).filter(Movement.unit_id == unit_id).delete()
        db.query(Unit).filter(Unit.id == unit_id).delete()
        db.commit()