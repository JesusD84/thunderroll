from sqlalchemy.orm import Session, selectinload
from app.models.models import Unit
from app.schemas.unit import UnitFilters


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
