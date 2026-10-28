"""Integration tests for transfer endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_transfers(client: AsyncClient, auth_headers, test_users, test_locations):
    """Authenticated user can list transfers."""
    response = await client.get("/api/v1/transfers/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_transfers_unauthorized(client: AsyncClient):
    """Unauthenticated request returns 401."""
    response = await client.get("/api/v1/transfers/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_transfer(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can create a transfer for an existing unit."""
    unit_data = {
        "model": "TR-Trans",
        "brand": "Thunderoll",
        "color": "Red",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-TRANSFER-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    transfer_data = {
        "unit_id": unit_id,
        "origin_location_id": test_locations[0].id,
        "destination_location_id": test_locations[1].id,
    }
    response = await client.post("/api/v1/transfers/", json=transfer_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["unit_id"] == unit_id


@pytest.mark.asyncio
async def test_create_transfer_populates_dispatched_at(client: AsyncClient, auth_headers, test_users, test_locations):
    """Regression: dispatched_at must never come back null for a newly
    created transfer, even when the caller does not send it explicitly.
    """
    unit_data = {
        "model": "TR-DispAt",
        "brand": "Thunderoll",
        "color": "Purple",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-DISPAT-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    transfer_data = {
        "unit_id": unit_id,
        "origin_location_id": test_locations[0].id,
        "destination_location_id": test_locations[1].id,
    }
    response = await client.post("/api/v1/transfers/", json=transfer_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["dispatched_at"] is not None


@pytest.mark.asyncio
async def test_status_change_creates_transfer_with_location_and_date(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """Regression: a pure status change (e.g. marking a unit SOLD) must
    still generate a transfer record with dispatched_at and a route
    (origin/destination), instead of the '-' shown in the Kanban bug.
    """
    unit_data = {
        "model": "TR-StatusChg",
        "brand": "Thunderoll",
        "color": "Orange",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-STATUSCHG-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/units/{unit_id}", json={"status": "SOLD"}, headers=auth_headers
    )
    assert update_resp.status_code == 200

    transfers_resp = await client.get("/api/v1/transfers/", headers=auth_headers)
    assert transfers_resp.status_code == 200
    matching = [t for t in transfers_resp.json() if t["unit_id"] == unit_id]
    assert matching
    latest = matching[0]
    assert latest["dispatched_at"] is not None
    assert latest["origin_location_id"] is not None
    assert latest["destination_location_id"] is not None


@pytest.mark.asyncio
async def test_transfer_includes_dispatched_by_name(client: AsyncClient, auth_headers, test_users, test_locations):
    """Regression: the 'Creado Por' column relies on dispatched_by_name,
    which must be populated from the dispatching user's name.
    """
    unit_data = {
        "model": "TR-DispBy",
        "brand": "Thunderoll",
        "color": "Pink",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-DISPBY-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/units/{unit_id}", json={"current_location_id": test_locations[1].id}, headers=auth_headers
    )
    assert update_resp.status_code == 200

    response = await client.get("/api/v1/transfers/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    matching = [t for t in data if t["unit_id"] == unit_id]
    assert matching
    assert matching[0]["dispatched_by_name"] == "Test Admin"


@pytest.mark.asyncio
async def test_get_transfer_by_id(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can fetch a transfer by ID."""
    unit_data = {
        "model": "TR-GetT",
        "brand": "Thunderoll",
        "color": "Blue",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-GETT-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    transfer_data = {
        "unit_id": unit_id,
        "destination_location_id": test_locations[1].id,
    }
    trans_resp = await client.post("/api/v1/transfers/", json=transfer_data, headers=auth_headers)
    transfer_id = trans_resp.json()["id"]

    response = await client.get(f"/api/v1/transfers/{transfer_id}", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_transfer_not_found(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns 404 for non-existent transfer."""
    response = await client.get("/api/v1/transfers/9999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_transfer(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can update a transfer status."""
    unit_data = {
        "model": "TR-UpdT",
        "brand": "Thunderoll",
        "color": "Green",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-UPDT-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    transfer_data = {"unit_id": unit_id, "destination_location_id": test_locations[1].id}
    trans_resp = await client.post("/api/v1/transfers/", json=transfer_data, headers=auth_headers)
    transfer_id = trans_resp.json()["id"]

    update_data = {"status": "RECEIVED"}
    response = await client.put(
        f"/api/v1/transfers/{transfer_id}", json=update_data, headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_transfer(client: AsyncClient, auth_headers, test_users, test_locations):
    """Admin can delete a transfer."""
    unit_data = {
        "model": "TR-DelT",
        "brand": "Thunderoll",
        "color": "Black",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-DELT-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    transfer_data = {"unit_id": unit_id, "destination_location_id": test_locations[1].id}
    trans_resp = await client.post("/api/v1/transfers/", json=transfer_data, headers=auth_headers)
    transfer_id = trans_resp.json()["id"]

    response = await client.delete(f"/api/v1/transfers/{transfer_id}", headers=auth_headers)
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]


@pytest.mark.asyncio
async def test_get_transfer_stats(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can fetch transfer statistics."""
    response = await client.get("/api/v1/transfers/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_transfers" in data


# ---------------------------------------------------------------------------
# POST /transfers/unit/{unit_id} and GET /transfers/unit/{unit_id}/active
#
# Real HTTP tests, sending exactly what the unit-detail-page "Transferir"/
# "Vender" actions send. The endpoint used to live at
# POST /units/{unit_id}/transfer and was validated against the wrong Pydantic
# model (a dead duplicate class), which made every real request 422. Only
# service-layer tests existed before, which is why that bug went unnoticed.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transfer_unit_dispatch(client: AsyncClient, auth_headers, test_users, test_locations):
    """Dispatching a unit to a new location marks it IN_TRANSIT."""
    unit_data = {
        "model": "TR-UnitTransfer",
        "brand": "Thunderoll",
        "color": "Blue",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-UNITTRANSFER-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/transfers/unit/{unit_id}",
        json={
            "from_location_id": test_locations[0].id,
            "to_location_id": test_locations[1].id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200

    unit_resp = await client.get(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert unit_resp.json()["status"] == "IN_TRANSIT"


@pytest.mark.asyncio
async def test_transfer_unit_sell_without_destination(client: AsyncClient, auth_headers, test_users, test_locations):
    """Omitting to_location_id is 'Vender': the unit is marked SOLD."""
    unit_data = {
        "model": "TR-UnitSell",
        "brand": "Thunderoll",
        "color": "Green",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-UNITSELL-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/transfers/unit/{unit_id}",
        json={"from_location_id": test_locations[0].id, "notes": "Venta de prueba"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    unit_resp = await client.get(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert unit_resp.json()["status"] == "SOLD"
    assert unit_resp.json()["sold_date"] is not None


@pytest.mark.asyncio
async def test_transfer_unit_not_found(client: AsyncClient, auth_headers, test_users, test_locations):
    """404 when the unit does not exist."""
    response = await client.post(
        "/api/v1/transfers/unit/999999",
        json={"to_location_id": test_locations[0].id},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_unit_active_transfer(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns the in-progress transfer for a unit that was just dispatched."""
    unit_data = {
        "model": "TR-UnitActive",
        "brand": "Thunderoll",
        "color": "Black",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-UNITACTIVE-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/transfers/unit/{unit_id}",
        json={"from_location_id": test_locations[0].id, "to_location_id": test_locations[1].id},
        headers=auth_headers,
    )

    response = await client.get(f"/api/v1/transfers/unit/{unit_id}/active", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["unit_id"] == unit_id


@pytest.mark.asyncio
async def test_get_unit_active_transfer_none(client: AsyncClient, auth_headers, test_users, test_locations):
    """404 when the unit has no in-progress transfer."""
    unit_data = {
        "model": "TR-UnitNoActive",
        "brand": "Thunderoll",
        "color": "White",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-UNITNOACTIVE-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/transfers/unit/{unit_id}/active", headers=auth_headers)
    assert response.status_code == 404
