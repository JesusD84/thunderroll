"""Test authentication endpoints."""

import pytest
from httpx import AsyncClient
from app.models.models import User, UserRole
from app.core.security import Security


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_users, test_locations):
    """Test successful login."""
    login_data = {
        "username": "admin",
        "password": "testpass123"
    }

    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_users, test_locations):
    """Test login with invalid credentials."""
    login_data = {
        "username": "admin@test.com",
        "password": "wrongpassword"
    }

    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session, test_locations):
    """Inactive user can obtain a token but cannot access protected endpoints."""
    inactive = User(
        first_name="Inactive",
        last_name="User",
        username="inactive",
        email="inactive@test.com",
        hashed_password=Security.get_password_hash("testpass123"),
        role=UserRole.VIEWER,
        is_active=False,
    )
    db_session.add(inactive)
    db_session.commit()

    login_data = {"username": "inactive", "password": "testpass123"}
    response = await client.post("/api/v1/auth/login", data=login_data)
    # Login succeeds — token is issued even for inactive users
    assert response.status_code == 200
    token = response.json()["access_token"]

    # But accessing a protected endpoint is denied
    headers = {"Authorization": f"Bearer {token}"}
    me_response = await client.get("/api/v1/user/me", headers=headers)
    assert me_response.status_code == 400


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test get current user endpoint."""
    response = await client.get("/api/v1/user/me", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test get current user without token."""
    response = await client.get("/api/v1/user/me")
    assert response.status_code == 401
