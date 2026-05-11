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
        "brand": "Thunderrol",
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
async def test_get_transfer_by_id(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can fetch a transfer by ID."""
    unit_data = {
        "model": "TR-GetT",
        "brand": "Thunderrol",
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
        "brand": "Thunderrol",
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
        "brand": "Thunderrol",
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
