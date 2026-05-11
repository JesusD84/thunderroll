"""Integration tests for unit endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_units(client: AsyncClient, auth_headers, test_users, test_locations):
    """Authenticated user can list units."""
    response = await client.get("/api/v1/units/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_units_unauthorized(client: AsyncClient):
    """Unauthenticated request returns 401."""
    response = await client.get("/api/v1/units/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_unit(client: AsyncClient, auth_headers, test_users, test_locations):
    """Admin can create a unit."""
    unit_data = {
        "model": "TR-2025",
        "brand": "Thunderrol",
        "color": "Red",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-TEST-001",
    }
    response = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "TR-2025"
    assert data["engine_number"] == "ENG-TEST-001"


@pytest.mark.asyncio
async def test_create_unit_duplicate_engine(client: AsyncClient, auth_headers, test_users, test_locations):
    """Creating a unit with duplicate engine returns 400."""
    unit_data = {
        "model": "TR",
        "brand": "Thunderrol",
        "color": "Blue",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-DUP-001",
    }
    await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    response = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_unit_by_id(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can fetch a unit by ID."""
    unit_data = {
        "model": "TR-Get",
        "brand": "Thunderrol",
        "color": "Green",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-GET-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["engine_number"] == "ENG-GET-001"


@pytest.mark.asyncio
async def test_get_unit_not_found(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns 404 for non-existent unit."""
    response = await client.get("/api/v1/units/9999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_unit(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can update a unit's fields."""
    unit_data = {
        "model": "TR-Update",
        "brand": "Thunderrol",
        "color": "Black",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-UPDATE-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    update_data = {"model": "TR-Updated"}
    response = await client.put(f"/api/v1/units/{unit_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["model"] == "TR-UPDATED"


@pytest.mark.asyncio
async def test_delete_unit(client: AsyncClient, auth_headers, test_users, test_locations):
    """Admin can delete a unit."""
    unit_data = {
        "model": "TR-Delete",
        "brand": "Thunderrol",
        "color": "White",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-DEL-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert response.status_code == 200
    assert "deleted" in response.json()["message"]

    get_resp = await client.get(f"/api/v1/units/{unit_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_unit_stats(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can fetch unit statistics."""
    response = await client.get("/api/v1/units/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_units" in data


@pytest.mark.asyncio
async def test_get_unit_transfers(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can fetch transfers for a unit."""
    unit_data = {
        "model": "TR-Transfers",
        "brand": "Thunderrol",
        "color": "Gray",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-TRANS-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/units/{unit_id}/transfers", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
