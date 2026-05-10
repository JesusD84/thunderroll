"""Unit tests for auth service functions."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, UTC
from jose import jwt
from fastapi import HTTPException

from app.services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_user_by_username,
    get_user_by_email,
    authenticate_user,
    create_password_reset_token,
    verify_password_reset_token,
    get_current_user,
    get_current_active_user,
    require_role,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.models.models import User, UserRole


# ---------------------------------------------------------------------------
# verify_password
# ---------------------------------------------------------------------------

def test_verify_password_correct():
    """verify_password returns True for correct password."""
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_incorrect():
    """verify_password returns False for wrong password."""
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("mypassword")
    assert verify_password("wrongpassword", hashed) is False


# ---------------------------------------------------------------------------
# get_password_hash
# ---------------------------------------------------------------------------

def test_get_password_hash_returns_different_string():
    """get_password_hash returns a string different from the input."""
    result = get_password_hash("mypassword")
    assert isinstance(result, str)
    assert result != "mypassword"


def test_get_password_hash_is_verifiable():
    """Hash produced by get_password_hash can be verified."""
    hashed = get_password_hash("mypassword")
    assert verify_password("mypassword", hashed) is True


# ---------------------------------------------------------------------------
# create_access_token
# ---------------------------------------------------------------------------

def test_create_access_token_contains_sub():
    """Token encodes the 'sub' claim."""
    token = create_access_token(data={"sub": "admin"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin"


def test_create_access_token_contains_exp():
    """Token contains an expiration claim."""
    token = create_access_token(data={"sub": "admin"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


def test_create_access_token_default_expiry():
    """Default expiry is ACCESS_TOKEN_EXPIRE_MINUTES from now."""
    before = datetime.now(UTC)
    token = create_access_token(data={"sub": "admin"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    after = datetime.now(UTC)
    expected_min = before + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expected_max = after + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) + timedelta(seconds=5)
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    assert expected_min - timedelta(seconds=5) <= exp <= expected_max


def test_create_access_token_custom_expiry():
    """Custom expires_delta is respected."""
    delta = timedelta(minutes=5)
    token = create_access_token(data={"sub": "admin"}, expires_delta=delta)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    now = datetime.now(UTC)
    assert (exp - now).total_seconds() <= 310  # 5 min + small margin


# ---------------------------------------------------------------------------
# get_user_by_username
# ---------------------------------------------------------------------------

def test_get_user_by_username_found():
    """Returns user when username exists."""
    mock_db = MagicMock()
    mock_user = User(username="admin", email="admin@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = get_user_by_username(mock_db, "admin")
    assert result is mock_user


def test_get_user_by_username_not_found():
    """Returns None when username does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = get_user_by_username(mock_db, "nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# get_user_by_email
# ---------------------------------------------------------------------------

def test_get_user_by_email_found():
    """Returns user when email exists."""
    mock_db = MagicMock()
    mock_user = User(username="admin", email="admin@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = get_user_by_email(mock_db, "admin@test.com")
    assert result is mock_user


def test_get_user_by_email_not_found():
    """Returns None when email does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = get_user_by_email(mock_db, "no@test.com")
    assert result is None


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------

def test_authenticate_user_success_by_username():
    """Authenticates with correct username + password."""
    mock_db = MagicMock()
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("testpass123")
    mock_user = User(username="admin", email="admin@test.com", hashed_password=hashed)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = authenticate_user(mock_db, "admin", "testpass123")
    assert result is mock_user


def test_authenticate_user_success_by_email():
    """Authenticates when username is actually an email."""
    mock_db = MagicMock()
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("testpass123")
    mock_user = User(username="admin", email="admin@test.com", hashed_password=hashed)

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        None, mock_user
    ]

    result = authenticate_user(mock_db, "admin@test.com", "testpass123")
    assert result is mock_user


def test_authenticate_user_wrong_password():
    """Returns False when password is incorrect."""
    mock_db = MagicMock()
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("testpass123")
    mock_user = User(username="admin", email="admin@test.com", hashed_password=hashed)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = authenticate_user(mock_db, "admin", "wrongpassword")
    assert result is False


def test_authenticate_user_not_found():
    """Returns False when user does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = authenticate_user(mock_db, "nonexistent", "testpass123")
    assert result is False


# ---------------------------------------------------------------------------
# create_password_reset_token
# ---------------------------------------------------------------------------

def test_create_password_reset_token():
    """Creates a valid reset token with correct claims."""
    token = create_password_reset_token("admin@test.com")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin@test.com"
    assert payload["type"] == "password_reset"
    assert "exp" in payload


# ---------------------------------------------------------------------------
# verify_password_reset_token
# ---------------------------------------------------------------------------

def test_verify_password_reset_token_valid():
    """Returns email for a valid reset token."""
    token = create_password_reset_token("admin@test.com")
    email = verify_password_reset_token(token)
    assert email == "admin@test.com"


def test_verify_password_reset_token_wrong_type():
    """Raises HTTPException when token type is not 'password_reset'."""
    token = create_access_token(data={"sub": "admin@test.com"})
    with pytest.raises(HTTPException) as exc:
        verify_password_reset_token(token)
    assert exc.value.status_code == 400


def test_verify_password_reset_token_expired():
    """Raises HTTPException for expired token."""
    expire = datetime.now(UTC) - timedelta(minutes=1)
    to_encode = {"sub": "admin@test.com", "type": "password_reset", "exp": expire}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        verify_password_reset_token(token)
    assert exc.value.status_code == 400


def test_verify_password_reset_token_invalid():
    """Raises HTTPException for malformed token."""
    with pytest.raises(HTTPException) as exc:
        verify_password_reset_token("not.a.valid.token")
    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# get_current_active_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_active_user_active():
    """Returns user when is_active is True."""
    user = User(username="admin", is_active=True)
    result = await get_current_active_user(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_active_user_inactive():
    """Raises HTTPException when is_active is False."""
    user = User(username="admin", is_active=False)
    with pytest.raises(HTTPException) as exc:
        await get_current_active_user(user)
    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# require_role
# ---------------------------------------------------------------------------

def test_require_role_allowed():
    """Returns user when role is in allowed list."""
    user = User(username="admin", role=UserRole.ADMIN)
    checker = require_role([UserRole.ADMIN, UserRole.MANAGER])
    result = checker(user)
    assert result is user


def test_require_role_denied():
    """Raises HTTPException when role is not allowed."""
    user = User(username="viewer", role=UserRole.VIEWER)
    checker = require_role([UserRole.ADMIN])
    with pytest.raises(HTTPException) as exc:
        checker(user)
    assert exc.value.status_code == 403
