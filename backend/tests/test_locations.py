"""Integration tests for location endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_locations(client: AsyncClient, auth_headers, test_users, test_locations):
    """Authenticated user can list locations."""
    response = await client.get("/api/v1/locations/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_get_locations_unauthorized(client: AsyncClient):
    """Unauthenticated request returns 401."""
    response = await client.get("/api/v1/locations/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_location_by_id(client: AsyncClient, auth_headers, test_users, test_locations):
    """Can fetch a single location by ID."""
    loc = test_locations[0]
    response = await client.get(f"/api/v1/locations/{loc.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == loc.id
    assert data["name"] == loc.name


@pytest.mark.asyncio
async def test_get_location_not_found(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns 404 for non-existent location."""
    response = await client.get("/api/v1/locations/9999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_location_as_admin(client: AsyncClient, auth_headers, test_users, test_locations):
    """Admin can create a location."""
    loc_data = {"name": "New Location", "address": "456 Ave"}
    response = await client.post("/api/v1/locations/", json=loc_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Location"
    assert data["address"] == "456 Ave"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_location_requires_elevated_role(client: AsyncClient, test_users, test_locations):
    """Viewer/operator cannot create locations."""
    login_data = {"username": "inventario", "password": "testpass123"}
    login_resp = await client.post("/api/v1/auth/login", data=login_data)
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/v1/locations/", json={"name": "X"}, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_location(client: AsyncClient, auth_headers, test_users, test_locations):
    """Admin can update a location."""
    loc = test_locations[0]
    update_data = {"name": "Updated Name"}
    response = await client.put(f"/api/v1/locations/{loc.id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_location_not_found(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns 404 when updating non-existent location."""
    response = await client.put("/api/v1/locations/9999", json={"name": "X"}, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_location_empty(client: AsyncClient, auth_headers, test_users, test_locations):
    """Admin can delete a location with no units."""
    loc = test_locations[2]  # Sucursal — no units assigned
    response = await client.delete(f"/api/v1/locations/{loc.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "deleted" in data["message"]


@pytest.mark.asyncio
async def test_delete_location_not_found(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns 404 when deleting non-existent location."""
    response = await client.delete("/api/v1/locations/9999", headers=auth_headers)
    assert response.status_code == 404
