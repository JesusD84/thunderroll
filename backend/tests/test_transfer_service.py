"""Unit tests for TransferService."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.models import Location, Transfer, TransferStatus, Unit, UnitStatus
from app.schemas.transfer import (
    TransferCreate,
    TransferFilters,
    TransferUpdate,
    UnitTransferRequest,
)
from app.services.transfer_service import TransferService
from tests.conftest import TestingSessionLocal

# ---------------------------------------------------------------------------
# A scenario: two locations and a unit that waits in the first one.
# ---------------------------------------------------------------------------


@pytest.fixture
def scenario():
    """Two locations and a unit in the first one, cleaned up afterwards."""
    db = TestingSessionLocal()
    suffix = uuid.uuid4().hex[:8]
    try:
        origin = Location(name=f"Origen {suffix}", address="Calle 1")
        destination = Location(name=f"Destino {suffix}", address="Calle 2")
        db.add_all([origin, destination])
        db.commit()
        db.refresh(origin)
        db.refresh(destination)

        unit = Unit(
            engine_number=f"ENG-{suffix}",
            chassis_number=f"CHS-{suffix}",
            model="TR",
            brand="Thunderoll",
            color="Rojo",
            current_location_id=origin.id,
            status=UnitStatus.AVAILABLE,
        )
        db.add(unit)
        db.commit()
        db.refresh(unit)

        yield {
            "db": db,
            "origin_id": origin.id,
            "destination_id": destination.id,
            "unit_id": unit.id,
        }
    finally:
        db.query(Transfer).filter(Transfer.unit_id == unit.id).delete()
        db.query(Unit).filter(Unit.id == unit.id).delete()
        db.query(Location).filter(
            Location.id.in_([origin.id, destination.id])
        ).delete()
        db.commit()
        db.close()


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


def test_create_transfer_dispatches_the_unit(scenario):
    """A dispatch puts the unit in transit and writes the transfer."""
    db = scenario["db"]
    transfer = TransferService.create_transfer(
        db,
        TransferCreate(
            unit_id=scenario["unit_id"],
            origin_location_id=scenario["origin_id"],
            destination_location_id=scenario["destination_id"],
        ),
        actor_id=1,
    )

    assert transfer.status == TransferStatus.PENDING
    assert transfer.dispatched_at is not None
    assert transfer.dispatched_by_id == 1

    db.expire_all()
    unit = db.query(Unit).filter(Unit.id == scenario["unit_id"]).one()
    assert unit.status == UnitStatus.IN_TRANSIT
    # The unit stays where it is until the transfer is closed.
    assert unit.current_location_id == scenario["origin_id"]


def test_create_transfer_rejects_a_sold_unit(scenario):
    """A sold unit never travels again."""
    db = scenario["db"]
    unit = db.query(Unit).filter(Unit.id == scenario["unit_id"]).one()
    unit.status = UnitStatus.SOLD
    db.commit()

    with pytest.raises(HTTPException) as exc:
        TransferService.create_transfer(
            db,
            TransferCreate(
                unit_id=scenario["unit_id"],
                destination_location_id=scenario["destination_id"],
            ),
            actor_id=1,
        )
    assert exc.value.status_code == 409


def test_create_transfer_rejects_a_second_active_transfer(scenario):
    """A unit holds at most one active transfer."""
    db = scenario["db"]
    payload = TransferCreate(
        unit_id=scenario["unit_id"],
        destination_location_id=scenario["destination_id"],
    )
    TransferService.create_transfer(db, payload, actor_id=1)

    with pytest.raises(HTTPException) as exc:
        TransferService.create_transfer(db, payload, actor_id=1)
    assert exc.value.status_code == 409


def test_create_transfer_rejects_a_wrong_origin(scenario):
    """The dispatch starts where the unit actually is."""
    db = scenario["db"]
    with pytest.raises(HTTPException) as exc:
        TransferService.create_transfer(
            db,
            TransferCreate(
                unit_id=scenario["unit_id"],
                origin_location_id=scenario["destination_id"],
                destination_location_id=scenario["origin_id"],
            ),
            actor_id=1,
        )
    assert exc.value.status_code == 409


def test_create_transfer_rejects_an_unknown_destination(scenario):
    """The destination has to exist."""
    db = scenario["db"]
    with pytest.raises(HTTPException) as exc:
        TransferService.create_transfer(
            db,
            TransferCreate(
                unit_id=scenario["unit_id"], destination_location_id=999999
            ),
            actor_id=1,
        )
    assert exc.value.status_code == 404


def test_create_transfer_rejects_the_same_origin_and_destination(scenario):
    """A unit cannot be sent where it already is."""
    db = scenario["db"]
    with pytest.raises(HTTPException) as exc:
        TransferService.create_transfer(
            db,
            TransferCreate(
                unit_id=scenario["unit_id"],
                origin_location_id=scenario["origin_id"],
                destination_location_id=scenario["origin_id"],
            ),
            actor_id=1,
        )
    assert exc.value.status_code == 400


def test_create_transfer_unit_not_found(scenario):
    """Raises 404 when the unit does not exist."""
    db = scenario["db"]
    with pytest.raises(HTTPException) as exc:
        TransferService.create_transfer(
            db,
            TransferCreate(unit_id=999999, destination_location_id=1),
            actor_id=1,
        )
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# update_transfer
# ---------------------------------------------------------------------------


def test_update_transfer_receives_the_unit_at_the_destination(scenario):
    """Receiving leaves the unit available at the destination."""
    db = scenario["db"]
    transfer = TransferService.create_transfer(
        db,
        TransferCreate(
            unit_id=scenario["unit_id"],
            destination_location_id=scenario["destination_id"],
        ),
        actor_id=1,
    )

    closed = TransferService.update_transfer(
        db, transfer.id, TransferUpdate(status=TransferStatus.RECEIVED), actor_id=7
    )

    assert closed.status == TransferStatus.RECEIVED
    assert closed.received_by_id == 7
    assert closed.received_at is not None

    db.expire_all()
    unit = db.query(Unit).filter(Unit.id == scenario["unit_id"]).one()
    assert unit.status == UnitStatus.AVAILABLE
    assert unit.current_location_id == scenario["destination_id"]


def test_update_transfer_rejects_a_second_reception(scenario):
    """A received transfer is closed: it cannot be received again."""
    db = scenario["db"]
    transfer = TransferService.create_transfer(
        db,
        TransferCreate(
            unit_id=scenario["unit_id"],
            destination_location_id=scenario["destination_id"],
        ),
        actor_id=1,
    )
    TransferService.update_transfer(
        db, transfer.id, TransferUpdate(status=TransferStatus.RECEIVED), actor_id=1
    )

    with pytest.raises(HTTPException) as exc:
        TransferService.update_transfer(
            db, transfer.id, TransferUpdate(status=TransferStatus.RECEIVED), actor_id=1
        )
    assert exc.value.status_code == 409


def test_update_transfer_cancels_and_brings_the_unit_back(scenario):
    """Cancelling brings the unit back to the origin, available."""
    db = scenario["db"]
    transfer = TransferService.create_transfer(
        db,
        TransferCreate(
            unit_id=scenario["unit_id"],
            destination_location_id=scenario["destination_id"],
        ),
        actor_id=1,
    )

    closed = TransferService.update_transfer(
        db, transfer.id, TransferUpdate(status=TransferStatus.CANCELLED), actor_id=7
    )

    assert closed.status == TransferStatus.CANCELLED
    assert closed.received_by_id == 7

    db.expire_all()
    unit = db.query(Unit).filter(Unit.id == scenario["unit_id"]).one()
    assert unit.status == UnitStatus.AVAILABLE
    assert unit.current_location_id == scenario["origin_id"]


def test_update_transfer_rejects_a_cancelled_transfer(scenario):
    """A cancelled transfer is closed too."""
    db = scenario["db"]
    transfer = TransferService.create_transfer(
        db,
        TransferCreate(
            unit_id=scenario["unit_id"],
            destination_location_id=scenario["destination_id"],
        ),
        actor_id=1,
    )
    TransferService.update_transfer(
        db, transfer.id, TransferUpdate(status=TransferStatus.CANCELLED), actor_id=1
    )

    with pytest.raises(HTTPException) as exc:
        TransferService.update_transfer(
            db, transfer.id, TransferUpdate(status=TransferStatus.RECEIVED), actor_id=1
        )
    assert exc.value.status_code == 409


def test_update_transfer_not_found(scenario):
    """Raises 404 when the transfer does not exist."""
    db = scenario["db"]
    with pytest.raises(HTTPException) as exc:
        TransferService.update_transfer(
            db, 999999, TransferUpdate(status=TransferStatus.RECEIVED), actor_id=1
        )
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
# transfer_unit_with_status_update
# ---------------------------------------------------------------------------
# This is what the unit-detail-page "Transferir"/"Vender" actions call.


def test_transfer_unit_not_found(scenario):
    """Raises 404 when the unit does not exist."""
    db = scenario["db"]
    with pytest.raises(HTTPException) as exc:
        TransferService.transfer_unit_with_status_update(
            db,
            999999,
            UnitTransferRequest(to_location_id=scenario["destination_id"]),
            user_id=1,
        )
    assert exc.value.status_code == 404


def test_transfer_unit_with_destination_sets_in_transit(scenario):
    """Providing to_location_id dispatches the unit (IN_TRANSIT)."""
    db = scenario["db"]

    TransferService.transfer_unit_with_status_update(
        db,
        scenario["unit_id"],
        UnitTransferRequest(
            from_location_id=scenario["origin_id"],
            to_location_id=scenario["destination_id"],
        ),
        user_id=1,
    )

    db.expire_all()
    unit = db.query(Unit).filter(Unit.id == scenario["unit_id"]).one()
    assert unit.status == UnitStatus.IN_TRANSIT

    transfer = (
        db.query(Transfer).filter(Transfer.unit_id == scenario["unit_id"]).one()
    )
    assert transfer.status == TransferStatus.PENDING
    assert transfer.origin_location_id == scenario["origin_id"]
    assert transfer.destination_location_id == scenario["destination_id"]
    assert transfer.dispatched_by_id == 1


def test_transfer_unit_without_destination_sells_it(scenario):
    """Omitting to_location_id means 'Vender': the unit becomes SOLD."""
    db = scenario["db"]

    TransferService.transfer_unit_with_status_update(
        db,
        scenario["unit_id"],
        UnitTransferRequest(from_location_id=scenario["origin_id"]),
        user_id=1,
    )

    db.expire_all()
    unit = db.query(Unit).filter(Unit.id == scenario["unit_id"]).one()
    assert unit.status == UnitStatus.SOLD
    assert unit.sold_date is not None

    # The sale is part of the history.
    transfer = (
        db.query(Transfer).filter(Transfer.unit_id == scenario["unit_id"]).one()
    )
    assert transfer.status == TransferStatus.RECEIVED
    assert transfer.destination_location_id is None
    assert transfer.origin_location_id == scenario["origin_id"]


def test_transfer_unit_same_origin_destination(scenario):
    """Raises 400 when origin and destination are the same location."""
    db = scenario["db"]
    with pytest.raises(HTTPException) as exc:
        TransferService.transfer_unit_with_status_update(
            db,
            scenario["unit_id"],
            UnitTransferRequest(
                from_location_id=scenario["origin_id"],
                to_location_id=scenario["origin_id"],
            ),
            user_id=1,
        )
    assert exc.value.status_code == 400


def test_transfer_unit_rejects_a_unit_in_transit(scenario):
    """A unit that is already travelling cannot be dispatched again."""
    db = scenario["db"]
    TransferService.transfer_unit_with_status_update(
        db,
        scenario["unit_id"],
        UnitTransferRequest(to_location_id=scenario["destination_id"]),
        user_id=1,
    )

    with pytest.raises(HTTPException) as exc:
        TransferService.transfer_unit_with_status_update(
            db,
            scenario["unit_id"],
            UnitTransferRequest(to_location_id=scenario["destination_id"]),
            user_id=1,
        )
    assert exc.value.status_code == 409


def test_transfer_unit_rejects_a_sold_unit(scenario):
    """A sold unit never travels again."""
    db = scenario["db"]
    unit = db.query(Unit).filter(Unit.id == scenario["unit_id"]).one()
    unit.status = UnitStatus.SOLD
    db.commit()

    with pytest.raises(HTTPException) as exc:
        TransferService.transfer_unit_with_status_update(
            db,
            scenario["unit_id"],
            UnitTransferRequest(to_location_id=scenario["destination_id"]),
            user_id=1,
        )
    assert exc.value.status_code == 409


def test_transfer_unit_rejects_a_wrong_origin(scenario):
    """The dispatch starts where the unit actually is."""
    db = scenario["db"]
    with pytest.raises(HTTPException) as exc:
        TransferService.transfer_unit_with_status_update(
            db,
            scenario["unit_id"],
            UnitTransferRequest(
                from_location_id=scenario["destination_id"],
                to_location_id=scenario["origin_id"],
            ),
            user_id=1,
        )
    assert exc.value.status_code == 409


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
