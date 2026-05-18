"""Integration tests for user endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users_as_admin(client: AsyncClient, auth_headers, test_users, test_locations):
    """Admin can list all users."""
    response = await client.get("/api/v1/user/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_list_users_requires_admin(client: AsyncClient, test_users, test_locations):
    """Non-admin user cannot list users."""
    login_data = {"username": "inventario", "password": "testpass123"}
    login_resp = await client.post("/api/v1/auth/login", data=login_data)
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/user/", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, test_locations):
    """Anyone can register a new user."""
    user_data = {
        "email": "newuser@test.com",
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
        "role": "viewer",
        "password": "password123",
    }
    response = await client.post("/api/v1/user/register", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["username"] == "newuser"
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient, test_users, test_locations):
    """Registering with an existing email returns 400."""
    user_data = {
        "email": "admin@test.com",
        "username": "another",
        "first_name": "Dup",
        "last_name": "Email",
        "role": "viewer",
        "password": "password123",
    }
    response = await client.post("/api/v1/user/register", json=user_data)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_user_duplicate_username(client: AsyncClient, test_users, test_locations):
    """Registering with an existing username returns 400."""
    user_data = {
        "email": "unique@test.com",
        "username": "admin",
        "first_name": "Dup",
        "last_name": "Username",
        "role": "viewer",
        "password": "password123",
    }
    response = await client.post("/api/v1/user/register", json=user_data)
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient, auth_headers, test_users, test_locations):
    """Authenticated user can read their own profile."""
    response = await client.get("/api/v1/user/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["username"] == "admin"


@pytest.mark.asyncio
async def test_read_users_me_unauthorized(client: AsyncClient):
    """Unauthenticated request to /me returns 401."""
    response = await client.get("/api/v1/user/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_users_me(client: AsyncClient, auth_headers, test_users, test_locations):
    """Authenticated user can update their own profile."""
    update_data = {"first_name": "UpdatedName"}
    response = await client.put("/api/v1/user/me", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "UpdatedName"


@pytest.mark.asyncio
async def test_update_users_me_unauthorized(client: AsyncClient):
    """Unauthenticated update to /me returns 401."""
    response = await client.put("/api/v1/user/me", json={"first_name": "X"})
    assert response.status_code == 401
