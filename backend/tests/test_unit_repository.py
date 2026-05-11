"""Unit tests for UnitRepository."""

import pytest
from unittest.mock import MagicMock
from app.repositories.unit_repository import UnitRepository
from app.models.models import Unit, Location, UnitStatus
from app.schemas.unit import UnitCreate, UnitFilters, UnitUpdate


# ---------------------------------------------------------------------------
# get_units
# ---------------------------------------------------------------------------

def test_get_units_no_filters():
    """Returns paginated units without filters."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.offset.return_value.limit.return_value.all.return_value = []
    filters = UnitFilters()

    result = UnitRepository.get_units(mock_db, filters, skip=0, limit=10)
    assert result == []


def test_get_units_with_status_filter():
    """Applies status filter."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
    filters = UnitFilters(status=UnitStatus.AVAILABLE)

    result = UnitRepository.get_units(mock_db, filters, skip=0, limit=10)
    assert result == []


def test_get_units_with_search_filter():
    """Applies search filter across multiple columns."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
    filters = UnitFilters(search="thunder")

    result = UnitRepository.get_units(mock_db, filters, skip=0, limit=10)
    assert result == []


# ---------------------------------------------------------------------------
# get_unit
# ---------------------------------------------------------------------------

def test_get_unit_found():
    """Returns unit with location eager-loaded."""
    mock_db = MagicMock()
    mock_unit = Unit(id=1, model="TR", brand="Thunderrol")
    mock_db.query.return_value.options.return_value.filter.return_value.one_or_none.return_value = mock_unit

    result = UnitRepository.get_unit(mock_db, 1)
    assert result is mock_unit


def test_get_unit_not_found():
    """Returns None when unit does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.one_or_none.return_value = None

    result = UnitRepository.get_unit(mock_db, 999)
    assert result is None


# ---------------------------------------------------------------------------
# get_by_engine_or_chassis
# ---------------------------------------------------------------------------

def test_get_by_engine_or_chassis_found():
    """Returns unit matching engine number."""
    mock_db = MagicMock()
    mock_unit = Unit(id=1, engine_number="ENG123")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_unit

    result = UnitRepository.get_by_engine_or_chassis(mock_db, "ENG123", None)
    assert result is mock_unit


def test_get_by_engine_or_chassis_both_none():
    """Returns None when both engine and chassis are None."""
    mock_db = MagicMock()
    result = UnitRepository.get_by_engine_or_chassis(mock_db, None, None)
    assert result is None


# ---------------------------------------------------------------------------
# create_unit
# ---------------------------------------------------------------------------

def test_create_unit_success():
    """Creates a unit and returns it with eager-loaded relations."""
    mock_db = MagicMock()
    unit_data = UnitCreate(
        model="TR", brand="Thunderrol", color="Red",
        current_location_id=1, engine_number="ENG1",
    )
    mock_unit = Unit(id=1, model="TR")
    mock_db.query.return_value.options.return_value.filter.return_value.one_or_none.return_value = mock_unit

    result = UnitRepository.create_unit(mock_db, unit_data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert result is mock_unit


def test_create_unit_missing_location():
    """Raises ValueError when current_location_id is None."""
    mock_db = MagicMock()
    unit_data = UnitCreate(
        model="TR", brand="Thunderrol", color="Red",
        current_location_id=1, engine_number="ENG1",
    )
    unit_data.current_location_id = None

    with pytest.raises(ValueError, match="current_location_id is required"):
        UnitRepository.create_unit(mock_db, unit_data)


# ---------------------------------------------------------------------------
# update_unit
# ---------------------------------------------------------------------------

def test_update_unit_success():
    """Updates unit fields and returns refreshed unit."""
    mock_db = MagicMock()
    unit = Unit(id=1, model="Old")
    update_data = UnitUpdate(model="New")
    mock_db.query.return_value.options.return_value.filter.return_value.one_or_none.return_value = unit

    result = UnitRepository.update_unit(mock_db, unit, update_data)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(unit)
    assert result is unit


# ---------------------------------------------------------------------------
# delete_unit
# ---------------------------------------------------------------------------

def test_delete_unit_cascades_transfers():
    """Deletes unit and its transfers, then commits."""
    mock_db = MagicMock()

    UnitRepository.delete_unit(mock_db, 1)

    assert mock_db.query.call_count >= 2
    mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

def test_get_stats():
    """Returns stats dict with expected keys."""
    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.join.return_value.group_by.return_value.all.return_value = []

    result = UnitRepository.get_stats(mock_db)

    assert "total_units" in result
    assert "in_stock_units" in result
    assert "sold_units" in result
    assert "in_transit_units" in result
    assert "inventory_by_location" in result
