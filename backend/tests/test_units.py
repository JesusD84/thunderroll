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
        "brand": "Thunderoll",
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
        "brand": "Thunderoll",
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
        "brand": "Thunderoll",
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
        "brand": "Thunderoll",
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
        "brand": "Thunderoll",
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
        "brand": "Thunderoll",
        "color": "Gray",
        "current_location_id": test_locations[0].id,
        "engine_number": "ENG-TRANS-001",
    }
    create_resp = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    unit_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/units/{unit_id}/transfers", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_sell_unit_marks_sold_without_transfer(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """POST /units/{id}/sell sets SOLD, stamps sold_date, keeps location and creates no transfer."""
    create_resp = await client.post(
        "/api/v1/units/",
        json={
            "model": "TR-SELL",
            "brand": "Thunderoll",
            "color": "Black",
            "current_location_id": test_locations[0].id,
            "engine_number": "ENG-SELL-001",
        },
        headers=auth_headers,
    )
    unit_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/units/{unit_id}/sell", json={"notes": "Cliente frecuente"}, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "SOLD"
    assert data["sold_date"] is not None
    assert "Cliente frecuente" in (data["notes"] or "")

    assert data["current_location_id"] == test_locations[0].id

    transfers = await client.get("/api/v1/transfers/", headers=auth_headers)
    assert transfers.status_code == 200
    matching = [t for t in transfers.json() if t["unit_id"] == unit_id]
    assert matching == []


@pytest.mark.asyncio
async def test_sell_unit_twice_returns_400(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """Selling an already sold unit is rejected."""
    create_resp = await client.post(
        "/api/v1/units/",
        json={
            "model": "TR-SELL2",
            "brand": "Thunderoll",
            "color": "Black",
            "current_location_id": test_locations[0].id,
            "engine_number": "ENG-SELL-002",
        },
        headers=auth_headers,
    )
    unit_id = create_resp.json()["id"]
    first = await client.post(f"/api/v1/units/{unit_id}/sell", json={}, headers=auth_headers)
    assert first.status_code == 200
    second = await client.post(f"/api/v1/units/{unit_id}/sell", json={}, headers=auth_headers)
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_sell_unit_not_found(client: AsyncClient, auth_headers, test_users):
    resp = await client.post("/api/v1/units/999999/sell", json={}, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sold_units_hidden_from_default_list(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """Sold units are excluded from the default list but shown when status=SOLD."""
    create_resp = await client.post(
        "/api/v1/units/",
        json={
            "model": "TR-HIDE",
            "brand": "Thunderoll",
            "color": "Red",
            "current_location_id": test_locations[0].id,
            "engine_number": "ENG-HIDE-001",
        },
        headers=auth_headers,
    )
    unit_id = create_resp.json()["id"]
    sell_resp = await client.post(f"/api/v1/units/{unit_id}/sell", json={}, headers=auth_headers)
    assert sell_resp.status_code == 200

    default_resp = await client.get("/api/v1/units/", headers=auth_headers)
    assert default_resp.status_code == 200
    assert unit_id not in [u["id"] for u in default_resp.json()]
    assert all(u["status"] != "SOLD" for u in default_resp.json())

    sold_resp = await client.get("/api/v1/units/", params={"status": "SOLD"}, headers=auth_headers)
    assert sold_resp.status_code == 200
    assert unit_id in [u["id"] for u in sold_resp.json()]
    assert int(sold_resp.headers["X-Total-Count"]) >= 1
