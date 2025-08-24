
"""Test authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_users, test_locations):
    """Test successful login."""
    login_data = {
        "email": "admin@test.com",
        "password": "testpass123"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_users, test_locations):
    """Test login with invalid credentials."""
    login_data = {
        "email": "admin@test.com",
        "password": "wrongpassword"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test get current user endpoint."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test get current user without token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
