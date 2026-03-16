from sqlalchemy.orm import Session, selectinload
from app.models.models import Unit
from app.schemas.unit import UnitCreate, UnitFilters


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
    def create_unit(db: Session, unit_data: UnitCreate) -> Unit:
        unit = Unit(**unit_data.model_dump())
        db.add(unit)
        db.commit()
        db.refresh(unit)
        return UnitRepository.get_unit(db, unit.id)