"""The integrity rules of the unit lifecycle, end to end.

A traceability system is only as good as the state it keeps: a unit that is
sold twice, a transfer that is received twice or a unit that is deleted with
its history are all ways of lying about the inventory. These tests pin down
every rule the lifecycle defines:

* the allowed transitions of a unit and of a transfer;
* the state of a unit comes out of the state of its transfer;
* the actor and the clock belong to the server;
* a unit holds at most one active transfer;
* a unit with history is never deleted;
* there is a single way to sell a unit, and it leaves a record.
"""

import uuid

import pytest
from httpx import AsyncClient

from app.models.models import Location, Transfer, TransferStatus, Unit, UnitStatus
from tests.conftest import TestingSessionLocal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def places():
    """Three locations of their own, cleaned up afterwards.

    The tests do not use the shared locations of the session: another test
    file deletes one of them, and a location that is gone cannot be part of
    a route.
    """
    db = TestingSessionLocal()
    suffix = uuid.uuid4().hex[:8]
    try:
        locations = [
            Location(name=f"Bodega {suffix}", address="Calle 1"),
            Location(name=f"Taller {suffix}", address="Calle 2"),
            Location(name=f"Sucursal {suffix}", address="Calle 3"),
        ]
        db.add_all(locations)
        db.commit()
        for location in locations:
            db.refresh(location)
        yield locations
    finally:
        location_ids = [location.id for location in locations]
        unit_ids = [
            unit.id
            for unit in db.query(Unit)
            .filter(Unit.current_location_id.in_(location_ids))
            .all()
        ]
        db.query(Transfer).filter(Transfer.unit_id.in_(unit_ids)).delete()
        db.query(Unit).filter(Unit.id.in_(unit_ids)).delete()
        db.query(Location).filter(Location.id.in_(location_ids)).delete()
        db.commit()
        db.close()


async def _create_unit(
    client: AsyncClient, headers: dict, location_id: int, prefix: str
) -> int:
    """A unit waiting in ``location_id``."""
    suffix = uuid.uuid4().hex[:8]
    response = await client.post(
        "/api/v1/units/",
        json={
            "model": "TR-Lifecycle",
            "brand": "Thunderoll",
            "color": "Azul",
            "current_location_id": location_id,
            "engine_number": f"{prefix}-{suffix}",
            "chassis_number": f"{prefix}-CHS-{suffix}",
            "status": "AVAILABLE",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _dispatch(
    client: AsyncClient,
    headers: dict,
    unit_id: int,
    origin_id: int,
    destination_id: int,
):
    """Send a unit on its way."""
    return await client.post(
        "/api/v1/transfers/",
        json={
            "unit_id": unit_id,
            "origin_location_id": origin_id,
            "destination_location_id": destination_id,
        },
        headers=headers,
    )


def _unit_row(unit_id: int) -> Unit:
    db = TestingSessionLocal()
    try:
        return db.query(Unit).filter(Unit.id == unit_id).one()
    finally:
        db.close()


def _transfer_rows(unit_id: int) -> list[Transfer]:
    db = TestingSessionLocal()
    try:
        return (
            db.query(Transfer)
            .filter(Transfer.unit_id == unit_id)
            .order_by(Transfer.id)
            .all()
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# There is a single way to sell a unit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_selling_twice_is_a_conflict(
    client: AsyncClient, auth_headers, test_users, places
):
    """A unit is sold once: the second sale is rejected with 409."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "SELL")

    first = await client.post(
        f"/api/v1/units/{unit_id}/sell", json={}, headers=auth_headers
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"/api/v1/units/{unit_id}/sell", json={}, headers=auth_headers
    )
    assert second.status_code == 409, second.text

    unit = _unit_row(unit_id)
    assert unit.status == UnitStatus.SOLD
    # The sale was recorded once, not twice.
    assert len(_transfer_rows(unit_id)) == 1


@pytest.mark.asyncio
async def test_the_sale_is_recorded_in_the_history(
    client: AsyncClient, auth_headers, test_users, places
):
    """A sale always leaves a record: sold_date and a closed transfer."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "SALEREC")

    response = await client.post(
        f"/api/v1/units/{unit_id}/sell",
        json={"notes": "Venta de prueba"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["sold_date"] is not None

    transfers = _transfer_rows(unit_id)
    assert len(transfers) == 1
    sale = transfers[0]
    assert sale.status == TransferStatus.RECEIVED
    assert sale.destination_location_id is None
    assert sale.origin_location_id == places[0].id
    assert sale.received_at is not None


@pytest.mark.asyncio
async def test_a_unit_in_transit_cannot_be_sold(
    client: AsyncClient, auth_headers, test_users, places
):
    """A unit that is on the road has to arrive before it is sold."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "SELLSKIP")
    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    assert dispatch.status_code == 200, dispatch.text

    response = await client.post(
        f"/api/v1/units/{unit_id}/sell", json={}, headers=auth_headers
    )
    assert response.status_code == 409, response.text
    assert _unit_row(unit_id).status == UnitStatus.IN_TRANSIT


# ---------------------------------------------------------------------------
# A transfer is closed once
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_receiving_a_transfer_twice_is_a_conflict(
    client: AsyncClient, auth_headers, test_users, places
):
    """A received transfer is closed: it cannot be received again."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "RECV")
    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    transfer_id = dispatch.json()["id"]

    first = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "RECEIVED"},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text

    second = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "RECEIVED"},
        headers=auth_headers,
    )
    assert second.status_code == 409, second.text


@pytest.mark.asyncio
async def test_a_cancelled_transfer_cannot_be_received(
    client: AsyncClient, auth_headers, test_users, places
):
    """A cancelled trip never happened: there is nothing to receive."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "CNLRCV")
    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    transfer_id = dispatch.json()["id"]

    cancelled = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "CANCELLED"},
        headers=auth_headers,
    )
    assert cancelled.status_code == 200, cancelled.text

    received = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "RECEIVED"},
        headers=auth_headers,
    )
    assert received.status_code == 409, received.text


@pytest.mark.asyncio
async def test_cancelling_brings_the_unit_back_to_the_origin(
    client: AsyncClient, auth_headers, test_users, places
):
    """Cancelling leaves the unit available at the origin."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "CNL")
    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    transfer_id = dispatch.json()["id"]

    cancelled = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "CANCELLED"},
        headers=auth_headers,
    )
    assert cancelled.status_code == 200, cancelled.text

    unit = _unit_row(unit_id)
    assert unit.status == UnitStatus.AVAILABLE
    assert unit.current_location_id == places[0].id
    assert unit.sold_date is None


@pytest.mark.asyncio
async def test_receiving_leaves_the_unit_at_the_destination(
    client: AsyncClient, auth_headers, test_users, places
):
    """The state of the unit comes out of the state of the transfer."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "RCV")
    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    transfer_id = dispatch.json()["id"]

    # The dispatch put the unit on the road.
    unit = _unit_row(unit_id)
    assert unit.status == UnitStatus.IN_TRANSIT
    assert unit.current_location_id == places[0].id

    received = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "RECEIVED"},
        headers=auth_headers,
    )
    assert received.status_code == 200, received.text

    unit = _unit_row(unit_id)
    assert unit.status == UnitStatus.AVAILABLE
    assert unit.current_location_id == places[1].id


# ---------------------------------------------------------------------------
# The actor and the clock belong to the server
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_dispatched_by_id_from_the_client_is_rejected(
    client: AsyncClient, auth_headers, test_users, places
):
    """Nobody signs a dispatch but the server."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "FORGE")

    response = await client.post(
        "/api/v1/transfers/",
        json={
            "unit_id": unit_id,
            "origin_location_id": places[0].id,
            "destination_location_id": places[1].id,
            "dispatched_by_id": test_users[0].id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text

    transfers = _transfer_rows(unit_id)
    assert transfers == []


@pytest.mark.asyncio
async def test_a_received_by_id_from_the_client_is_rejected(
    client: AsyncClient, auth_headers, test_users, places
):
    """Reception is signed by the server too."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "FORGE2")
    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    transfer_id = dispatch.json()["id"]

    response = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "RECEIVED", "received_by_id": test_users[0].id},
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text

    transfer = _transfer_rows(unit_id)[0]
    assert transfer.received_by_id is None


@pytest.mark.asyncio
async def test_a_dispatched_at_from_the_client_is_rejected(
    client: AsyncClient, auth_headers, test_users, places
):
    """The dispatch moment is the server's clock."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "FORGE3")

    response = await client.post(
        "/api/v1/transfers/",
        json={
            "unit_id": unit_id,
            "origin_location_id": places[0].id,
            "destination_location_id": places[1].id,
            "dispatched_at": "2020-01-01T00:00:00",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_the_dispatch_is_signed_by_the_session_user(
    client: AsyncClient, auth_headers, test_users, places
):
    """The transfer records who dispatched it and when."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "SIGN")
    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    assert dispatch.status_code == 200, dispatch.text

    transfer = _transfer_rows(unit_id)[0]
    assert transfer.dispatched_by_id == test_users[0].id
    assert transfer.dispatched_at is not None
    assert transfer.received_by_id is None


# ---------------------------------------------------------------------------
# One active transfer per unit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_second_active_transfer_is_rejected(
    client: AsyncClient, auth_headers, test_users, places
):
    """A unit holds at most one active transfer."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "TWO")

    first = await _dispatch(client, auth_headers, unit_id, places[0].id, places[1].id)
    assert first.status_code == 200, first.text

    second = await _dispatch(client, auth_headers, unit_id, places[0].id, places[2].id)
    assert second.status_code == 409, second.text

    active = [
        transfer
        for transfer in _transfer_rows(unit_id)
        if transfer.status in (TransferStatus.PENDING, TransferStatus.IN_TRANSIT)
    ]
    assert len(active) == 1


@pytest.mark.asyncio
async def test_a_unit_can_be_dispatched_again_once_the_transfer_is_closed(
    client: AsyncClient, auth_headers, test_users, places
):
    """The rule is about *active* transfers, not about the whole history."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "AGAIN")
    first = await _dispatch(client, auth_headers, unit_id, places[0].id, places[1].id)
    assert first.status_code == 200, first.text

    received = await client.put(
        f"/api/v1/transfers/{first.json()['id']}",
        json={"status": "RECEIVED"},
        headers=auth_headers,
    )
    assert received.status_code == 200, received.text

    second = await _dispatch(client, auth_headers, unit_id, places[1].id, places[2].id)
    assert second.status_code == 200, second.text


@pytest.mark.asyncio
async def test_a_unit_in_transit_cannot_be_dispatched_again(
    client: AsyncClient, auth_headers, test_users, places
):
    """The unit-detail dispatch refuses a unit that is already travelling."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "INTR")
    first = await _dispatch(client, auth_headers, unit_id, places[0].id, places[1].id)
    assert first.status_code == 200, first.text

    again = await client.post(
        f"/api/v1/transfers/unit/{unit_id}",
        json={"to_location_id": places[2].id},
        headers=auth_headers,
    )
    assert again.status_code == 409, again.text


# ---------------------------------------------------------------------------
# A sold unit never travels again
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_sold_unit_cannot_be_dispatched(
    client: AsyncClient, auth_headers, test_users, places
):
    """A sold unit is final."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "SOLDDSP")
    sold = await client.post(
        f"/api/v1/units/{unit_id}/sell", json={}, headers=auth_headers
    )
    assert sold.status_code == 200, sold.text

    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    assert dispatch.status_code == 409, dispatch.text


# ---------------------------------------------------------------------------
# The dispatch starts where the unit is, and ends somewhere real
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_origin_has_to_be_where_the_unit_is(
    client: AsyncClient, auth_headers, test_users, places
):
    """A dispatch cannot start somewhere the unit is not."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "ORIGIN")

    response = await client.post(
        "/api/v1/transfers/",
        json={
            "unit_id": unit_id,
            "origin_location_id": places[1].id,
            "destination_location_id": places[2].id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test_the_destination_has_to_exist(
    client: AsyncClient, auth_headers, test_users, places
):
    """A dispatch cannot end in a place that does not exist."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "DEST")

    response = await client.post(
        "/api/v1/transfers/",
        json={
            "unit_id": unit_id,
            "origin_location_id": places[0].id,
            "destination_location_id": 999999,
        },
        headers=auth_headers,
    )
    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# The history of a unit is never deleted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deleting_a_unit_keeps_its_history(
    client: AsyncClient, auth_headers, test_users, places
):
    """A unit with transfers is not deleted: the trail is preserved."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "DEL")
    dispatch = await _dispatch(
        client, auth_headers, unit_id, places[0].id, places[1].id
    )
    assert dispatch.status_code == 200, dispatch.text

    deleted = await client.delete(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert deleted.status_code == 409, deleted.text

    # The unit is still there, and so is its history.
    unit = await client.get(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert unit.status_code == 200, unit.text

    transfers = _transfer_rows(unit_id)
    assert len(transfers) == 1
    assert transfers[0].unit_id == unit_id


@pytest.mark.asyncio
async def test_a_unit_without_history_can_be_deleted(
    client: AsyncClient, auth_headers, test_users, places
):
    """A unit that never travelled can be deleted."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "DEL2")

    deleted = await client.delete(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert deleted.status_code == 200, deleted.text

    gone = await client.get(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert gone.status_code == 404


# ---------------------------------------------------------------------------
# The state of a unit only changes through a transfer or a sale
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_state_of_a_unit_cannot_be_edited(
    client: AsyncClient, auth_headers, test_users, places
):
    """PUT /units/{id} does not touch the state of the unit."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "EDIT")

    for payload in (
        {"status": "SOLD"},
        {"status": "IN_TRANSIT"},
        {"sold_date": "2026-01-01T00:00:00"},
        {"current_location_id": places[1].id},
    ):
        response = await client.put(
            f"/api/v1/units/{unit_id}", json=payload, headers=auth_headers
        )
        assert response.status_code == 422, response.text

    unit = _unit_row(unit_id)
    assert unit.status == UnitStatus.AVAILABLE
    assert unit.sold_date is None
    assert unit.current_location_id == places[0].id


@pytest.mark.asyncio
async def test_a_transfer_without_a_destination_is_a_sale(
    client: AsyncClient, auth_headers, test_users, places
):
    """The unit-detail "Vender" action goes through the sale service."""
    unit_id = await _create_unit(client, auth_headers, places[0].id, "NOSALE")

    response = await client.post(
        f"/api/v1/transfers/unit/{unit_id}",
        json={"from_location_id": places[0].id, "notes": "Venta"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text

    unit = _unit_row(unit_id)
    assert unit.status == UnitStatus.SOLD
    assert unit.sold_date is not None

    transfers = _transfer_rows(unit_id)
    assert len(transfers) == 1
    assert transfers[0].status == TransferStatus.RECEIVED
    assert transfers[0].destination_location_id is None
