"""Unit tests for UnitService."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.services.unit_service import UnitService
from app.models.models import Unit, Location, UnitStatus, TransferStatus
from app.schemas.unit import UnitCreate, UnitFilters, UnitUpdate
from app.schemas.transfer import TransferCreate


# ---------------------------------------------------------------------------
# get_units
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.UnitRepository")
def test_get_units_delegates(mock_repo):
    """Delegates to UnitRepository.get_units."""
    mock_db = MagicMock()
    filters = UnitFilters()
    mock_repo.get_units.return_value = []

    result = UnitService.get_units(mock_db, filters, skip=0, limit=10)

    mock_repo.get_units.assert_called_once_with(mock_db, filters, 0, 10)
    assert result == []


# ---------------------------------------------------------------------------
# create_unit
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.UnitRepository")
@patch("app.services.unit_service.LocationRepository")
def test_create_unit_success(mock_loc_repo, mock_unit_repo):
    """Creates a unit when location exists and no duplicates."""
    mock_db = MagicMock()
    unit_data = UnitCreate(
        model="TR", brand="Thunderrol", color="Red",
        current_location_id=1, engine_number="ENG1",
    )
    mock_loc_repo.get_location.return_value = Location(id=1, name="Bodega")
    mock_unit_repo.get_by_engine_or_chassis.return_value = None
    mock_unit = Unit(id=1, model="TR")
    mock_unit_repo.create_unit.return_value = mock_unit

    result = UnitService.create_unit(mock_db, unit_data)
    assert result is mock_unit


@patch("app.services.unit_service.UnitRepository")
@patch("app.services.unit_service.LocationRepository")
def test_create_unit_location_not_found(mock_loc_repo, mock_unit_repo):
    """Raises 404 when location does not exist."""
    mock_db = MagicMock()
    unit_data = UnitCreate(
        model="TR", brand="Thunderrol", color="Red",
        current_location_id=999,
    )
    mock_loc_repo.get_location.return_value = None

    with pytest.raises(HTTPException) as exc:
        UnitService.create_unit(mock_db, unit_data)
    assert exc.value.status_code == 404


@patch("app.services.unit_service.UnitRepository")
@patch("app.services.unit_service.LocationRepository")
def test_create_unit_duplicate_engine(mock_loc_repo, mock_unit_repo):
    """Raises 400 when engine/chassis already exists."""
    mock_db = MagicMock()
    unit_data = UnitCreate(
        model="TR", brand="Thunderrol", color="Red",
        current_location_id=1, engine_number="ENG1",
    )
    mock_loc_repo.get_location.return_value = Location(id=1, name="Bodega")
    mock_unit_repo.get_by_engine_or_chassis.return_value = Unit(id=2, engine_number="ENG1")

    with pytest.raises(HTTPException) as exc:
        UnitService.create_unit(mock_db, unit_data)
    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# get_unit_by_id
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.UnitRepository")
def test_get_unit_by_id_found(mock_repo):
    """Returns unit when found."""
    mock_db = MagicMock()
    mock_unit = Unit(id=1, model="TR")
    mock_repo.get_unit.return_value = mock_unit

    result = UnitService.get_unit_by_id(mock_db, 1)
    assert result is mock_unit


@patch("app.services.unit_service.UnitRepository")
def test_get_unit_by_id_not_found(mock_repo):
    """Raises 404 when unit does not exist."""
    mock_db = MagicMock()
    mock_repo.get_unit.return_value = None

    with pytest.raises(HTTPException) as exc:
        UnitService.get_unit_by_id(mock_db, 999)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# update_unit
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.TransferService")
@patch("app.services.unit_service.UnitRepository")
@patch("app.services.unit_service.LocationRepository")
def test_update_unit_success(mock_loc_repo, mock_unit_repo, mock_transfer_svc):
    """Updates unit fields without triggering transfers."""
    mock_db = MagicMock()
    unit = Unit(id=1, model="Old", current_location_id=1, status=UnitStatus.AVAILABLE)
    mock_unit_repo.get_unit.return_value = unit
    update_data = UnitUpdate(model="New")
    mock_unit_repo.update_unit.return_value = unit

    result = UnitService.update_unit(mock_db, 1, update_data, user_id=1)
    assert result is unit
    mock_transfer_svc.create_unit_transfer_record.assert_not_called()


@patch("app.services.unit_service.TransferService")
@patch("app.services.unit_service.UnitRepository")
@patch("app.services.unit_service.LocationRepository")
def test_update_unit_location_change_creates_transfer(mock_loc_repo, mock_unit_repo, mock_transfer_svc):
    """Changing location creates a transfer record."""
    mock_db = MagicMock()
    unit = Unit(id=1, model="TR", current_location_id=1, status=UnitStatus.AVAILABLE)
    mock_unit_repo.get_unit.return_value = unit
    mock_loc_repo.get_location.return_value = Location(id=2, name="Taller")
    mock_unit_repo.update_unit.return_value = unit

    update_data = UnitUpdate(current_location_id=2)
    UnitService.update_unit(mock_db, 1, update_data, user_id=1)

    mock_transfer_svc.create_unit_transfer_record.assert_called_once()


@patch("app.services.unit_service.TransferService")
@patch("app.services.unit_service.UnitRepository")
@patch("app.services.unit_service.LocationRepository")
def test_update_unit_status_to_sold_creates_transfer(mock_loc_repo, mock_unit_repo, mock_transfer_svc):
    """Changing status to SOLD creates a RECEIVED transfer record."""
    mock_db = MagicMock()
    unit = Unit(id=1, model="TR", current_location_id=1, status=UnitStatus.AVAILABLE)
    mock_unit_repo.get_unit.return_value = unit
    mock_unit_repo.update_unit.return_value = unit

    update_data = UnitUpdate(status=UnitStatus.SOLD)
    UnitService.update_unit(mock_db, 1, update_data, user_id=1)

    mock_transfer_svc.create_unit_transfer_record.assert_called_once()


@patch("app.services.unit_service.UnitRepository")
def test_update_unit_not_found(mock_repo):
    """Raises 404 when unit does not exist."""
    mock_db = MagicMock()
    mock_repo.get_unit.return_value = None

    with pytest.raises(HTTPException) as exc:
        UnitService.update_unit(mock_db, 999, UnitUpdate(model="X"), user_id=1)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_unit
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.UnitRepository")
def test_delete_unit_success(mock_repo):
    """Deletes a unit that is not in transit."""
    mock_db = MagicMock()
    unit = Unit(id=1, status=UnitStatus.AVAILABLE)
    mock_repo.get_unit.return_value = unit

    result = UnitService.delete_unit(mock_db, 1)
    mock_repo.delete_unit.assert_called_once_with(mock_db, 1)
    assert "deleted" in result["message"]


@patch("app.services.unit_service.UnitRepository")
def test_delete_unit_in_transit(mock_repo):
    """Raises 400 when unit is in transit."""
    mock_db = MagicMock()
    unit = Unit(id=1, status=UnitStatus.IN_TRANSIT)
    mock_repo.get_unit.return_value = unit

    with pytest.raises(HTTPException) as exc:
        UnitService.delete_unit(mock_db, 1)
    assert exc.value.status_code == 400


@patch("app.services.unit_service.UnitRepository")
def test_delete_unit_not_found(mock_repo):
    """Raises 404 when unit does not exist."""
    mock_db = MagicMock()
    mock_repo.get_unit.return_value = None

    with pytest.raises(HTTPException) as exc:
        UnitService.delete_unit(mock_db, 999)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.UnitRepository")
def test_get_stats_delegates(mock_repo):
    """Delegates to UnitRepository.get_stats."""
    mock_db = MagicMock()
    mock_repo.get_stats.return_value = {"total_units": 5}

    result = UnitService.get_stats(mock_db)
    assert result == {"total_units": 5}


# ---------------------------------------------------------------------------
# get_unit_transfers
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.UnitRepository")
def test_get_unit_transfers_success(mock_repo):
    """Returns transfers for an existing unit."""
    mock_db = MagicMock()
    unit = Unit(id=1)
    mock_repo.get_unit.return_value = unit
    mock_repo.get_unit_transfers.return_value = []

    result = UnitService.get_unit_transfers(mock_db, 1, skip=0, limit=10)
    assert result == []


@patch("app.services.unit_service.UnitRepository")
def test_get_unit_transfers_unit_not_found(mock_repo):
    """Raises 404 when unit does not exist."""
    mock_db = MagicMock()
    mock_repo.get_unit.return_value = None

    with pytest.raises(HTTPException) as exc:
        UnitService.get_unit_transfers(mock_db, 999, skip=0, limit=10)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# transfer_unit
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.TransferService")
def test_transfer_unit_delegates(mock_transfer_svc):
    """Delegates to TransferService.transfer_unit_with_status_update."""
    mock_db = MagicMock()
    transfer_data = TransferCreate(from_location_id=1, to_location_id=2, unit_ids=[1])
    mock_unit = Unit(id=1)
    mock_transfer_svc.transfer_unit_with_status_update.return_value = mock_unit

    result = UnitService.transfer_unit(mock_db, 1, transfer_data, user_id=1)
    assert result is mock_unit


# ---------------------------------------------------------------------------
# get_active_transfer
# ---------------------------------------------------------------------------

@patch("app.services.unit_service.TransferService")
def test_get_active_transfer_delegates(mock_transfer_svc):
    """Delegates to TransferService.get_active_transfer_for_unit."""
    mock_db = MagicMock()
    mock_transfer_svc.get_active_transfer_for_unit.return_value = None

    result = UnitService.get_active_transfer(mock_db, 1)
    assert result is None
