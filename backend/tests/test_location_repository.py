"""Unit tests for LocationRepository."""

import pytest
from unittest.mock import MagicMock
from app.repositories.location_repository import LocationRepository
from app.models.models import Location, Unit
from app.schemas.location import LocationCreate, LocationFilters, LocationUpdate


# ---------------------------------------------------------------------------
# get_locations
# ---------------------------------------------------------------------------

def test_get_locations_no_filters():
    """Returns paginated locations without filters."""
    mock_db = MagicMock()
    mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
    filters = LocationFilters()

    result = LocationRepository.get_locations(mock_db, filters, skip=0, limit=10)
    assert result == []


def test_get_locations_with_name_filter():
    """Applies name ilike filter when provided."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
    filters = LocationFilters(name="Bodega")

    result = LocationRepository.get_locations(mock_db, filters, skip=0, limit=10)
    assert result == []


# ---------------------------------------------------------------------------
# get_location
# ---------------------------------------------------------------------------

def test_get_location_found():
    """Returns location when ID exists."""
    mock_db = MagicMock()
    mock_loc = Location(id=1, name="Bodega")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_loc

    result = LocationRepository.get_location(mock_db, 1)
    assert result is mock_loc


def test_get_location_not_found():
    """Returns None when ID does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = LocationRepository.get_location(mock_db, 999)
    assert result is None


# ---------------------------------------------------------------------------
# create_location
# ---------------------------------------------------------------------------

def test_create_location_success():
    """Creates a location and commits."""
    mock_db = MagicMock()
    loc_data = LocationCreate(name="New Location", address="123 St")

    result = LocationRepository.create_location(mock_db, loc_data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result is not None


# ---------------------------------------------------------------------------
# update_location
# ---------------------------------------------------------------------------

def test_update_location_changes_fields():
    """Updates only provided fields."""
    mock_db = MagicMock()
    existing = Location(id=1, name="Old", address="Old St")
    update_data = LocationUpdate(name="New")

    result = LocationRepository.update_location(mock_db, existing, update_data)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result is existing


def test_update_location_no_fields():
    """Calling update with no fields still commits."""
    mock_db = MagicMock()
    existing = Location(id=1, name="Old")
    update_data = LocationUpdate()

    result = LocationRepository.update_location(mock_db, existing, update_data)

    mock_db.commit.assert_called_once()
    assert result is existing


# ---------------------------------------------------------------------------
# delete_location
# ---------------------------------------------------------------------------

def test_delete_location_success():
    """Deletes the location and commits."""
    mock_db = MagicMock()
    loc = Location(id=1, name="ToDelete")

    LocationRepository.delete_location(mock_db, loc)

    mock_db.delete.assert_called_once_with(loc)
    mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# count_units_at_location
# ---------------------------------------------------------------------------

def test_count_units_at_location_zero():
    """Returns 0 when no units at location."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.count.return_value = 0

    result = LocationRepository.count_units_at_location(mock_db, 1)
    assert result == 0


def test_count_units_at_location_some():
    """Returns count of units at location."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.count.return_value = 5

    result = LocationRepository.count_units_at_location(mock_db, 1)
    assert result == 5
