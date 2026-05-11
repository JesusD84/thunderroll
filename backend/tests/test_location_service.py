"""Unit tests for LocationService."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.services.location_service import LocationService
from app.models.models import Location
from app.schemas.location import LocationCreate, LocationFilters, LocationUpdate


# ---------------------------------------------------------------------------
# get_locations
# ---------------------------------------------------------------------------

@patch("app.services.location_service.LocationRepository")
def test_get_locations_delegates(mock_repo):
    """Delegates to LocationRepository.get_locations."""
    mock_db = MagicMock()
    filters = LocationFilters()
    mock_repo.get_locations.return_value = []

    result = LocationService.get_locations(mock_db, filters, skip=0, limit=10)

    mock_repo.get_locations.assert_called_once_with(mock_db, filters, 0, 10)
    assert result == []


# ---------------------------------------------------------------------------
# get_location_by_id
# ---------------------------------------------------------------------------

@patch("app.services.location_service.LocationRepository")
def test_get_location_by_id_found(mock_repo):
    """Returns location when found."""
    mock_db = MagicMock()
    mock_loc = Location(id=1, name="Bodega")
    mock_repo.get_location.return_value = mock_loc

    result = LocationService.get_location_by_id(mock_db, 1)
    assert result is mock_loc


@patch("app.services.location_service.LocationRepository")
def test_get_location_by_id_not_found(mock_repo):
    """Raises 404 when location does not exist."""
    mock_db = MagicMock()
    mock_repo.get_location.return_value = None

    with pytest.raises(HTTPException) as exc:
        LocationService.get_location_by_id(mock_db, 999)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# create_location
# ---------------------------------------------------------------------------

@patch("app.services.location_service.LocationRepository")
def test_create_location_success(mock_repo):
    """Delegates to LocationRepository.create_location."""
    mock_db = MagicMock()
    loc_data = LocationCreate(name="New", address="123 St")
    mock_loc = Location(id=2, name="New")
    mock_repo.create_location.return_value = mock_loc

    result = LocationService.create_location(mock_db, loc_data)

    mock_repo.create_location.assert_called_once_with(mock_db, loc_data)
    assert result is mock_loc


# ---------------------------------------------------------------------------
# update_location
# ---------------------------------------------------------------------------

@patch("app.services.location_service.LocationRepository")
def test_update_location_success(mock_repo):
    """Updates an existing location."""
    mock_db = MagicMock()
    existing = Location(id=1, name="Old")
    update_data = LocationUpdate(name="New")
    mock_repo.get_location.return_value = existing
    mock_repo.update_location.return_value = existing

    result = LocationService.update_location(mock_db, 1, update_data)

    mock_repo.update_location.assert_called_once_with(mock_db, existing, update_data)
    assert result is existing


@patch("app.services.location_service.LocationRepository")
def test_update_location_not_found(mock_repo):
    """Raises 404 when location to update does not exist."""
    mock_db = MagicMock()
    mock_repo.get_location.return_value = None

    with pytest.raises(HTTPException) as exc:
        LocationService.update_location(mock_db, 999, LocationUpdate(name="X"))
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_location
# ---------------------------------------------------------------------------

@patch("app.services.location_service.LocationRepository")
def test_delete_location_empty(mock_repo):
    """Deletes location when it has no units."""
    mock_db = MagicMock()
    loc = Location(id=1, name="Empty")
    mock_repo.get_location.return_value = loc
    mock_repo.count_units_at_location.return_value = 0

    result = LocationService.delete_location(mock_db, 1)

    mock_repo.delete_location.assert_called_once_with(mock_db, loc)
    assert result == {"message": "Location deleted successfully"}


@patch("app.services.location_service.LocationRepository")
def test_delete_location_with_units(mock_repo):
    """Raises 400 when location has units."""
    mock_db = MagicMock()
    loc = Location(id=1, name="Occupied")
    mock_repo.get_location.return_value = loc
    mock_repo.count_units_at_location.return_value = 3

    with pytest.raises(HTTPException) as exc:
        LocationService.delete_location(mock_db, 1)
    assert exc.value.status_code == 400
    assert "3 units" in exc.value.detail


@patch("app.services.location_service.LocationRepository")
def test_delete_location_not_found(mock_repo):
    """Raises 404 when location to delete does not exist."""
    mock_db = MagicMock()
    mock_repo.get_location.return_value = None

    with pytest.raises(HTTPException) as exc:
        LocationService.delete_location(mock_db, 999)
    assert exc.value.status_code == 404
