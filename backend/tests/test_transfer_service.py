"""Unit tests for TransferService."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.services.transfer_service import TransferService
from app.models.models import Transfer, Unit, Location, User, TransferStatus, UnitStatus
from app.schemas.transfer import TransferCreate, TransferFilters, TransferUpdate


# ---------------------------------------------------------------------------
# get_transfers
# ---------------------------------------------------------------------------

@patch("app.services.transfer_service.TransferRepository")
def test_get_transfers_delegates(mock_repo):
    """Delegates to TransferRepository.get_transfers."""
    mock_db = MagicMock()
    filters = TransferFilters()
    mock_repo.get_transfers.return_value = []

    result = TransferService.get_transfers(mock_db, filters, skip=0, limit=10)
    assert result == []


# ---------------------------------------------------------------------------
# get_transfer_by_id
# ---------------------------------------------------------------------------

@patch("app.services.transfer_service.TransferRepository")
def test_get_transfer_by_id_found(mock_repo):
    """Returns transfer when found."""
    mock_db = MagicMock()
    mock_transfer = Transfer(id=1)
    mock_repo.get_transfer.return_value = mock_transfer

    result = TransferService.get_transfer_by_id(mock_db, 1)
    assert result is mock_transfer


@patch("app.services.transfer_service.TransferRepository")
def test_get_transfer_by_id_not_found(mock_repo):
    """Raises 404 when transfer does not exist."""
    mock_db = MagicMock()
    mock_repo.get_transfer.return_value = None

    with pytest.raises(HTTPException) as exc:
        TransferService.get_transfer_by_id(mock_db, 999)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# create_transfer
# ---------------------------------------------------------------------------

@patch("app.services.transfer_service.TransferRepository")
@patch("app.services.transfer_service.UnitRepository")
@patch("app.services.transfer_service.UserRepository")
@patch("app.services.transfer_service.LocationRepository")
def test_create_transfer_success(mock_loc, mock_user, mock_unit, mock_transfer):
    """Creates a transfer when all relations are valid."""
    mock_db = MagicMock()
    transfer_data = TransferCreate(unit_id=1, destination_location_id=2)
    mock_unit.get_unit.return_value = Unit(id=1, current_location_id=1)
    mock_loc.get_location.return_value = Location(id=2)
    mock_transfer.create_transfer.return_value = Transfer(id=1)

    result = TransferService.create_transfer(mock_db, transfer_data)
    assert result is not None


@patch("app.services.transfer_service.TransferRepository")
@patch("app.services.transfer_service.UnitRepository")
@patch("app.services.transfer_service.UserRepository")
@patch("app.services.transfer_service.LocationRepository")
def test_create_transfer_unit_not_found(mock_loc, mock_user, mock_unit, mock_transfer):
    """Raises 404 when unit does not exist."""
    mock_db = MagicMock()
    transfer_data = TransferCreate(unit_id=999)
    mock_unit.get_unit.return_value = None

    with pytest.raises(HTTPException) as exc:
        TransferService.create_transfer(mock_db, transfer_data)
    assert exc.value.status_code == 404


@patch("app.services.transfer_service.TransferRepository")
@patch("app.services.transfer_service.UnitRepository")
@patch("app.services.transfer_service.UserRepository")
@patch("app.services.transfer_service.LocationRepository")
def test_create_transfer_same_origin_destination(mock_loc, mock_user, mock_unit, mock_transfer):
    """Raises 400 when origin and destination are the same."""
    mock_db = MagicMock()
    transfer_data = TransferCreate(
        unit_id=1, origin_location_id=2, destination_location_id=2
    )
    mock_unit.get_unit.return_value = Unit(id=1)
    mock_loc.get_location.return_value = Location(id=2)

    with pytest.raises(HTTPException) as exc:
        TransferService.create_transfer(mock_db, transfer_data)
    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# update_transfer
# ---------------------------------------------------------------------------

@patch("app.services.transfer_service.TransferRepository")
@patch("app.services.transfer_service.UnitRepository")
@patch("app.services.transfer_service.UserRepository")
@patch("app.services.transfer_service.LocationRepository")
def test_update_transfer_success(mock_loc, mock_user, mock_unit, mock_transfer):
    """Updates a transfer successfully."""
    mock_db = MagicMock()
    existing = Transfer(id=1, unit_id=1, status=TransferStatus.PENDING)
    mock_transfer.get_transfer.return_value = existing
    mock_unit.get_unit.return_value = Unit(id=1)
    mock_transfer.update_transfer.return_value = existing

    update_data = TransferUpdate(status=TransferStatus.IN_TRANSIT)
    result = TransferService.update_transfer(mock_db, 1, update_data)
    assert result is existing


@patch("app.services.transfer_service.TransferRepository")
def test_update_transfer_not_found(mock_repo):
    """Raises 404 when transfer does not exist."""
    mock_db = MagicMock()
    mock_repo.get_transfer.return_value = None

    with pytest.raises(HTTPException) as exc:
        TransferService.update_transfer(mock_db, 999, TransferUpdate())
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# delete_transfer
# ---------------------------------------------------------------------------

@patch("app.services.transfer_service.TransferRepository")
def test_delete_transfer_success(mock_repo):
    """Deletes a transfer successfully."""
    mock_db = MagicMock()
    mock_repo.get_transfer.return_value = Transfer(id=1)

    result = TransferService.delete_transfer(mock_db, 1)
    mock_repo.delete_transfer.assert_called_once()
    assert "deleted" in result["message"]


@patch("app.services.transfer_service.TransferRepository")
def test_delete_transfer_not_found(mock_repo):
    """Raises 404 when transfer does not exist."""
    mock_db = MagicMock()
    mock_repo.get_transfer.return_value = None

    with pytest.raises(HTTPException) as exc:
        TransferService.delete_transfer(mock_db, 999)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# get_transfer_stats
# ---------------------------------------------------------------------------

@patch("app.services.transfer_service.TransferRepository")
def test_get_transfer_stats(mock_repo):
    """Returns transfer statistics."""
    mock_db = MagicMock()
    mock_repo.count_transfers.return_value = 10
    mock_repo.count_transfers_by_status.side_effect = [3, 4, 2, 1]
    mock_repo.get_recent_transfers.return_value = []

    result = TransferService.get_transfer_stats(mock_db)

    assert result.total_transfers == 10
    assert result.pending_transfers == 3
    assert result.in_transit_transfers == 4
    assert result.received_transfers == 2
    assert result.cancelled == 1


# ---------------------------------------------------------------------------
# create_unit_transfer_record
# ---------------------------------------------------------------------------

@patch("app.services.transfer_service.TransferRepository")
def test_create_unit_transfer_record(mock_repo):
    """Delegates to TransferRepository.create_unit_transfer."""
    mock_db = MagicMock()
    mock_transfer = Transfer(id=1)
    mock_repo.create_unit_transfer.return_value = mock_transfer

    result = TransferService.create_unit_transfer_record(
        mock_db, unit_id=1, user_id=2, status=TransferStatus.PENDING,
    )
    assert result is mock_transfer


# ---------------------------------------------------------------------------
# get_active_transfer_for_unit
# ---------------------------------------------------------------------------

@patch("app.services.transfer_service.TransferRepository")
@patch("app.services.transfer_service.UnitRepository")
def test_get_active_transfer_for_unit_found(mock_unit, mock_transfer):
    """Returns active transfer when found."""
    mock_db = MagicMock()
    mock_unit.get_unit.return_value = Unit(id=1)
    mock_transfer.get_active_transfer_by_unit.return_value = Transfer(id=1)

    result = TransferService.get_active_transfer_for_unit(mock_db, 1)
    assert result is not None


@patch("app.services.transfer_service.TransferRepository")
@patch("app.services.transfer_service.UnitRepository")
def test_get_active_transfer_for_unit_not_found(mock_unit, mock_transfer):
    """Raises 404 when no active transfer."""
    mock_db = MagicMock()
    mock_unit.get_unit.return_value = Unit(id=1)
    mock_transfer.get_active_transfer_by_unit.return_value = None

    with pytest.raises(HTTPException) as exc:
        TransferService.get_active_transfer_for_unit(mock_db, 1)
    assert exc.value.status_code == 404
