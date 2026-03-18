from sqlalchemy.orm import Session

from app.models.models import Location, Unit
from app.schemas.location import LocationCreate, LocationFilters, LocationUpdate


class LocationRepository:

    @staticmethod
    def get_locations(db: Session, filters: LocationFilters, skip: int, limit: int) -> list[Location]:
        query = db.query(Location)

        if filters.name:
            query = query.filter(Location.name.ilike(f"%{filters.name}%"))

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_location(db: Session, location_id: int) -> Location | None:
        return db.query(Location).filter(Location.id == location_id).first()

    @staticmethod
    def create_location(db: Session, location_data: LocationCreate) -> Location:
        db_location = Location(**location_data.model_dump())
        db.add(db_location)
        db.commit()
        db.refresh(db_location)
        return db_location

    @staticmethod
    def update_location(db: Session, db_location: Location, location_update: LocationUpdate) -> Location:
        update_data = location_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_location, field, value)
        db.commit()
        db.refresh(db_location)
        return db_location

    @staticmethod
    def delete_location(db: Session, db_location: Location) -> None:
        db.delete(db_location)
        db.commit()

    @staticmethod
    def count_units_at_location(db: Session, location_id: int) -> int:
        return db.query(Unit).filter(Unit.current_location_id == location_id).count()
