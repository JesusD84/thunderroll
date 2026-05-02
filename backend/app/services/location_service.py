from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.models import Location
from app.schemas.location import LocationCreate, LocationFilters, LocationUpdate
from app.repositories.location_repository import LocationRepository


class LocationService:

    @staticmethod
    def get_locations(db: Session, filters: LocationFilters, skip: int, limit: int) -> list[Location]:
        return LocationRepository.get_locations(db, filters, skip, limit)

    @staticmethod
    def get_location_by_id(db: Session, location_id: int) -> Location:
        location = LocationRepository.get_location(db, location_id)
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        return location

    @staticmethod
    def create_location(db: Session, location_data: LocationCreate) -> Location:
        return LocationRepository.create_location(db, location_data)

    @staticmethod
    def update_location(db: Session, location_id: int, location_update: LocationUpdate) -> Location:
        db_location = LocationRepository.get_location(db, location_id)
        if not db_location:
            raise HTTPException(status_code=404, detail="Location not found")
        return LocationRepository.update_location(db, db_location, location_update)

    @staticmethod
    def delete_location(db: Session, location_id: int) -> dict:
        db_location = LocationRepository.get_location(db, location_id)
        if not db_location:
            raise HTTPException(status_code=404, detail="Location not found")

        unit_count = LocationRepository.count_units_at_location(db, location_id)
        if unit_count > 0:
            raise HTTPException(status_code=400, detail=f"Cannot delete: there {'is' if unit_count == 1 else 'are'} {unit_count} unit{'s' if unit_count != 1 else ''} at this location")

        LocationRepository.delete_location(db, db_location)
        return {"message": "Location deleted successfully"}