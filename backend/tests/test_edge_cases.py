"""Edge case and error handling tests."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Auth edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_users):
    """Login with wrong password returns 401."""
    login_data = {"username": "admin", "password": "wrongpassword"}
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Login with non-existent user returns 401."""
    login_data = {"username": "noexiste", "password": "testpass123"}
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient):
    """Request with invalid token returns 401."""
    headers = {"Authorization": "Bearer invalidtoken123"}
    response = await client.get("/api/v1/units/", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_token(client: AsyncClient):
    """Request with malformed token returns 401."""
    headers = {"Authorization": "Bearer not.a.real.jwt"}
    response = await client.get("/api/v1/units/", headers=headers)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Unit creation edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_unit_missing_required_fields(client: AsyncClient, auth_headers, test_users, test_locations):
    """Creating unit without required fields returns 422."""
    unit_data = {"brand": "Thunderrol"}
    response = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_unit_invalid_location(client: AsyncClient, auth_headers, test_users):
    """Creating unit with non-existent location returns 404."""
    unit_data = {
        "model": "TR",
        "brand": "Thunderrol",
        "color": "Red",
        "current_location_id": 9999,
        "engine_number": "ENG-EDGE-001",
    }
    response = await client.post("/api/v1/units/", json=unit_data, headers=auth_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Transfer edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transfer_nonexistent_unit(client: AsyncClient, auth_headers, test_users, test_locations):
    """Transferring non-existent unit returns 404."""
    transfer_data = {
        "unit_id": 9999,
        "destination_location_id": test_locations[1].id,
    }
    response = await client.post("/api/v1/transfers/", json=transfer_data, headers=auth_headers)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Security edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sql_injection_attempt(client: AsyncClient, auth_headers):
    """SQL injection in query params does not break the API."""
    response = await client.get(
        "/api/v1/units/?search='; DROP TABLE units;--", headers=auth_headers
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Pagination edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pagination_negative_skip(client: AsyncClient, auth_headers):
    """Negative skip returns 422."""
    response = await client.get("/api/v1/units/?skip=-1", headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pagination_zero_limit(client: AsyncClient, auth_headers):
    """Zero limit returns 422."""
    response = await client.get("/api/v1/units/?limit=0", headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pagination_excessive_limit(client: AsyncClient, auth_headers):
    """Limit over 1000 returns 422."""
    response = await client.get("/api/v1/units/?limit=9999", headers=auth_headers)
    assert response.status_code == 422
