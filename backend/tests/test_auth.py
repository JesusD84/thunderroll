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
    """An inactive user cannot log in at all: no token is handed out.

    Deactivating an account must actually close the credentials, otherwise the
    password keeps working against the API even though every business
    endpoint rejects the user afterwards.
    """
    inactive = User(
        first_name="Inactive",
        last_name="User",
        username="inactive",
        email="inactive@test.com",
        hashed_password=Security.get_password_hash("testpass123"),
        role=UserRole.OPERATOR,
        is_active=False,
    )
    db_session.add(inactive)
    db_session.commit()

    login_data = {"username": "inactive", "password": "testpass123"}
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401
    assert "access_token" not in response.json()


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


# ---------------------------------------------------------------------------
# forgot-password: el fallo de SMTP debe ser visible
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forgot_password_reports_smtp_failure(client, test_users, test_locations):
    """A broken SMTP answers 503 instead of a silent 200.

    A 200 would be indistinguishable from a successful send, and this is the
    only self-service way back into an account.
    """
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        new=AsyncMock(side_effect=RuntimeError("SMTP unreachable")),
    ):
        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "admin@test.com"}
        )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_forgot_password_succeeds_when_email_is_sent(client, test_users, test_locations):
    """When the email goes out, the endpoint answers 200 as before."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        new=AsyncMock(return_value=None),
    ):
        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "admin@test.com"}
        )

    assert response.status_code == 200
    assert "access_token" not in response.json()


@pytest.mark.asyncio
async def test_forgot_password_does_not_leak_user_existence(client, test_users, test_locations):
    """An unknown email still answers 200: no account enumeration."""
    response = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nadie-aqui@test.com"}
    )
    assert response.status_code == 200
