"""Unit tests for TransferRepository."""

import pytest
from unittest.mock import MagicMock
from app.repositories.transfer_repository import TransferRepository
from app.models.models import Transfer, TransferStatus
from app.schemas.transfer import TransferCreate, TransferFilters, TransferUpdate


# ---------------------------------------------------------------------------
# get_transfers
# ---------------------------------------------------------------------------

def test_get_transfers_no_filters():
    """Returns paginated transfers without filters."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    filters = TransferFilters()

    result = TransferRepository.get_transfers(mock_db, filters, skip=0, limit=10)
    assert result == []


def test_get_transfers_with_status_filter():
    """Applies status filter."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    filters = TransferFilters(status=TransferStatus.PENDING)

    result = TransferRepository.get_transfers(mock_db, filters, skip=0, limit=10)
    assert result == []


# ---------------------------------------------------------------------------
# get_transfer
# ---------------------------------------------------------------------------

def test_get_transfer_found():
    """Returns transfer when ID exists."""
    mock_db = MagicMock()
    mock_transfer = Transfer(id=1, unit_id=1)
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_transfer

    result = TransferRepository.get_transfer(mock_db, 1)
    assert result is mock_transfer


def test_get_transfer_not_found():
    """Returns None when ID does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None

    result = TransferRepository.get_transfer(mock_db, 999)
    assert result is None


# ---------------------------------------------------------------------------
# create_transfer
# ---------------------------------------------------------------------------

def test_create_transfer_success():
    """Creates a transfer and commits."""
    mock_db = MagicMock()
    transfer_data = TransferCreate(unit_id=1)

    result = TransferRepository.create_transfer(mock_db, transfer_data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result is not None


def test_create_transfer_does_not_null_dispatched_at():
    """Regression: dispatched_at must not be explicitly set to None,
    otherwise it overrides the DB server_default=func.now().
    """
    mock_db = MagicMock()
    transfer_data = TransferCreate(unit_id=1)

    TransferRepository.create_transfer(mock_db, transfer_data)

    created_transfer = mock_db.add.call_args[0][0]
    assert "dispatched_at" not in created_transfer.__dict__


def test_create_transfer_keeps_provided_dispatched_at():
    """When dispatched_at is provided explicitly, it must be kept."""
    from datetime import datetime, UTC
    mock_db = MagicMock()
    provided_at = datetime.now(UTC)
    transfer_data = TransferCreate(unit_id=1, dispatched_at=provided_at)

    TransferRepository.create_transfer(mock_db, transfer_data)

    created_transfer = mock_db.add.call_args[0][0]
    assert created_transfer.dispatched_at == provided_at


# ---------------------------------------------------------------------------
# update_transfer
# ---------------------------------------------------------------------------

def test_update_transfer_success():
    """Updates transfer fields."""
    mock_db = MagicMock()
    existing = Transfer(id=1, unit_id=1)
    update_data = TransferUpdate(status=TransferStatus.RECEIVED)

    result = TransferRepository.update_transfer(mock_db, existing, update_data)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result is existing


# ---------------------------------------------------------------------------
# delete_transfer
# ---------------------------------------------------------------------------

def test_delete_transfer_success():
    """Deletes transfer and commits."""
    mock_db = MagicMock()
    transfer = Transfer(id=1)

    TransferRepository.delete_transfer(mock_db, transfer)

    mock_db.delete.assert_called_once_with(transfer)
    mock_db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# count_transfers
# ---------------------------------------------------------------------------

def test_count_transfers():
    """Returns total transfer count."""
    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 5

    result = TransferRepository.count_transfers(mock_db)
    assert result == 5


# ---------------------------------------------------------------------------
# create_unit_transfer
# ---------------------------------------------------------------------------

def test_create_unit_transfer_success():
    """Creates a unit transfer record with all fields."""
    mock_db = MagicMock()

    result = TransferRepository.create_unit_transfer(
        mock_db, unit_id=1, dispatched_by_id=2,
        origin_location_id=3, destination_location_id=4,
        status=TransferStatus.IN_TRANSIT,
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert result is not None


def test_create_unit_transfer_defaults_dispatched_at_when_missing():
    """Regression: dispatched_at must default to now(), never stay None,
    since this Transfer() is a plain in-memory object with no way for the
    DB server_default to apply once a value (even None) is already set.
    """
    mock_db = MagicMock()

    result = TransferRepository.create_unit_transfer(
        mock_db, unit_id=1, dispatched_by_id=2,
        status=TransferStatus.PENDING,
    )

    assert result.dispatched_at is not None


# ---------------------------------------------------------------------------
# get_active_transfer_by_unit
# ---------------------------------------------------------------------------

def test_get_active_transfer_by_unit_found():
    """Returns active transfer for a unit."""
    mock_db = MagicMock()
    mock_transfer = Transfer(id=1, unit_id=1, status=TransferStatus.IN_TRANSIT)
    mock_db.query.return_value.options.return_value.filter.return_value.order_by.return_value.first.return_value = mock_transfer

    result = TransferRepository.get_active_transfer_by_unit(mock_db, 1)
    assert result is mock_transfer


def test_get_active_transfer_by_unit_not_found():
    """Returns None when no active transfer exists."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.order_by.return_value.first.return_value = None

    result = TransferRepository.get_active_transfer_by_unit(mock_db, 1)
    assert result is None
